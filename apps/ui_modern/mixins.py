"""Mixins for multi-tenant isolation in ui_modern views.

The :class:`CompanyRequiredMixin` enforces that every view resolves the
active company from ``request.current_company`` (set by
``TenantMiddleware`` from ``session["current_company_id"]``). When no
company is set, the view raises :class:`~django.core.exceptions.PermissionDenied`
rather than silently falling back to ``Company.objects.first()``.

Usage::

    class MyListView(LoginRequiredMixin, CompanyRequiredMixin, ListView):
        def get_queryset(self):
            company = self.get_company()
            return MyModel.objects.filter(company=company)

For function-style helpers and views that don't fit the mixin pattern
(e.g. module-level ``_get_company(request)`` helpers in report views),
use :func:`require_current_company` directly.
"""

from django.core.exceptions import PermissionDenied


def require_current_company(request):
    """Return ``request.current_company`` or raise :class:`PermissionDenied`.

    Use this in function-based helpers and ``View.post/get`` methods that
    cannot inherit :class:`CompanyRequiredMixin`.
    """
    company = getattr(request, "current_company", None)
    if company is None:
        raise PermissionDenied("No company context.")
    return company


class CompanyRequiredMixin:
    """Mixin that exposes :meth:`get_company` for company-scoped views.

    The mixin does NOT change MRO behavior for ``dispatch`` so it is safe
    to combine with ``LoginRequiredMixin`` and other Django generic mixins.
    Views call ``self.get_company()`` to obtain the active tenant.

    If ``request.current_company`` is missing the mixin raises
    :class:`~django.core.exceptions.PermissionDenied` which Django renders
    as a 403 response.
    """

    raise_permission_denied = True

    def get_company(self):
        company = getattr(self.request, "current_company", None)
        if company is None and self.raise_permission_denied:
            raise PermissionDenied("No company context.")
        return company
