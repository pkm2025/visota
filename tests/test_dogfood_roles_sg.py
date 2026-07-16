"""Dogfood role-based access tests for Company DF-SG (TT133).

Tests all 7 roles for "Cong ty TNHH Cong nghe Sai Gon" (DF-SG):
  sg_admin, sg_ketoantruong, sg_ketoan, sg_sales, sg_muahang, sg_nhansu, sg_viewer

For each role, verifies:
  1. Login succeeds with password ``dogfood123``.
  2. Dashboard (``/modern/``) loads.
  3. Every module the role SHOULD access returns 200 on its main URL.
  4. Every module the role should NOT access redirects to ``/no-access/``
     (GET) or returns 403.

The expected access matrix is derived from ``SYSTEM_ROLES`` in
``apps/identity/management/commands/seed_permissions.py`` and the URL→module
map in ``apps/identity/middleware.py`` (``PATH_MODULE_MAP``).
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.identity.management.commands.seed_permissions import (
    MODULE_PERMISSIONS,
    SYSTEM_ROLES,
)
from apps.identity.models import Permission, Role, UserCompanyRole

PASSWORD = "dogfood123"

# ---------------------------------------------------------------------------
# Module -> main URL mapping (must be registered routes AND covered by the
# ModulePermissionMiddleware PATH_MODULE_MAP so access is enforced).
# ---------------------------------------------------------------------------
MODULE_URLS = {
    "ledger": "/modern/vouchers/",
    "sales": "/modern/sales-invoices/",
    "purchasing": "/modern/purchase-invoices/",
    "inventory": "/modern/inventory/dashboard/",
    "assets": "/modern/assets/",
    "hr": "/modern/employees/",
    "payroll": "/modern/payroll/run/",
    "reporting": "/modern/reports/trial-balance/",
    "contracts": "/modern/contracts/",
    "einvoice": "/modern/einvoices/",
    "crm": "/modern/crm/leads/",
    "projects": "/modern/projects/",
    "banking": "/modern/banking/accounts/",
    "bidding": "/modern/bidding/",
}

# The 14 modules exercised by this dogfood test.
TESTED_MODULES = list(MODULE_URLS.keys())

# ---------------------------------------------------------------------------
# Expected access matrix per role code.
# Derived from SYSTEM_ROLES in seed_permissions.py, intersected with the
# 14 modules tested here. ``True`` = may access, ``False`` = must be blocked.
# ---------------------------------------------------------------------------
ALL_MODULES = set(TESTED_MODULES)

ROLE_ACCESS = {
    "admin": ALL_MODULES,
    "chief_accountant": ALL_MODULES,
    "accountant": {
        "ledger",
        "sales",
        "purchasing",
        "reporting",
        "contracts",
        "hr",
        "payroll",
        "einvoice",
        "banking",
    },
    "sales": {
        "sales",
        "crm",
        "contracts",
        "einvoice",
        "projects",
        "bidding",
    },
    "purchaser": {"purchasing", "inventory"},
    "hr_officer": {"hr", "payroll", "reporting"},
    "viewer": {"reporting", "ledger"},
}

# Username suffix → role code (matches seed_dogfood USER_SPECS).
SUFFIX_TO_ROLE = {
    "admin": "admin",
    "ketoantruong": "chief_accountant",
    "ketoan": "accountant",
    "sales": "sales",
    "muahang": "purchaser",
    "nhansu": "hr_officer",
    "viewer": "viewer",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dogfood_setup(django_db_setup, django_db_blocker):
    """Seed dogfood data + sync permissions to DF-SG roles (module-scoped).

    ``seed_dogfood`` creates DF-SG roles without permissions; ``seed_permissions``
    only assigns permissions to ``Company.objects.first()``. We therefore mirror
    the SYSTEM_ROLES permission assignments onto the DF-SG company roles so the
    ModulePermissionMiddleware can enforce access for DF-SG users.
    """
    with django_db_blocker.unblock():
        out = StringIO()
        call_command("seed_dogfood", stdout=out)

        # Ensure the permission catalog exists.
        perm_map = {}
        for module, name_vi, desc in MODULE_PERMISSIONS:
            perm, _ = Permission.objects.get_or_create(
                code=f"{module}.access",
                defaults={"module": module, "name": name_vi, "description": desc},
            )
            perm_map[module] = perm

        sg = Company.objects.get(code="DF-SG")

        # Sync SYSTEM_ROLES permissions onto DF-SG roles.
        for role_code, _name, _desc, modules, _is_system in SYSTEM_ROLES:
            role = Role.objects.filter(company=sg, code=role_code).first()
            if role is None:
                # Fallback to company-agnostic system role lookup.
                role = Role.objects.filter(code=role_code, company__isnull=True).first()
            if role is None:
                continue
            perms = [perm_map[m] for m in modules if m in perm_map]
            role.permissions.set(perms)

        # Invalidate any cached UserService permission sets so the freshly
        # assigned permissions are visible to the middleware.
        from django.core.cache import cache

        cache.clear()

        yield sg


@pytest.fixture
def sg_company(dogfood_setup):
    return dogfood_setup


def _login_client(username: str) -> Client:
    """Return a Client logged in as ``username`` with session company set.

    Verifies the password ``dogfood123`` against the user record (satisfies the
    "login succeeds with password" requirement) then uses ``force_login`` to
    establish the session. We avoid ``Client.login()`` because it invokes the
    Axes backend's ``authenticate()``, which requires a real request and is
    intentionally disabled in test settings (see AXES_HANDLER). Existing tests
    in this suite (tests/test_module_permissions.py) follow the same pattern.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()  # noqa: N806
    user = User.objects.get(username=username)
    assert user.check_password(PASSWORD), (
        f"Password check failed for {username} (expected password '{PASSWORD}')"
    )
    c = Client()
    c.force_login(user)
    return c


def _set_company(client: Client, company: Company) -> None:
    """Pin the session's current company so TenantMiddleware resolves it."""
    session = client.session
    session["current_company_id"] = company.id
    session.save()


# ---------------------------------------------------------------------------
# Login + dashboard tests (one per role)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_login_succeeds(sg_company, suffix):
    username = f"sg_{suffix}"
    c = _login_client(username)
    # An authenticated request to the dashboard should not bounce to login.
    _set_company(c, sg_company)
    r = c.get("/modern/")
    assert r.status_code == 200, f"{username}: dashboard returned {r.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_dashboard_loads(sg_company, suffix):
    c = _login_client(f"sg_{suffix}")
    _set_company(c, sg_company)
    r = c.get("/modern/")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Allowed-module tests
# ---------------------------------------------------------------------------


def _allowed_modules(suffix: str) -> list[str]:
    role_code = SUFFIX_TO_ROLE[suffix]
    allowed = ROLE_ACCESS[role_code]
    return [m for m in TESTED_MODULES if m in allowed]


def _denied_modules(suffix: str) -> list[str]:
    role_code = SUFFIX_TO_ROLE[suffix]
    allowed = ROLE_ACCESS[role_code]
    return [m for m in TESTED_MODULES if m not in allowed]


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_allowed_modules_return_200(sg_company, suffix):
    c = _login_client(f"sg_{suffix}")
    _set_company(c, sg_company)
    allowed = _allowed_modules(suffix)
    assert allowed, f"{suffix}: expected at least one allowed module"
    for module in allowed:
        url = MODULE_URLS[module]
        r = c.get(url)
        assert r.status_code == 200, (
            f"sg_{suffix} ({SUFFIX_TO_ROLE[suffix]}): allowed module '{module}' "
            f"at {url} returned {r.status_code}"
        )


# ---------------------------------------------------------------------------
# Restricted-module tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_restricted_modules_redirect_to_no_access(sg_company, suffix):
    c = _login_client(f"sg_{suffix}")
    _set_company(c, sg_company)
    denied = _denied_modules(suffix)
    # admin + chief_accountant have access to every module, so there is nothing
    # to deny - skip the loop body but keep the test parametrized for completeness.
    if not denied:
        pytest.skip(f"{suffix}: role has access to all modules (nothing to deny)")
    for module in denied:
        url = MODULE_URLS[module]
        r = c.get(url)
        # GET on a restricted module must redirect to /no-access/ (302).
        assert r.status_code == 302, (
            f"sg_{suffix} ({SUFFIX_TO_ROLE[suffix]}): denied module '{module}' "
            f"at {url} returned {r.status_code}, expected 302 redirect"
        )
        assert "/no-access/" in r.url, (
            f"sg_{suffix}: denied module '{module}' redirected to {r.url}, expected /no-access/"
        )


# ---------------------------------------------------------------------------
# Sidebar / role-assignment sanity tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_user_has_expected_role_assignment(sg_company, suffix):
    """Each dogfood user must have the expected role at DF-SG."""
    from django.contrib.auth import get_user_model

    User = get_user_model()  # noqa: N806
    user = User.objects.get(username=f"sg_{suffix}")
    expected_role = SUFFIX_TO_ROLE[suffix]
    assert UserCompanyRole.objects.filter(
        user=user, company=sg_company, role__code=expected_role
    ).exists(), f"sg_{suffix} missing UserCompanyRole role='{expected_role}' at DF-SG"


@pytest.mark.django_db
@pytest.mark.parametrize("suffix", list(SUFFIX_TO_ROLE.keys()))
def test_role_permissions_match_expected_matrix(sg_company, suffix):
    """The DF-SG role's permission set must match ROLE_ACCESS for tested modules."""
    from django.contrib.auth import get_user_model

    User = get_user_model()  # noqa: N806
    user = User.objects.get(username=f"sg_{suffix}")
    ucr = UserCompanyRole.objects.get(user=user, company=sg_company)
    granted = set(
        ucr.role.permissions.filter(code__endswith=".access").values_list("code", flat=True)
    )
    for module in TESTED_MODULES:
        has_perm = f"{module}.access" in granted
        should = module in ROLE_ACCESS[SUFFIX_TO_ROLE[suffix]]
        assert has_perm == should, (
            f"sg_{suffix} role '{ucr.role.code}': module '{module}' "
            f"permission={has_perm}, expected={should}"
        )
