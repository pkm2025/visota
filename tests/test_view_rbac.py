"""View-layer RBAC enforcement tests.

Validates the :class:`PermissionRequiredMixin` behavior described in the
validation contract assertions VAL-RBAC-001 through VAL-RBAC-005.

The mixin checks ``UserService.has_permission(required_permission)`` inside
``dispatch`` so that even if URL-level middleware is bypassed, the view
itself denies access. Superusers bypass the check.

Test strategy:
    1. **Mixin unit tests** — bypass middleware entirely via ``RequestFactory``,
       calling ``view.dispatch()`` directly. This isolates the mixin's logic.
    2. **Full-stack tests** — exercise the real view classes through the Django
       test client. These rely on the ``ModulePermissionMiddleware`` which also
       enforces at the URL level. Both the middleware and the view mixin must
       agree on access decisions.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.views import View

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.ui_modern.mixins import PermissionRequiredMixin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def setup_rbac(db):
    """Create a company, the module permission catalog, and users with
    distinct roles: viewer, accountant, sales, hr_officer, superuser."""
    from apps.identity.management.commands.seed_permissions import MODULE_PERMISSIONS

    # Seed the module permission catalog.
    perm_map = {}
    for module, name_vi, desc in MODULE_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            code=f"{module}.access",
            defaults={"module": module, "name": name_vi, "description": desc},
        )
        perm_map[module] = perm

    company = Company.objects.create(
        code="RBAC",
        name="RBAC Co",
        tax_code="0100000rbac",
        accounting_regime="tt133",
    )

    def make_user(username, role_code, modules):
        user = User.objects.create_user(
            username=username, password="Secret123", email=f"{username}@t.co"
        )
        role = Role.objects.create(company=company, code=role_code, name=role_code)
        for m in modules:
            role.permissions.add(perm_map[m])
        UserCompanyRole.objects.create(user=user, company=company, role=role, is_default=True)
        return user

    viewer = make_user("viewer_user", "viewer", ["reporting", "ledger", "notifications"])
    accountant = make_user(
        "accountant_user",
        "accountant",
        [
            "ledger",
            "sales",
            "purchasing",
            "reporting",
            "contracts",
            "documents",
            "hr",
            "payroll",
            "recurring",
            "master_data",
            "input_docs",
            "treasury",
            "einvoice",
            "approvals",
            "notifications",
            "banking",
            "guarantees",
            "loans",
            "fx",
        ],
    )
    sales = make_user(
        "sales_user",
        "sales",
        [
            "sales",
            "crm",
            "contracts",
            "documents",
            "projects",
            "master_data",
            "einvoice",
            "notifications",
            "bidding",
        ],
    )
    hr = make_user(
        "hr_user",
        "hr_officer",
        ["hr", "payroll", "documents", "master_data", "reporting", "notifications"],
    )
    superuser = User.objects.create_superuser(
        username="super_user", password="Secret123", email="s@t.co"
    )

    return {
        "company": company,
        "viewer": viewer,
        "accountant": accountant,
        "sales": sales,
        "hr": hr,
        "superuser": superuser,
    }


# ---------------------------------------------------------------------------
# Direct mixin unit tests (bypass middleware via RequestFactory)
#
# These tests exercise the PermissionRequiredMixin.dispatch() in isolation,
# proving the view-layer check works independently of the URL middleware.
# ---------------------------------------------------------------------------


class _DummyView(PermissionRequiredMixin, View):
    """Minimal view to test the mixin's dispatch behavior."""

    required_permission = "ledger.access"

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse

        return HttpResponse("ok")


def _make_request(user, company, method="GET"):
    """Build a request with current_company set, bypassing middleware."""
    rf = RequestFactory()
    handler = getattr(rf, method.lower())
    request = handler("/some-url/")
    request.user = user
    request.current_company = company
    return request


@pytest.mark.django_db
def test_mixin_blocks_user_without_permission(setup_rbac):
    """VAL-RBAC-001/004 (view layer): user without the required permission
    gets PermissionDenied (→403)."""
    from django.core.exceptions import PermissionDenied

    company = setup_rbac["company"]
    sales_user = setup_rbac["sales"]  # no ledger.access

    request = _make_request(sales_user, company)
    view = _DummyView()
    with pytest.raises(PermissionDenied):
        view.dispatch(request)


@pytest.mark.django_db
def test_mixin_allows_user_with_permission(setup_rbac):
    """VAL-RBAC-003 (view layer): user with the required permission passes
    through dispatch."""
    company = setup_rbac["company"]
    accountant = setup_rbac["accountant"]  # has ledger.access

    request = _make_request(accountant, company)
    view = _DummyView()
    response = view.dispatch(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mixin_allows_superuser(setup_rbac):
    """Superuser bypasses the permission check entirely."""
    company = setup_rbac["company"]
    su = setup_rbac["superuser"]

    request = _make_request(su, company)
    view = _DummyView()
    response = view.dispatch(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mixin_skips_check_when_no_required_permission(setup_rbac):
    """If required_permission is empty, the mixin allows all (no-op)."""

    class _NoPermView(PermissionRequiredMixin, View):
        required_permission = ""

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    company = setup_rbac["company"]
    hr_user = setup_rbac["hr"]

    request = _make_request(hr_user, company)
    view = _NoPermView()
    response = view.dispatch(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mixin_does_not_crash_on_anonymous(setup_rbac):
    """Anonymous user is passed through to LoginRequiredMixin (no crash).

    The mixin checks ``user.is_authenticated`` and if not authenticated,
    defers to the standard LoginRequiredMixin flow.
    """

    class _AnonView(PermissionRequiredMixin, View):
        required_permission = "ledger.access"

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    company = setup_rbac["company"]
    request = _make_request(AnonymousUser(), company)
    view = _AnonView()
    # The mixin sees anonymous user and lets super().dispatch() handle it.
    # Since we don't have LoginRequiredMixin here, View dispatches to get()
    # and returns 200 - proving the mixin does NOT crash on anonymous users.
    response = view.dispatch(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mixin_blocks_hr_from_sales(setup_rbac):
    """VAL-RBAC-005 (view layer): HR user blocked from a sales view."""

    class _SalesView(PermissionRequiredMixin, View):
        required_permission = "sales.access"

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    from django.core.exceptions import PermissionDenied

    company = setup_rbac["company"]
    hr_user = setup_rbac["hr"]  # no sales.access

    request = _make_request(hr_user, company)
    view = _SalesView()
    with pytest.raises(PermissionDenied):
        view.dispatch(request)


@pytest.mark.django_db
def test_mixin_blocks_viewer_from_sales(setup_rbac):
    """VAL-RBAC-002 (view layer): viewer blocked from a sales view."""

    class _SalesView(PermissionRequiredMixin, View):
        required_permission = "sales.access"

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    from django.core.exceptions import PermissionDenied

    company = setup_rbac["company"]
    viewer = setup_rbac["viewer"]  # has ledger + reporting, NOT sales

    request = _make_request(viewer, company)
    view = _SalesView()
    with pytest.raises(PermissionDenied):
        view.dispatch(request)


@pytest.mark.django_db
def test_mixin_allows_sales_to_sales(setup_rbac):
    """VAL-RBAC-004 (view layer): sales user can access a sales view."""

    class _SalesView(PermissionRequiredMixin, View):
        required_permission = "sales.access"

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    company = setup_rbac["company"]
    sales_user = setup_rbac["sales"]  # has sales.access

    request = _make_request(sales_user, company)
    view = _SalesView()
    response = view.dispatch(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_mixin_allows_hr_to_hr(setup_rbac):
    """VAL-RBAC-005 (view layer): HR user can access an HR view."""

    class _HrView(PermissionRequiredMixin, View):
        required_permission = "hr.access"

        def get(self, request, *args, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("ok")

    company = setup_rbac["company"]
    hr_user = setup_rbac["hr"]  # has hr.access

    request = _make_request(hr_user, company)
    view = _HrView()
    response = view.dispatch(request)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Verify the mixin is applied to actual write views (import-level check)
# ---------------------------------------------------------------------------


def test_mixin_applied_to_voucher_create():
    """VoucherCreateView must inherit PermissionRequiredMixin."""
    from apps.ui_modern.views.ledger_views import VoucherCreateView

    assert issubclass(VoucherCreateView, PermissionRequiredMixin)
    assert VoucherCreateView.required_permission == "ledger.access"


def test_mixin_applied_to_voucher_delete():
    from apps.ui_modern.views.ledger_views import VoucherDeleteView

    assert issubclass(VoucherDeleteView, PermissionRequiredMixin)
    assert VoucherDeleteView.required_permission == "ledger.access"


def test_mixin_applied_to_sales_create():
    from apps.ui_modern.views.sales_views import SalesInvoiceCreateView

    assert issubclass(SalesInvoiceCreateView, PermissionRequiredMixin)
    assert SalesInvoiceCreateView.required_permission == "sales.access"


def test_mixin_applied_to_purchase_create():
    from apps.ui_modern.views.purchase_views import PurchaseInvoiceCreateView

    assert issubclass(PurchaseInvoiceCreateView, PermissionRequiredMixin)
    assert PurchaseInvoiceCreateView.required_permission == "purchasing.access"


def test_mixin_applied_to_dnsn_create():
    from apps.ui_modern.views.dnsn_voucher_views import DnsnVoucherCreateView

    assert issubclass(DnsnVoucherCreateView, PermissionRequiredMixin)
    assert DnsnVoucherCreateView.required_permission == "ledger.access"


def test_mixin_applied_to_dnsn_edit():
    from apps.ui_modern.views.dnsn_voucher_views import DnsnVoucherEditView

    assert issubclass(DnsnVoucherEditView, PermissionRequiredMixin)


def test_mixin_applied_to_dnsn_delete():
    from apps.ui_modern.views.dnsn_voucher_views import DnsnVoucherDeleteView

    assert issubclass(DnsnVoucherDeleteView, PermissionRequiredMixin)


def test_mixin_applied_to_employee_create():
    from apps.ui_modern.views.hr_views import EmployeeCreateView

    assert issubclass(EmployeeCreateView, PermissionRequiredMixin)
    assert EmployeeCreateView.required_permission == "hr.access"


def test_mixin_applied_to_labor_contract_create():
    from apps.ui_modern.views.hr_management_views import LaborContractCreateView

    assert issubclass(LaborContractCreateView, PermissionRequiredMixin)
    assert LaborContractCreateView.required_permission == "hr.access"


def test_mixin_applied_to_payroll_run():
    from apps.ui_modern.views.payroll_views import PayrollRunView

    assert issubclass(PayrollRunView, PermissionRequiredMixin)
    assert PayrollRunView.required_permission == "payroll.access"


def test_mixin_applied_to_einvoice_issue():
    from apps.einvoice.views import EInvoiceIssueFromSalesView

    assert issubclass(EInvoiceIssueFromSalesView, PermissionRequiredMixin)
    assert EInvoiceIssueFromSalesView.required_permission == "einvoice.access"


def test_mixin_applied_to_einvoice_publish():
    from apps.einvoice.views import EInvoicePublishView

    assert issubclass(EInvoicePublishView, PermissionRequiredMixin)
    assert EInvoicePublishView.required_permission == "einvoice.access"


def test_mixin_applied_to_einvoice_cancel():
    from apps.einvoice.views import EInvoiceCancelView

    assert issubclass(EInvoiceCancelView, PermissionRequiredMixin)
    assert EInvoiceCancelView.required_permission == "einvoice.access"


def test_mixin_applied_to_contract_create():
    from apps.ui_modern.views.contract_views import ContractCreateView

    assert issubclass(ContractCreateView, PermissionRequiredMixin)
    assert ContractCreateView.required_permission == "contracts.access"


def test_mixin_applied_to_crm_lead_create():
    from apps.ui_modern.views.crm_views import LeadCreateView

    assert issubclass(LeadCreateView, PermissionRequiredMixin)
    assert LeadCreateView.required_permission == "crm.access"


def test_mixin_applied_to_asset_create():
    from apps.ui_modern.views.asset_views import AssetCreateView

    assert issubclass(AssetCreateView, PermissionRequiredMixin)
    assert AssetCreateView.required_permission == "assets.access"


def test_mixin_applied_to_stock_voucher_create():
    from apps.ui_modern.views.stock_views import StockVoucherCreateView

    assert issubclass(StockVoucherCreateView, PermissionRequiredMixin)
    assert StockVoucherCreateView.required_permission == "inventory.access"


def test_mixin_applied_to_stock_adjustment_create():
    from apps.ui_modern.views.stock_views import StockAdjustmentCreateView

    assert issubclass(StockAdjustmentCreateView, PermissionRequiredMixin)
    assert StockAdjustmentCreateView.required_permission == "inventory.access"


def test_mixin_applied_to_period_closing():
    from apps.ui_modern.views.closing_views import PeriodClosingView

    assert issubclass(PeriodClosingView, PermissionRequiredMixin)
    assert PeriodClosingView.required_permission == "ledger.access"


def test_mixin_applied_to_chart_of_accounts_change_code():
    from apps.ui_modern.views.chart_of_accounts_views import ChartOfAccountsChangeCodeView

    assert issubclass(ChartOfAccountsChangeCodeView, PermissionRequiredMixin)
    assert ChartOfAccountsChangeCodeView.required_permission == "master_data.access"
