"""Module-level permission middleware.

Maps URL path prefix → <module>.access permission and enforces on every
request. Superusers bypass. Users without permission are redirected to
/no-access/. Auth/login/static/media paths are exempt.
"""

from django.urls import reverse
from django.shortcuts import redirect

from apps.identity.services import UserService


PATH_MODULE_MAP = [
    ("/modern/vouchers/", "ledger"),
    ("/modern/closing/", "ledger"),
    ("/modern/chart-of-accounts/", "master_data"),
    ("/modern/customers/", "sales"),
    ("/modern/vendors/", "purchasing"),
    ("/modern/products/", "master_data"),
    ("/modern/sales-invoices/", "sales"),
    ("/modern/purchase-invoices/", "purchasing"),
    ("/modern/stock-vouchers/", "inventory"),
    ("/modern/inventory/", "inventory"),
    ("/modern/assets/", "assets"),
    ("/modern/employees/", "hr"),
    ("/modern/labor-contracts/", "hr"),
    ("/modern/leave/", "hr"),
    ("/modern/dependents/", "hr"),
    ("/modern/insurance/", "hr"),
    ("/modern/payroll/", "payroll"),
    ("/modern/reports/", "reporting"),
    ("/modern/contracts/", "contracts"),
    ("/modern/contract-templates/", "contracts"),
    ("/modern/input-invoices/", "input_docs"),
    ("/modern/recurring/", "recurring"),
    ("/modern/projects/", "projects"),
    ("/modern/crm/", "crm"),
    ("/modern/treasury/", "treasury"),
    ("/modern/banking/", "banking"),
    ("/modern/guarantees/", "guarantees"),
    ("/modern/loans/", "loans"),
    ("/modern/bidding/", "bidding"),
    ("/modern/budget/", "budget"),
    ("/modern/cash-flow/", "budget"),
    ("/modern/fx/", "fx"),
    ("/modern/einvoices/", "einvoice"),
    ("/modern/approvals/", "approvals"),
]

EXEMPT_PREFIXES = (
    "/auth/",
    "/admin/",  # Django admin
    "/no-access/",
    "/static/",
    "/media/",
    "/api/",
    "/health",
    "/__debug__/",
)


def _resolve_module(path: str):
    """Return required module code for path, or None if no requirement."""
    if not path.startswith("/modern/"):
        return None
    # Dashboard is always allowed for authenticated users
    if path == "/modern/" or path.startswith("/modern/dashboard"):
        return None
    for prefix, module in PATH_MODULE_MAP:
        if path.startswith(prefix):
            return module
    return None


class ModulePermissionMiddleware:
    """Enforce <module>.access permission based on URL path."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if (
            not user
            or not user.is_authenticated
            or not request.path.startswith("/modern/")
        ):
            return self.get_response(request)

        # Ensure current_company is set (session may not have current_company_id).
        # This also benefits downstream context processors that read it.
        if not getattr(request, "current_company", None):
            from apps.core.models import Company

            company = Company.objects.first()
            if company:
                request.current_company = company

        # Superusers bypass permission checks once company is set
        if user.is_superuser:
            return self.get_response(request)

        for ex in EXEMPT_PREFIXES:
            if request.path.startswith(ex):
                return self.get_response(request)

        module = _resolve_module(request.path)
        if module is None:
            return self.get_response(request)

        company = getattr(request, "current_company", None)
        if not company:
            return self.get_response(request)

        service = UserService(user, company)
        if not service.has_permission(f"{module}.access"):
            # Allow GET redirect; block write methods with 403
            if request.method == "GET":
                return redirect("/no-access/")
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden(
                f"Bạn không có quyền truy cập module: {module}"
            )

        return self.get_response(request)
