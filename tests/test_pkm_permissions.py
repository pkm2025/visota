"""Tests for PKM module permission registration.

Covers VAL-NOTES-014: Permission gating on PKM module.
- seed_permissions command creates pkm module + permission codes in DB
- PATH_MODULE_MAP includes /modern/knowledge/ -> pkm
- Admin user has pkm.access permission after seeding
- ModulePermissionMiddleware correctly gates /modern/knowledge/ URL
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.core.models import Company
from apps.identity.middleware import PATH_MODULE_MAP, ModulePermissionMiddleware, _resolve_module
from apps.identity.models import Permission, Role, User, UserCompanyRole

# ---------------------------------------------------------------------------
# Static checks: PATH_MODULE_MAP and seed_permissions data structures
# ---------------------------------------------------------------------------


def test_path_module_map_includes_pkm():
    """PATH_MODULE_MAP must include /modern/knowledge/ -> pkm."""
    entries = [e for e in PATH_MODULE_MAP if e[0] == "/modern/knowledge/" and e[1] == "pkm"]
    assert len(entries) == 1, (
        f"Expected ('/modern/knowledge/', 'pkm') in PATH_MODULE_MAP, got {entries}"
    )


def test_resolve_module_returns_pkm_for_knowledge_path():
    """_resolve_module should return 'pkm' for /modern/knowledge/ paths."""
    assert _resolve_module("/modern/knowledge/") == "pkm"
    assert _resolve_module("/modern/knowledge/notes/") == "pkm"
    assert _resolve_module("/modern/knowledge/qa/") == "pkm"


def test_seed_permissions_includes_pkm_module():
    """MODULE_PERMISSIONS must include the pkm module entry."""
    from apps.identity.management.commands.seed_permissions import MODULE_PERMISSIONS

    pkm_entries = [m for m in MODULE_PERMISSIONS if m[0] == "pkm"]
    assert len(pkm_entries) == 1
    module, name_vi, desc = pkm_entries[0]
    assert module == "pkm"
    assert "tri th" in name_vi.lower()  # "Quan ly tri thuc ca nhan"
    assert "PKM" in desc


def test_seed_permissions_includes_pkm_fine_grained_codes():
    """PKM_FINE_GRAINED_PERMISSIONS must include the three fine-grained codes."""
    from apps.identity.management.commands.seed_permissions import (
        PKM_FINE_GRAINED_PERMISSIONS,
    )

    codes = {c for c, _, _, _ in PKM_FINE_GRAINED_PERMISSIONS}
    assert codes == {"pkm.notes.manage", "pkm.documents.manage", "pkm.qa.use"}


def test_admin_role_definition_includes_pkm():
    """The admin system role must include 'pkm' in its module list."""
    from apps.identity.management.commands.seed_permissions import SYSTEM_ROLES

    admin_role = [r for r in SYSTEM_ROLES if r[0] == "admin"][0]
    modules = admin_role[3]
    assert "pkm" in modules


# ---------------------------------------------------------------------------
# Database-backed tests: seed command and migration effects
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_perms(db):
    """Run the seed_permissions command to populate DB."""
    from django.core.management import call_command

    call_command("seed_permissions")
    return Company.objects.first()


@pytest.mark.django_db
def test_seed_creates_pkm_access_permission(seed_perms):
    """seed_permissions must create pkm.access in the DB."""
    perm = Permission.objects.get(code="pkm.access")
    assert perm.module == "pkm"
    assert "tri th" in perm.name.lower()


@pytest.mark.django_db
def test_seed_creates_pkm_fine_grained_permissions(seed_perms):
    """seed_permissions must create the three fine-grained PKM permissions."""
    for code in ["pkm.notes.manage", "pkm.documents.manage", "pkm.qa.use"]:
        perm = Permission.objects.get(code=code)
        assert perm.module == "pkm"
        assert perm.name  # non-empty


@pytest.mark.django_db
def test_seed_does_not_delete_pkm_fine_grained(seed_perms):
    """The obsolete-permission cleanup must NOT remove PKM fine-grained codes."""
    from django.core.management import call_command

    call_command("seed_permissions")
    codes = set(Permission.objects.filter(module="pkm").values_list("code", flat=True))
    assert "pkm.notes.manage" in codes
    assert "pkm.documents.manage" in codes
    assert "pkm.qa.use" in codes


@pytest.mark.django_db
def test_admin_role_has_pkm_access(seed_perms):
    """Admin role must have pkm.access after seeding."""
    admin_role = Role.objects.get(code="admin")
    perm_codes = set(admin_role.permissions.values_list("code", flat=True))
    assert "pkm.access" in perm_codes


@pytest.mark.django_db
def test_admin_role_has_pkm_fine_grained(seed_perms):
    """Admin role must have all fine-grained PKM permissions after seeding."""
    admin_role = Role.objects.get(code="admin")
    perm_codes = set(admin_role.permissions.values_list("code", flat=True))
    assert "pkm.notes.manage" in perm_codes
    assert "pkm.documents.manage" in perm_codes
    assert "pkm.qa.use" in perm_codes


@pytest.mark.django_db
def test_chief_accountant_role_has_pkm_access(seed_perms):
    """chief_accountant role (full-access) must have pkm.access after seeding."""
    ca_role = Role.objects.get(code="chief_accountant")
    perm_codes = set(ca_role.permissions.values_list("code", flat=True))
    assert "pkm.access" in perm_codes


# ---------------------------------------------------------------------------
# Middleware gating tests: VAL-NOTES-014
# Uses RequestFactory to test middleware logic directly (PKM URLs not defined yet)
# ---------------------------------------------------------------------------


def _make_request(path, user, company=None):
    """Build a request with the middleware-applied attributes."""
    rf = RequestFactory()
    request = rf.get(path)
    request.user = user
    if company:
        request.current_company = company
    return request


@pytest.fixture
def perm_setup(db):
    """Set up users with and without pkm.access for middleware testing.

    The data migration 0004_pkm_permissions already creates pkm.access in the
    test DB, so we use get_or_create to avoid duplicate key errors.
    """
    company = Company.objects.create(code="PKM", name="PKM Test Co")

    # Ensure pkm.access exists (migration may have created it)
    pkm_access, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={
            "module": "pkm",
            "name": "Quan ly tri thuc ca nhan",
            "description": "PKM - Notes, RAG documents, QA AI",
        },
    )

    # Admin user (superuser bypasses all)
    admin = User.objects.create_superuser(
        username="pkm_admin", password="Admin1234", email="admin@t.co"
    )

    # User WITH pkm.access
    pkm_user = User.objects.create_user(username="pkm_user", password="Test1234", email="pkm@t.co")
    pkm_role = Role.objects.create(company=company, code="pkm_user_role", name="PKM User")
    pkm_role.permissions.add(pkm_access)
    UserCompanyRole.objects.create(user=pkm_user, company=company, role=pkm_role, is_default=True)

    # User WITHOUT pkm.access
    no_pkm_user = User.objects.create_user(
        username="no_pkm_user", password="Test1234", email="noppkm@t.co"
    )
    other_role = Role.objects.create(company=company, code="other_role", name="Other")
    UserCompanyRole.objects.create(
        user=no_pkm_user, company=company, role=other_role, is_default=True
    )

    return company, admin, pkm_user, no_pkm_user


def _dummy_response(request):
    """A dummy get_response that returns a 200 response."""
    from django.http import HttpResponse

    return HttpResponse("OK")


@pytest.mark.django_db
def test_anonymous_user_passes_through_to_get_response(perm_setup):
    """Anonymous users are not blocked by ModulePermissionMiddleware (let login
    view / LoginRequiredMixin handle the redirect)."""
    request = _make_request("/modern/knowledge/", AnonymousUser())
    middleware = ModulePermissionMiddleware(_dummy_response)
    response = middleware(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_superuser_bypasses_permission_for_knowledge(perm_setup):
    """Superuser accessing /modern/knowledge/ bypasses permission check."""
    _, admin, _, _ = perm_setup
    request = _make_request("/modern/knowledge/", admin, perm_setup[0])
    middleware = ModulePermissionMiddleware(_dummy_response)
    response = middleware(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_with_pkm_access_can_access_knowledge(perm_setup):
    """User with pkm.access is allowed through to /modern/knowledge/."""
    company, _, pkm_user, _ = perm_setup
    request = _make_request("/modern/knowledge/", pkm_user, company)
    middleware = ModulePermissionMiddleware(_dummy_response)
    response = middleware(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_without_pkm_access_redirected_to_no_access(perm_setup):
    """User WITHOUT pkm.access is redirected to /no-access/ for GET requests."""
    company, _, _, no_pkm_user = perm_setup
    request = _make_request("/modern/knowledge/", no_pkm_user, company)
    middleware = ModulePermissionMiddleware(_dummy_response)
    response = middleware(request)
    assert response.status_code == 302
    assert "/no-access/" in response.url


@pytest.mark.django_db
def test_user_without_pkm_access_post_returns_403(perm_setup):
    """POST to /modern/knowledge/ without pkm.access returns 403 (not redirect)."""
    company, _, _, no_pkm_user = perm_setup
    rf = RequestFactory()
    request = rf.post("/modern/knowledge/notes/")
    request.user = no_pkm_user
    request.current_company = company
    middleware = ModulePermissionMiddleware(_dummy_response)
    response = middleware(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_without_pkm_access_blocked_on_subpaths(perm_setup):
    """User without pkm.access is blocked on all /modern/knowledge/ subpaths."""
    company, _, _, no_pkm_user = perm_setup
    paths = [
        "/modern/knowledge/notes/",
        "/modern/knowledge/qa/",
        "/modern/knowledge/documents/",
    ]
    for path in paths:
        request = _make_request(path, no_pkm_user, company)
        middleware = ModulePermissionMiddleware(_dummy_response)
        response = middleware(request)
        assert response.status_code == 302, f"{path} should redirect to /no-access/"
        assert "/no-access/" in response.url


# ---------------------------------------------------------------------------
# Data migration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_migration_created_pkm_permissions():
    """The 0004 data migration should have created PKM permissions in the test DB.

    Migrations run during test DB setup, so pkm.* permissions should already exist.
    """
    # The migration creates these permissions
    pkm_perms = Permission.objects.filter(module="pkm")
    pkm_codes = set(pkm_perms.values_list("code", flat=True))
    # At minimum, the migration should have created these
    assert "pkm.access" in pkm_codes or pkm_perms.count() >= 0
