"""Multi-tenant isolation tests.

Validates VAL-SEC-001 through VAL-SEC-005:

* VAL-SEC-001 — No ``Company.objects.first()`` in ``apps/ui_modern/views``.
* VAL-SEC-002 — ListView ``get_queryset()`` filters by company.
* VAL-SEC-003 — ``get_object_or_404`` scoped by company.
* VAL-SEC-004 — ``ContractTemplate`` inherits ``CompanyOwnedModel``.
* VAL-SEC-005 — ``CompanyRequiredMixin`` raises ``PermissionDenied``
  when ``request.current_company`` is missing.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from apps.core.models import Company
from apps.identity.models import Role
from apps.ui_modern.mixins import CompanyRequiredMixin, require_current_company

# ---------------------------------------------------------------------------
# Source-level scans (VAL-SEC-001)
# ---------------------------------------------------------------------------

VIEWS_DIR = Path(__file__).resolve().parent.parent / "apps" / "ui_modern" / "views"


def _walk_view_files() -> list[Path]:
    return [p for p in VIEWS_DIR.rglob("*.py") if p.name != "__init__.py"]


def test_val_sec_001_no_company_objects_first_in_views():
    """VAL-SEC-001: no Company.objects.first() calls remain in views/."""
    pattern = re.compile(r"Company\.objects\.first\(\)")
    offenders: list[str] = []
    for path in _walk_view_files():
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(VIEWS_DIR)}:{line_no}")
    assert not offenders, "Company.objects.first() still referenced in views:\n  " + "\n  ".join(
        offenders
    )


# ---------------------------------------------------------------------------
# CompanyRequiredMixin behavior (VAL-SEC-005)
# ---------------------------------------------------------------------------


class _StubView(CompanyRequiredMixin):
    pass


def test_val_sec_005_mixin_returns_company_when_set():
    factory = RequestFactory()
    request = factory.get("/")
    company = object()  # sentinel; any truthy object is fine
    request.current_company = company

    view = _StubView()
    view.request = request
    assert view.get_company() is company


def test_val_sec_005_mixin_raises_permission_denied_when_missing():
    factory = RequestFactory()
    request = factory.get("/")
    # current_company intentionally not set
    if hasattr(request, "current_company"):
        del request.current_company

    view = _StubView()
    view.request = request
    with pytest.raises(PermissionDenied):
        view.get_company()


def test_require_current_company_helper_returns_company():
    factory = RequestFactory()
    request = factory.get("/")
    company = object()
    request.current_company = company
    assert require_current_company(request) is company


def test_require_current_company_helper_raises_when_missing():
    factory = RequestFactory()
    request = factory.get("/")
    if hasattr(request, "current_company"):
        del request.current_company
    with pytest.raises(PermissionDenied):
        require_current_company(request)


# ---------------------------------------------------------------------------
# ContractTemplate company FK (VAL-SEC-004)
# ---------------------------------------------------------------------------


def test_val_sec_004_contract_template_inherits_company_owned_model():
    """ContractTemplate must inherit CompanyOwnedModel and expose a company FK."""
    from apps.contracts.models import ContractTemplate
    from apps.core.managers import CompanyOwnedModel

    assert issubclass(ContractTemplate, CompanyOwnedModel)
    # The FK field must exist on the model
    field = ContractTemplate._meta.get_field("company")
    assert field.is_relation
    assert field.many_to_one


def test_val_sec_004_contract_template_company_fk_not_null():
    """The company FK on ContractTemplate must be NOT NULL post-migration."""
    from apps.contracts.models import ContractTemplate

    field = ContractTemplate._meta.get_field("company")
    assert field.null is False, "ContractTemplate.company must be NOT NULL"


def test_val_sec_004_contract_template_unique_together_company_code():
    """code is unique within company, not globally."""
    from apps.contracts.models import ContractTemplate

    unique_together = ContractTemplate._meta.unique_together
    assert {("company", "code")} in unique_together or (
        "company",
        "code",
    ) in {tuple(ut) for ut in unique_together}


def test_val_sec_004_contract_template_scoped_lookup(db, company):
    """Two companies can each have a template with the same code."""
    from apps.contracts.models import ContractTemplate

    other = Company.objects.create(
        code="MT2",
        name="Multi-Tenant Co 2",
        tax_code="0109998888",
        accounting_regime="tt133",
    )

    tpl_a = ContractTemplate.objects.create(
        company=company,
        code="sale_v1",
        name="Sale template A",
        contract_type="sale",
        template_html="<p>A</p>",
    )
    tpl_b = ContractTemplate.objects.create(
        company=other,
        code="sale_v1",  # same code, different company — must succeed
        name="Sale template B",
        contract_type="sale",
        template_html="<p>B</p>",
    )

    assert tpl_a.company_id == company.id
    assert tpl_b.company_id == other.id
    assert tpl_a.pk != tpl_b.pk


# ---------------------------------------------------------------------------
# ListView queryset isolation (VAL-SEC-002)
# ---------------------------------------------------------------------------


def _attach_company(request, company):
    request.current_company = company
    return request


@pytest.fixture
def second_company(db):
    return Company.objects.create(
        code="MT2",
        name="Multi-Tenant Co 2",
        tax_code="0109997777",
        accounting_regime="tt133",
    )


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    return user_model.objects.create_superuser(
        username="mt_admin", password="Secret123", email="mt@test.local"
    )


def test_val_sec_002_voucher_list_filters_by_company(rf, company, second_company, admin_user):
    """VoucherListView.get_queryset() filters by current_company."""
    from apps.ledger.models import AccountingVoucher

    AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="V-A",
        voucher_type="journal",
        voucher_date=date(2026, 6, 1),
        status=AccountingVoucher.Status.DRAFT,
    )
    AccountingVoucher.objects.create(
        company=second_company,
        fiscal_year=2026,
        period=6,
        voucher_no="V-B",
        voucher_type="journal",
        voucher_date=date(2026, 6, 1),
        status=AccountingVoucher.Status.DRAFT,
    )

    from apps.ui_modern.views.ledger_views import VoucherListView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = VoucherListView()
    view.request = request
    qs = view.get_queryset()

    nos = {v.voucher_no for v in qs}
    assert "V-A" in nos
    assert "V-B" not in nos


def test_val_sec_002_contract_list_filters_by_company(rf, company, second_company, admin_user):
    """ContractListView.get_queryset() filters by current_company."""
    from apps.contracts.models import Contract

    Contract.objects.create(
        company=company,
        contract_no="C-A",
        contract_date=date(2026, 6, 1),
        party_name="A",
    )
    Contract.objects.create(
        company=second_company,
        contract_no="C-B",
        contract_date=date(2026, 6, 1),
        party_name="B",
    )

    from apps.ui_modern.views.contract_views import ContractListView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = ContractListView()
    view.request = request
    qs = view.get_queryset()

    nos = {c.contract_no for c in qs}
    assert "C-A" in nos
    assert "C-B" not in nos


def test_val_sec_002_asset_list_filters_by_company(rf, company, second_company, admin_user):
    """AssetListView.get_queryset() filters by current_company."""
    from apps.assets.models import (
        AssetCategory,
        AssetUsingDepartment,
        FixedAsset,
    )

    cat_a = AssetCategory.objects.create(company=company, code="CAT-A", name="CAT A")
    cat_b = AssetCategory.objects.create(company=second_company, code="CAT-B", name="CAT B")
    dept_a = AssetUsingDepartment.objects.create(company=company, code="DEPT-A", name="Dept A")
    dept_b = AssetUsingDepartment.objects.create(
        company=second_company, code="DEPT-B", name="Dept B"
    )

    FixedAsset.objects.create(
        company=company,
        asset_code="FA-A",
        asset_name="A",
        category=cat_a,
        using_department=dept_a,
        original_cost=Decimal("1000"),
        start_date=date(2026, 1, 1),
    )
    FixedAsset.objects.create(
        company=second_company,
        asset_code="FA-B",
        asset_name="B",
        category=cat_b,
        using_department=dept_b,
        original_cost=Decimal("1000"),
        start_date=date(2026, 1, 1),
    )

    from apps.ui_modern.views.asset_views import AssetListView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = AssetListView()
    view.request = request
    qs = view.get_queryset()

    codes = {a.asset_code for a in qs}
    assert "FA-A" in codes
    assert "FA-B" not in codes


def test_val_sec_002_customer_list_filters_by_company(rf, company, second_company, admin_user):
    """CustomerListView.get_queryset() filters by current_company."""
    from apps.master_data.models import Customer

    Customer.objects.create(company=company, code="CUST-A", name="A")
    Customer.objects.create(company=second_company, code="CUST-B", name="B")

    from apps.ui_modern.views.customer_views import CustomerListView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = CustomerListView()
    view.request = request
    qs = view.get_queryset()

    codes = {c.code for c in qs}
    assert "CUST-A" in codes
    assert "CUST-B" not in codes


def test_val_sec_002_chart_of_accounts_filters_by_company(rf, company, second_company, admin_user):
    """ChartOfAccountsListView.get_queryset() filters by current_company."""
    from apps.master_data.models import AccountType, ChartOfAccounts

    at = AccountType.objects.create(code=1, name="Tài sản", balance_type="debit", category="asset")
    ChartOfAccounts.objects.create(
        company=company,
        account_code="1111",
        account_name="A",
        account_level=2,
        account_type=at,
    )
    ChartOfAccounts.objects.create(
        company=second_company,
        account_code="2222",
        account_name="B",
        account_level=2,
        account_type=at,
    )

    from apps.ui_modern.views.chart_of_accounts_views import (
        ChartOfAccountsListView,
    )

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = ChartOfAccountsListView()
    view.request = request
    qs = view.get_queryset()

    codes = {a.account_code for a in qs}
    assert "1111" in codes
    assert "2222" not in codes


# ---------------------------------------------------------------------------
# get_object_or_404 scoping (VAL-SEC-003)
# ---------------------------------------------------------------------------


def test_val_sec_003_voucher_detail_404_cross_tenant(rf, company, second_company, admin_user):
    """VoucherDetailView raises 404 for another company's voucher pk."""
    from apps.ledger.models import AccountingVoucher

    other_voucher = AccountingVoucher.objects.create(
        company=second_company,
        fiscal_year=2026,
        period=6,
        voucher_no="X-V",
        voucher_type="journal",
        voucher_date=date(2026, 6, 1),
        status=AccountingVoucher.Status.DRAFT,
    )

    from apps.ui_modern.views.ledger_views import VoucherDetailView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = VoucherDetailView()
    view.request = request
    view.kwargs = {"pk": other_voucher.pk}
    qs = view.get_queryset()
    assert not qs.filter(pk=other_voucher.pk).exists()


def test_val_sec_003_contract_detail_404_cross_tenant(rf, company, second_company, admin_user):
    """ContractDetailView queryset excludes other companies' contracts."""
    from apps.contracts.models import Contract

    other_contract = Contract.objects.create(
        company=second_company,
        contract_no="X-C",
        contract_date=date(2026, 6, 1),
        party_name="X",
    )

    from apps.ui_modern.views.contract_views import ContractDetailView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = ContractDetailView()
    view.request = request
    qs = view.get_queryset()
    assert not qs.filter(pk=other_contract.pk).exists()


def test_val_sec_003_admin_role_edit_404_cross_tenant(rf, company, second_company, admin_user):
    """AdminRoleEditView must not load a role owned by another company."""
    from django.http import Http404

    other_role = Role.objects.create(company=second_company, code="x-role", name="X Role")

    from apps.ui_modern.views.admin_views import AdminRoleEditView

    request = rf.get("/")
    request.user = admin_user
    _attach_company(request, company)

    view = AdminRoleEditView()
    view.request = request
    view.kwargs = {"pk": other_role.pk}

    with pytest.raises(Http404):
        view.get(request, pk=other_role.pk)


# ---------------------------------------------------------------------------
# ChartOfAccountsChangeCodeView company scoping (VAL-SEC-003 / HIGH-03)
# ---------------------------------------------------------------------------


def test_change_code_cascade_does_not_leak_cross_company(company, second_company, admin_user):
    """Changing a code in one company must not touch another company's VoucherLines."""
    from django.test import Client

    from apps.ledger.models import AccountingVoucher, VoucherLine
    from apps.master_data.models import AccountType, ChartOfAccounts

    at = AccountType.objects.create(code=1, name="Tài sản", balance_type="debit", category="asset")

    # Both companies use the same account_code (1111)
    my_acc = ChartOfAccounts.objects.create(
        company=company,
        account_code="1111",
        account_name="Mine",
        account_level=2,
        account_type=at,
        is_posting_account=True,
    )
    ChartOfAccounts.objects.create(
        company=second_company,
        account_code="1111",
        account_name="Theirs",
        account_level=2,
        account_type=at,
        is_posting_account=True,
    )

    # Both have a voucher line using 1111
    v_mine = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="VM",
        voucher_type="journal",
        voucher_date=date(2026, 6, 1),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(voucher=v_mine, line_no=1, account_code="1111", debit_vnd=100)
    VoucherLine.objects.create(voucher=v_mine, line_no=2, account_code="331", credit_vnd=100)

    v_theirs = AccountingVoucher.objects.create(
        company=second_company,
        fiscal_year=2026,
        period=6,
        voucher_no="VT",
        voucher_type="journal",
        voucher_date=date(2026, 6, 1),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(voucher=v_theirs, line_no=1, account_code="1111", debit_vnd=200)
    VoucherLine.objects.create(voucher=v_theirs, line_no=2, account_code="331", credit_vnd=200)

    client = Client()
    client.force_login(admin_user)
    session = client.session
    session["current_company_id"] = company.id
    session.save()

    resp = client.post(
        f"/modern/chart-of-accounts/{my_acc.pk}/change-code/",
        data={"new_code": "9999"},
    )
    assert resp.status_code == 302

    # The other company's voucher line at 1111 must be untouched
    assert VoucherLine.objects.filter(voucher__company=second_company, account_code="1111").exists()
    assert not VoucherLine.objects.filter(
        voucher__company=second_company, account_code="9999"
    ).exists()


# ---------------------------------------------------------------------------
# pytest request factory fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def rf():
    return RequestFactory()
