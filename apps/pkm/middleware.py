"""Middleware for logging PKM page-view interactions.

This module contains a lightweight middleware (``PKMInteractionMiddleware``)
that logs ``page_view`` interactions for requests to PKM module URLs
(``/modern/knowledge/*``). The logging is non-blocking: all errors are
swallowed so that interaction capture can NEVER break a page load.

The middleware only fires for authenticated users on successful (2xx/3xx)
GET responses to ``/modern/knowledge/`` paths, avoiding noise from API
calls, static assets, and failed requests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from django.http import HttpRequest, HttpResponse

from apps.pkm.services.interaction_service import log_interaction

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = ["PKMInteractionMiddleware", "PKM_URL_PREFIX"]

#: URL prefix that identifies PKM module pages.
PKM_URL_PREFIX: str = "/modern/knowledge/"


class PKMInteractionMiddleware:
    """Log a ``page_view`` interaction for every PKM page visit.

    The middleware runs *after* the view (in the response phase), so the
    interaction is only logged for successful responses. This avoids
    recording page views for redirects-to-login, 403s, or 500s errors.

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
        """Log a page_view interaction if this is a PKM page visit.

        Conditions:
          - Only for GET requests (page loads, not POST form submits).
          - Only for authenticated users.
          - Only for PKM URL prefix (``/modern/knowledge/``).
          - Only for successful responses (2xx) to avoid logging
            redirects-to-login or error pages.
        """
        # Only log GET page views
        if request.method != "GET":
            return

        # Only for PKM module pages
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

        # Log the interaction — never raise (non-blocking)
        try:
            log_interaction(
                user=user,
                company=company,
                interaction_type="page_view",
                module="pkm",
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
