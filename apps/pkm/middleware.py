"""Middleware for logging page-view interactions across ALL modern modules.

This module contains a lightweight middleware (``PKMInteractionMiddleware``)
that logs ``page_view`` interactions for requests to ANY modern module URL
(``/modern/*``), resolving the module code from the URL path via the
``PATH_MODULE_MAP`` defined in the identity middleware. This gives the PKM
smart-context system visibility into what the user is doing across the
entire ERP, not just inside the knowledge base.

The logging is non-blocking: all errors are swallowed so that interaction
capture can NEVER break a page load.

The middleware only fires for authenticated users on successful (2xx) GET
responses to ``/modern/*`` paths, avoiding noise from API calls, static
assets, and failed requests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from django.http import HttpRequest, HttpResponse

from apps.identity.middleware import PATH_MODULE_MAP, _resolve_module
from apps.pkm.services.interaction_service import log_interaction

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = ["PKMInteractionMiddleware", "PKM_URL_PREFIX", "PATH_MODULE_MAP"]

#: URL prefix that identifies modern module pages (all modules).
PKM_URL_PREFIX: str = "/modern/"


class PKMInteractionMiddleware:
    """Log a ``page_view`` interaction for every modern module page visit.

    The middleware runs *after* the view (in the response phase), so the
    interaction is only logged for successful responses. This avoids
    recording page views for redirects-to-login, 403s, or 500s errors.

    The module code is resolved from the URL path via
    :func:`apps.identity.middleware._resolve_module` (backed by
    ``PATH_MODULE_MAP``). Paths that do not map to a specific module
    (e.g. ``/modern/`` dashboard) are skipped.

    Logging is wrapped in ``try/except`` and never raises — interaction
    capture must not break the main user operation (VAL-CAP-009).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        self._maybe_log_page_view(request, response)
        return response

    def _maybe_log_page_view(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> None:
        """Log a page_view interaction if this is a modern module page visit.

        Conditions:
          - Only for GET requests (page loads, not POST form submits).
          - Only for authenticated users.
          - Only for modern URL prefix (``/modern/*``).
          - Only when a module code can be resolved from the path.
          - Only for successful responses (2xx) to avoid logging
            redirects-to-login or error pages.
        """
        # Only log GET page views
        if request.method != "GET":
            return

        # Only for modern module pages (all modules, not just PKM)
        if not request.path.startswith(PKM_URL_PREFIX):
            return

        user: User | Any = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return

        # Only log successful responses (2xx). Skip 3xx (redirects like
        # login), 4xx (client errors), and 5xx (server errors).
        status_code = getattr(response, "status_code", 200)
        if not (200 <= status_code < 300):
            return

        company: Company | Any = getattr(request, "current_company", None)
        if company is None:
            # TenantMiddleware / ModulePermissionMiddleware normally sets
            # this; skip logging if it is missing rather than guessing.
            return

        # Resolve the module code from the URL path using the identity
        # middleware's PATH_MODULE_MAP. Skip if no module maps (e.g.
        # dashboard at /modern/).
        module = _resolve_module(request.path)
        if module is None:
            return

        # Log the interaction — never raise (non-blocking)
        try:
            log_interaction(
                user=user,
                company=company,
                interaction_type="page_view",
                module=module,
                entity_type="page",
                entity_id=request.path,
                metadata={"url": request.path, "method": "GET"},
            )
        except Exception:
            logger.debug(
                "PKMInteractionMiddleware: failed to log page_view for %s "
                "(user=%s) — interaction logging is non-blocking.",
                request.path,
                getattr(user, "id", user),
                exc_info=True,
            )
