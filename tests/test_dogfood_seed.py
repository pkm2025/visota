"""Tests for seed_dogfood management command.

Verifies the 3-company / 21-user / multi-regime dogfooding dataset.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.core.models import Company
from apps.hr.models import Employee, LaborContract
from apps.identity.management.commands.seed_permissions import SYSTEM_ROLES
from apps.identity.models import Role, UserCompanyRole
from apps.ledger.models import AccountingVoucher, DnsnVoucher
from apps.master_data.models import Customer, Product, Vendor
from apps.payroll.models import PayrollRun
from apps.projects.models import Project
from apps.purchasing.models import PurchaseInvoice
from apps.sales.models import SalesInvoice

User = get_user_model()

COMPANY_CODES = ["DF-SG", "DF-HN", "DF-AB"]
COMPANY_PREFIXES = ["sg", "hn", "ab"]
ROLE_SUFFIXES = ["admin", "ketoantruong", "ketoan", "sales", "muahang", "nhansu", "viewer"]

# Build a role-code -> expected module list lookup from SYSTEM_ROLES for tests.
EXPECTED_ROLE_MODULES: dict[str, list[str]] = {
    role_code: modules for role_code, _name, _desc, modules, _is_system in SYSTEM_ROLES
}

# seed_dogfood only creates these 7 roles per company (subset of SYSTEM_ROLES).
DOGFOOD_ROLE_CODES = {
    "admin",
    "chief_accountant",
    "accountant",
    "sales",
    "purchaser",
    "hr_officer",
    "viewer",
}


def _run_seed():
    """Run the seed command and return its stdout."""
    out = StringIO()
    call_command("seed_dogfood", stdout=out)
    return out.getvalue()


def test_three_companies_with_correct_regimes(db):
    _run_seed()
    sg = Company.objects.get(code="DF-SG")
    hn = Company.objects.get(code="DF-HN")
    ab = Company.objects.get(code="DF-AB")
    assert sg.accounting_regime == "tt133"
    assert hn.accounting_regime == "tt58"
    assert ab.accounting_regime == "tt58"
    assert Company.objects.filter(code__in=COMPANY_CODES).count() == 3


def test_tt58_tax_groups(db):
    _run_seed()
    hn = Company.objects.get(code="DF-HN")
    ab = Company.objects.get(code="DF-AB")
    # Hà Nội: GTGT% + TNDN tinh thue = Group 2
    assert hn.vat_method == "ty_le_phan_tram"
    assert hn.tndn_method == "tinh_thue"
    assert hn.tax_method_group == 2
    # An Bình: ho_kinh_doanh, GTGT% + TNDN% = Group 1
    assert ab.entity_type == "ho_kinh_doanh"
    assert ab.tax_method_group == 1


def test_21_users_exist(db):
    _run_seed()
    for prefix in COMPANY_PREFIXES:
        for suffix in ROLE_SUFFIXES:
            username = f"{prefix}_{suffix}"
            assert User.objects.filter(username=username).exists(), f"Missing user {username}"
    assert (
        User.objects.filter(
            username__in=[f"{p}_{s}" for p in COMPANY_PREFIXES for s in ROLE_SUFFIXES]
        ).count()
        == 21
    )


def test_each_user_has_correct_role(db):
    _run_seed()
    # Map suffix to expected role code
    suffix_to_role = {
        "admin": "admin",
        "ketoantruong": "chief_accountant",
        "ketoan": "accountant",
        "sales": "sales",
        "muahang": "purchaser",
        "nhansu": "hr_officer",
        "viewer": "viewer",
    }
    for prefix, company_code in zip(COMPANY_PREFIXES, COMPANY_CODES, strict=True):
        company = Company.objects.get(code=company_code)
        for suffix, role_code in suffix_to_role.items():
            user = User.objects.get(username=f"{prefix}_{suffix}")
            assert UserCompanyRole.objects.filter(
                user=user, company=company, role__code=role_code
            ).exists(), f"User {user.username} missing role '{role_code}' at {company_code}"


def test_master_data_per_company(db):
    _run_seed()
    for code in COMPANY_CODES:
        company = Company.objects.get(code=code)
        assert Customer.objects.filter(company=company).count() == 3, (
            f"{code} should have 3 customers"
        )
        assert Vendor.objects.filter(company=company).count() == 3, f"{code} should have 3 vendors"
        assert Product.objects.filter(company=company).count() == 5, (
            f"{code} should have 5 products"
        )
        assert Employee.objects.filter(company=company).count() == 2, (
            f"{code} should have 2 employees"
        )
        assert Project.objects.filter(company=company).count() == 1, f"{code} should have 1 project"


def test_master_data_isolated_per_company(db):
    _run_seed()
    """Each company's master data must be isolated (multi-tenant)."""
    sg = Company.objects.get(code="DF-SG")
    hn = Company.objects.get(code="DF-HN")
    sg_customers = set(Customer.objects.filter(company=sg).values_list("code", flat=True))
    hn_customers = set(Customer.objects.filter(company=hn).values_list("code", flat=True))
    # Same codes (KH001...) but different PKs / companies
    assert sg_customers == hn_customers
    assert (
        Customer.objects.filter(company=sg).first().id
        != Customer.objects.filter(company=hn).first().id
    )


def test_tt133_transactions(db):
    _run_seed()
    sg = Company.objects.get(code="DF-SG")
    assert SalesInvoice.objects.filter(company=sg).count() == 2
    assert PurchaseInvoice.objects.filter(company=sg).count() == 1
    # 3 posted GL vouchers: 2 phiếu thu + 1 phiếu chi
    vouchers = AccountingVoucher.objects.filter(company=sg)
    assert vouchers.count() == 3
    assert vouchers.filter(voucher_type=AccountingVoucher.VoucherType.CASH_RECEIPT).count() == 2
    assert vouchers.filter(voucher_type=AccountingVoucher.VoucherType.CASH_PAYMENT).count() == 1
    for v in vouchers:
        assert v.is_posted


def test_tt58_dnsn_vouchers(db):
    _run_seed()
    hn = Company.objects.get(code="DF-HN")
    vouchers = DnsnVoucher.objects.filter(company=hn)
    assert vouchers.count() == 2
    assert vouchers.filter(voucher_type=DnsnVoucher.VoucherType.PHIEU_THU).exists()
    assert vouchers.filter(voucher_type=DnsnVoucher.VoucherType.PHIEU_CHI).exists()
    for v in vouchers:
        assert v.is_posted


def test_hr_contracts_and_payroll(db):
    _run_seed()
    for code in COMPANY_CODES:
        company = Company.objects.get(code=code)
        assert LaborContract.objects.filter(company=company).count() == 2, (
            f"{code} should have 2 labor contracts"
        )
        assert PayrollRun.objects.filter(company=company).count() == 1, (
            f"{code} should have 1 payroll run"
        )
        run = PayrollRun.objects.get(company=company)
        assert run.status == PayrollRun.Status.CALCULATED
        assert run.lines.count() == 2


def test_seed_is_idempotent(db):
    """Running the command twice should not duplicate data."""
    _run_seed()
    _run_seed()
    assert Company.objects.filter(code__in=COMPANY_CODES).count() == 3
    assert (
        User.objects.filter(
            username__in=[f"{p}_{s}" for p in COMPANY_PREFIXES for s in ROLE_SUFFIXES]
        ).count()
        == 21
    )
    sg = Company.objects.get(code="DF-SG")
    assert SalesInvoice.objects.filter(company=sg).count() == 2
    assert PurchaseInvoice.objects.filter(company=sg).count() == 1


def test_sample_data_accessible_from_company_context(db):
    """Master data created under a company is retrievable via company FK."""
    _run_seed()
    sg = Company.objects.get(code="DF-SG")
    # via related_name
    assert sg.customers.count() == 3
    assert sg.vendors.count() == 3
    assert sg.products.count() == 5
    assert sg.employees.count() == 2
    assert sg.projects.count() == 1
    # transactions
    assert sg.sales_invoices.count() == 2
    assert sg.purchase_invoices.count() == 1
    assert sg.vouchers.count() == 3

    hn = Company.objects.get(code="DF-HN")
    assert hn.dnsn_vouchers.count() == 2


# ---------------------------------------------------------------------------
# Permission assignment tests (VAL-SEED-001, VAL-SEED-002)
# ---------------------------------------------------------------------------


def test_seed_dogfood_assigns_permissions_to_all_company_roles(db):
    """VAL-SEED-001: each company's roles have correct module permissions per SYSTEM_ROLES."""
    _run_seed()
    for company_code in COMPANY_CODES:
        company = Company.objects.get(code=company_code)
        for role_code in DOGFOOD_ROLE_CODES:
            expected_modules = EXPECTED_ROLE_MODULES[role_code]
            role = Role.objects.get(company=company, code=role_code)
            actual_codes = set(role.permissions.values_list("code", flat=True))
            for module in expected_modules:
                assert f"{module}.access" in actual_codes, (
                    f"{company_code} role '{role_code}' missing permission '{module}.access'"
                )


def test_seed_dogfood_role_permissions_match_exactly(db):
    """VAL-SEED-001: role permissions match the SYSTEM_ROLES module list exactly (no extras)."""
    _run_seed()
    for company_code in COMPANY_CODES:
        company = Company.objects.get(code=company_code)
        for role_code in DOGFOOD_ROLE_CODES:
            expected_modules = EXPECTED_ROLE_MODULES[role_code]
            role = Role.objects.get(company=company, code=role_code)
            actual_codes = set(role.permissions.values_list("code", flat=True))
            expected_codes = {f"{m}.access" for m in expected_modules}
            assert actual_codes == expected_codes, (
                f"{company_code} role '{role_code}': permission mismatch. "
                f"Expected {sorted(expected_codes)}, got {sorted(actual_codes)}"
            )


def test_viewer_permissions_are_limited(db):
    """VAL-SEED-002: sg_viewer has only reporting.access, ledger.access, notifications.access."""
    _run_seed()
    sg = Company.objects.get(code="DF-SG")
    viewer = User.objects.get(username="sg_viewer")
    ucr = UserCompanyRole.objects.get(user=viewer, company=sg)
    granted = set(ucr.role.permissions.values_list("code", flat=True))
    expected = {"reporting.access", "ledger.access", "notifications.access"}
    assert granted == expected, (
        f"sg_viewer permissions mismatch: expected {sorted(expected)}, got {sorted(granted)}"
    )


def test_all_21_users_have_permissions_via_role(db):
    """VAL-SEED-002: all 21 dogfood users have at least one permission via their role."""
    _run_seed()
    suffix_to_role = {
        "admin": "admin",
        "ketoantruong": "chief_accountant",
        "ketoan": "accountant",
        "sales": "sales",
        "muahang": "purchaser",
        "nhansu": "hr_officer",
        "viewer": "viewer",
    }
    for prefix, company_code in zip(COMPANY_PREFIXES, COMPANY_CODES, strict=True):
        company = Company.objects.get(code=company_code)
        for suffix, role_code in suffix_to_role.items():
            user = User.objects.get(username=f"{prefix}_{suffix}")
            ucr = UserCompanyRole.objects.get(user=user, company=company)
            perm_count = ucr.role.permissions.count()
            assert perm_count > 0, (
                f"{user.username} role '{role_code}' has zero permissions at {company_code}"
            )


def test_permissions_assigned_after_idempotent_reseed(db):
    """Permissions remain correct after running seed_dogfood twice (idempotent)."""
    _run_seed()
    _run_seed()
    sg = Company.objects.get(code="DF-SG")
    for role_code in DOGFOOD_ROLE_CODES:
        expected_modules = EXPECTED_ROLE_MODULES[role_code]
        role = Role.objects.get(company=sg, code=role_code)
        actual_codes = set(role.permissions.values_list("code", flat=True))
        expected_codes = {f"{m}.access" for m in expected_modules}
        assert actual_codes == expected_codes, (
            f"After reseed, role '{role_code}' permissions mismatch: "
            f"expected {sorted(expected_codes)}, got {sorted(actual_codes)}"
        )
