"""Dogfood tests for Sales/CRM and HR/Payroll flows.

Tests two primary user flows against the seed_dogfood dataset:
  Flow A — Sales rep (sg_sales) creating invoices + CRM leads
  Flow B — HR officer (sg_nhansu) managing employees + payroll
  Flow C — Admin (sg_admin) cross-module access + company switch

Prerequisites:
  - ``seed_dogfood`` creates companies/users/master-data/transactions.
  - ``seed_permissions`` creates the permission catalog + system role templates.
  - A fixture then syncs permissions onto the per-company dogfood roles so
    that ModulePermissionMiddleware can enforce denials correctly.
"""

from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.crm.models import CRMLead
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.identity.services import UserService

# ---------------------------------------------------------------------------
# Role → module mapping (mirrors SYSTEM_ROLES in seed_permissions.py)
# ---------------------------------------------------------------------------

ROLE_MODULES = {
    "admin": None,  # all modules — handled specially
    "chief_accountant": None,  # all modules
    "accountant": [
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
    "sales": [
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
    "purchaser": [
        "purchasing",
        "inventory",
        "documents",
        "master_data",
        "input_docs",
        "notifications",
    ],
    "hr_officer": [
        "hr",
        "payroll",
        "documents",
        "master_data",
        "reporting",
        "notifications",
    ],
    "viewer": ["reporting", "ledger", "notifications"],
}

ALL_MODULES = [
    "master_data",
    "ledger",
    "sales",
    "purchasing",
    "inventory",
    "assets",
    "hr",
    "payroll",
    "reporting",
    "documents",
    "contracts",
    "input_docs",
    "recurring",
    "projects",
    "crm",
    "treasury",
    "banking",
    "guarantees",
    "loans",
    "bidding",
    "budget",
    "fx",
    "einvoice",
    "approvals",
    "notifications",
    "pkm",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dogfood_data(db):
    """Seed dogfood companies/users/data + sync permissions onto roles."""
    out = StringIO()
    call_command("seed_dogfood", stdout=out)

    # Seed permission catalog + system role templates (for Company.objects.first()).
    call_command("seed_permissions", stdout=StringIO())

    # Sync permissions onto the per-company dogfood roles.
    _sync_role_permissions()

    # Clear any cached permissions so middleware sees the fresh state.
    cache.clear()
    return out.getvalue()


def _sync_role_permissions():
    """Assign the correct module permissions to every dogfood-created role."""
    for company in Company.objects.filter(code__in=["DF-SG", "DF-HN", "DF-AB"]):
        for role in Role.objects.filter(company=company):
            modules = ROLE_MODULES.get(role.code)
            if modules is None:
                # admin / chief_accountant → all modules
                modules = ALL_MODULES
            perm_codes = [f"{m}.access" for m in modules]
            perms = Permission.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)


def _login_and_set_company(client: Client, username: str, company_code: str) -> Company:
    """Log in as *username* and set the session company to *company_code*.

    Returns the Company instance.
    """
    user = User.objects.get(username=username)
    company = Company.objects.get(code=company_code)

    # Ensure the user has a UserCompanyRole for this company (dogfood seed
    # already creates it, but be defensive for cross-company tests).
    UserCompanyRole.objects.get_or_create(
        user=user,
        company=company,
        defaults={"role": Role.objects.filter(company=company).first()},
    )

    client.force_login(user)
    client.session["current_company_id"] = company.id
    client.session.save()

    # Invalidate cached perms so the new company context takes effect.
    UserService(user, company).invalidate_cache()
    return company


# ---------------------------------------------------------------------------
# Flow A — Sales Rep (sg_sales)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_flow_a_sales_rep_sales_and_crm(dogfood_data):
    """Sales rep can access sales invoices, CRM leads, contracts, einvoice
    but is denied ledger and HR."""
    client = Client()
    _login_and_set_company(client, "sg_sales", "DF-SG")

    # A2. Sales invoice list → 200
    r = client.get("/modern/sales-invoices/")
    assert r.status_code == 200, f"sales-invoices returned {r.status_code}"

    # A3. CRM leads → 200
    r = client.get("/modern/crm/leads/")
    assert r.status_code == 200, f"crm/leads returned {r.status_code}"

    # A4. Create a new CRM lead
    lead_count_before = CRMLead.objects.filter(company__code="DF-SG").count()
    r = client.post(
        "/modern/crm/leads/new/",
        data={
            "code": "DOGFOOD-LEAD-001",
            "full_name": "Nguyễn Văn Demo",
            "company_name": "Công ty Dogfood Test",
            "email": "demo@dogfood.test",
            "phone": "0901234567",
            "source": "website",
            "status": "new",
        },
    )
    assert r.status_code == 302, f"lead create returned {r.status_code}"
    lead_count_after = CRMLead.objects.filter(company__code="DF-SG").count()
    assert lead_count_after == lead_count_before + 1, "Lead was not created"
    new_lead = CRMLead.objects.get(code="DOGFOOD-LEAD-001")
    assert new_lead.full_name == "Nguyễn Văn Demo"
    assert new_lead.company.code == "DF-SG"

    # A5. Contracts → 200
    r = client.get("/modern/contracts/")
    assert r.status_code == 200, f"contracts returned {r.status_code}"

    # A6. Einvoice → 200
    r = client.get("/modern/einvoices/")
    assert r.status_code == 200, f"einvoices returned {r.status_code}"

    # A7. Ledger → denied (no permission)
    r = client.get("/modern/vouchers/")
    assert r.status_code == 302, f"vouchers should redirect, got {r.status_code}"
    assert "/no-access/" in r.url, f"expected /no-access/ redirect, got {r.url}"

    # A8. HR → denied
    r = client.get("/modern/employees/")
    assert r.status_code == 302, f"employees should redirect, got {r.status_code}"
    assert "/no-access/" in r.url, f"expected /no-access/ redirect, got {r.url}"


# ---------------------------------------------------------------------------
# Flow B — HR Officer (sg_nhansu)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_flow_b_hr_officer_employees_and_payroll(dogfood_data):
    """HR officer can access employees, payroll, reports
    but is denied sales invoices and purchasing."""
    client = Client()
    _login_and_set_company(client, "sg_nhansu", "DF-SG")

    # B2. Employees list → 200
    r = client.get("/modern/employees/")
    assert r.status_code == 200, f"employees returned {r.status_code}"

    # B3. Payroll → 200
    r = client.get("/modern/payroll/run/")
    assert r.status_code == 200, f"payroll returned {r.status_code}"

    # B4. Reports → 200
    r = client.get("/modern/reports/trial-balance/")
    assert r.status_code == 200, f"reports returned {r.status_code}"

    # B5. Sales invoices → denied
    r = client.get("/modern/sales-invoices/")
    assert r.status_code == 302, f"sales should redirect, got {r.status_code}"
    assert "/no-access/" in r.url

    # B6. Purchasing → denied
    r = client.get("/modern/purchase-invoices/")
    assert r.status_code == 302, f"purchasing should redirect, got {r.status_code}"
    assert "/no-access/" in r.url


# ---------------------------------------------------------------------------
# Flow C — Admin (sg_admin) cross-module
# ---------------------------------------------------------------------------

# Representative URLs spanning every major module.
ADMIN_MODULE_URLS = [
    ("/modern/vouchers/", "ledger"),
    ("/modern/sales-invoices/", "sales"),
    ("/modern/purchase-invoices/", "purchasing"),
    ("/modern/employees/", "hr"),
    ("/modern/payroll/run/", "payroll"),
    ("/modern/reports/trial-balance/", "reporting"),
    ("/modern/contracts/", "contracts"),
    ("/modern/einvoices/", "einvoice"),
    ("/modern/crm/leads/", "crm"),
    ("/modern/projects/", "projects"),
    ("/modern/customers/", "master_data"),
    ("/modern/vendors/", "purchasing"),
    ("/modern/products/", "master_data"),
    ("/modern/labor-contracts/", "hr"),
    ("/modern/assets/", "assets"),
    ("/modern/inventory/dashboard/", "inventory"),
]


@pytest.mark.django_db
def test_flow_c_admin_all_modules_200(dogfood_data):
    """Admin (sg_admin) should get 200 for every module in DF-SG."""
    client = Client()
    _login_and_set_company(client, "sg_admin", "DF-SG")

    for url, module in ADMIN_MODULE_URLS:
        r = client.get(url)
        assert r.status_code == 200, f"admin access to {url} ({module}) returned {r.status_code}"


@pytest.mark.django_db
def test_flow_c_admin_dashboard_tt133_mode(dogfood_data):
    """DF-SG dashboard should NOT be in TT58/DNSN mode."""
    client = Client()
    _login_and_set_company(client, "sg_admin", "DF-SG")

    r = client.get("/modern/")
    assert r.status_code == 200
    ctx = r.context
    assert ctx is not None, "dashboard response has no context"
    assert ctx.get("is_dnsn") is False, "DF-SG (tt133) should not be DNSN"


@pytest.mark.django_db
def test_flow_c_admin_switch_to_tt58_company(dogfood_data):
    """If sg_admin has a role at DF-HN (TT58), switching should show DNSN mode.

    The seed only creates sg_admin at DF-SG. We add a UserCompanyRole for
    DF-HN so the switch is permitted, then verify the dashboard context
    switches to TT58/DNSN mode.
    """
    from apps.identity.models import Role

    user = User.objects.get(username="sg_admin")
    hn = Company.objects.get(code="DF-HN")

    # Add admin role at DF-HN so the switch is allowed
    hn_admin_role, _ = Role.objects.get_or_create(
        company=hn,
        code="admin",
        defaults={"name": "Quản trị viên"},
    )
    hn_admin_role.permissions.set(
        Permission.objects.filter(code__in=[f"{m}.access" for m in ALL_MODULES])
    )
    UserCompanyRole.objects.update_or_create(
        user=user,
        company=hn,
        defaults={"role": hn_admin_role, "is_default": False},
    )
    cache.clear()

    client = Client()
    client.force_login(user)

    # Simulate the company switch POST
    r = client.post("/switch-company/", data={"company_id": hn.id})
    assert r.status_code == 302, f"switch-company returned {r.status_code}"
    assert client.session.get("current_company_id") == hn.id

    # Dashboard should now be in TT58/DNSN mode
    r = client.get("/modern/")
    assert r.status_code == 200
    ctx = r.context
    assert ctx is not None
    assert ctx.get("is_dnsn") is True, "DF-HN (tt58) dashboard should be in DNSN mode"
