"""Mixins for multi-tenant isolation and RBAC enforcement in ui_modern views.

The :class:`CompanyRequiredMixin` enforces that every view resolves the
active company from ``request.current_company`` (set by
``TenantMiddleware`` from ``session["current_company_id"]``). When no
company is set, the view raises :class:`~django.core.exceptions.PermissionDenied`
rather than silently falling back to ``Company.objects.first()``.

The :class:`PermissionRequiredMixin` provides view-layer RBAC enforcement
that complements the URL-level ``ModulePermissionMiddleware``. Each write
view (Create/Update/Delete/Post/etc.) sets ``required_permission`` to a
module-level permission code (e.g. ``"ledger.access"``). The mixin checks
``UserService.has_permission()`` in ``dispatch()`` and returns 403 if the
user lacks the permission. Superusers bypass the check.

Usage::

    class MyListView(LoginRequiredMixin, CompanyRequiredMixin, ListView):
        def get_queryset(self):
            company = self.get_company()
            return MyModel.objects.filter(company=company)

    class MyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
        required_permission = "sales.access"

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


class PermissionRequiredMixin:
    """Mixin that enforces module-level RBAC at the view ``dispatch`` layer.

    Set ``required_permission`` on the view to a permission code (typically
    ``"<module>.access"``). The mixin calls
    ``UserService(user, company).has_permission(required_permission)`` in
    :meth:`dispatch`. If the check fails, Django renders a 403 response
    (via :class:`~django.core.exceptions.PermissionDenied`).

    Superusers bypass the check entirely (handled inside
    :meth:`UserService.has_permission`).

    This mixin must be placed BEFORE the view class in the MRO so that
    ``dispatch`` is resolved from this mixin and can call ``super().dispatch()``
    to delegate to the underlying view (``LoginRequiredMixin``,
    ``CreateView``, ``View``, etc.).

    Usage::

        class VoucherCreateView(
            LoginRequiredMixin, PermissionRequiredMixin, View
        ):
            required_permission = "ledger.access"
    """

    #: Permission code required to access this view. Subclasses MUST set this.
    required_permission: str = ""

    def dispatch(self, request, *args, **kwargs):
        if self.required_permission:
            user = getattr(request, "user", None)
            company = getattr(request, "current_company", None)
            if user is None or not user.is_authenticated:
                # Let LoginRequiredMixin handle the auth redirect.
                return super().dispatch(request, *args, **kwargs)

            from apps.identity.services import UserService

            if not UserService(user, company).has_permission(self.required_permission):
                raise PermissionDenied(f"Missing permission: {self.required_permission}")
        return super().dispatch(request, *args, **kwargs)
