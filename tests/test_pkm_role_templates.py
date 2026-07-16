"""Tests for the ``seed_pkm_templates`` management command and the
role-based template visibility in the PKM dashboard.

Fulfills VAL-TPL-001: "Given seed runs, when accountant user views PKM
dashboard, then pinned notes with role_context='accountant' appear in
suggestions."

Coverage:
  Seed command (``seed_pkm_templates``):
    - Creates the expected shared, pinned KnowledgeNote templates for all
      four role codes (accountant, sales, hr_officer, viewer).
    - Each template has ``is_pinned=True`` and the matching ``role_context``.
    - Idempotent: re-running updates bodies instead of duplicating.
    - Falls back to the first user when no superuser exists.
    - Creates a sentinel SYSTEM company when no company exists.
    - Raises a helpful error when no user exists.

  Dashboard visibility:
    - VAL-TPL-001: an accountant user sees templates with
      ``role_context='accountant'`` in role suggestions (both API stats
      and the dashboard UI).
    - Templates appear regardless of owner (shared templates owned by a
      system/superuser are visible to any user with the matching role).
    - A user with a non-matching role (e.g. ``viewer``) does NOT see
      templates seeded for ``accountant``.
    - A user with no role gets zero role suggestions.
    - Multi-tenant isolation: templates seeded in company A are not visible
      to a user in company B.
"""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.management.commands._role_template_content import (
    ROLE_TEMPLATES,
    TEMPLATE_TITLE_PREFIX,
)
from apps.pkm.management.commands.seed_pkm_templates import (
    _extract_slug_from_title,
    _template_title,
)
from apps.pkm.models import KnowledgeNote

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="TPL_CO", name="Template Co")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="tpl_admin", password="Test1234!", email="tpl_admin@t.co"
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="tpl_user", password="Test1234!", email="tpl_user@t.co"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_command(*args: str) -> str:
    """Run seed_pkm_templates and return stdout output."""
    out = io.StringIO()
    call_command("seed_pkm_templates", *args, stdout=out, stderr=out)
    return out.getvalue()


def _make_role(company: Company, code: str) -> Role:
    """Create (or get) a role with the given code in ``company``."""
    role, _ = Role.objects.get_or_create(
        company=company,
        code=code,
        defaults={"name": code.replace("_", " ").title()},
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={
            "module": "pkm",
            "name": "PKM Access",
            "description": "Access PKM module",
        },
    )
    role.permissions.add(perm)
    return role


def _make_user_with_role(company: Company, username: str, role_code: str) -> User:
    """Create a regular user and assign the given role code in ``company``."""
    user = User.objects.create_user(
        username=username, password="Test1234!", email=f"{username}@t.co"
    )
    role = _make_role(company, role_code)
    UserCompanyRole.objects.create(user=user, company=company, role=role, is_default=True)
    return user


def _client_for(user: User, company: Company | None = None) -> Client:
    """Return a logged-in client, optionally setting the current company."""
    c = Client()
    c.force_login(user)
    if company:
        session = c.session
        session["current_company_id"] = company.id
        session.save()
    return c


# ===========================================================================
# Seed command: VAL-TPL-001 setup
# ===========================================================================


@pytest.mark.django_db
def test_seed_creates_templates_for_all_roles(company, superuser):
    """All role templates are seeded with is_pinned=True and role_context."""
    output = _run_command()
    assert "Seeded 7 role template(s)" in output

    templates = list(KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX))
    assert len(templates) == len(ROLE_TEMPLATES)

    # Each role code should be represented.
    seeded_roles = {t.role_context for t in templates}
    assert seeded_roles == {"accountant", "sales", "hr_officer", "viewer"}

    # All templates are pinned.
    for tpl in templates:
        assert tpl.is_pinned is True
        assert tpl.role_context in {"accountant", "sales", "hr_officer", "viewer"}
        assert tpl.content  # body populated
        assert tpl.title.startswith(TEMPLATE_TITLE_PREFIX)


@pytest.mark.django_db
def test_seed_creates_two_templates_per_main_role(company, superuser):
    """Accountant and sales each get 2 templates; hr_officer gets 2; viewer 1."""
    _run_command()
    by_role: dict[str, int] = {}
    for tpl in KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX):
        by_role[tpl.role_context] = by_role.get(tpl.role_context, 0) + 1
    assert by_role == {"accountant": 2, "sales": 2, "hr_officer": 2, "viewer": 1}


@pytest.mark.django_db
def test_seed_templates_attached_to_company_and_owner(company, superuser):
    """Templates are owned by the superuser and attached to the company."""
    _run_command()
    tpl = KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX).first()
    assert tpl is not None
    assert tpl.company_id == company.id
    assert tpl.user_id == superuser.id


@pytest.mark.django_db
def test_seed_falls_back_to_any_user_when_no_superuser(company, regular_user):
    """Without a superuser, the command uses the first available user."""
    assert not User.objects.filter(is_superuser=True).exists()
    _run_command()
    tpl = KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX).first()
    assert tpl is not None
    assert tpl.user_id == regular_user.id


@pytest.mark.django_db
def test_seed_creates_sentinel_company_when_none_exists(superuser):
    """When no company exists, a sentinel SYSTEM company is created."""
    assert Company.objects.count() == 0
    _run_command()
    tpl = KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX).first()
    assert tpl is not None
    assert tpl.company.code == "SYSTEM"


@pytest.mark.django_db
def test_seed_fails_when_no_user(company):
    """Command raises a helpful error when no user exists."""
    assert User.objects.count() == 0
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        _run_command()
    assert "user" in str(exc_info.value).lower() or "superuser" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_is_idempotent(company, superuser):
    """Re-running the command updates existing templates instead of duplicating."""
    _run_command()
    after_first = list(
        KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX).order_by("title")
    )
    assert len(after_first) == len(ROLE_TEMPLATES)

    output = _run_command()
    assert "0 new" in output

    after_second = list(
        KnowledgeNote.objects.filter(title__startswith=TEMPLATE_TITLE_PREFIX).order_by("title")
    )
    assert len(after_second) == len(ROLE_TEMPLATES)
    # Same PKs (not recreated).
    assert [n.id for n in after_first] == [n.id for n in after_second]


@pytest.mark.django_db
def test_seed_updates_body_in_place(company, superuser):
    """Re-running the command refreshes the body of an existing template."""
    _run_command()
    tpl = KnowledgeNote.objects.filter(
        title__startswith=TEMPLATE_TITLE_PREFIX, role_context="viewer"
    ).first()
    assert tpl is not None
    original_content = tpl.content

    # Tamper with the body to prove it gets refreshed.
    tpl.content = "TAMPERED"
    tpl.save(update_fields=["content"])

    _run_command()
    tpl.refresh_from_db()
    assert tpl.content == original_content
    assert tpl.content != "TAMPERED"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_template_title_round_trip():
    """Slug embedded in title is recoverable (used for idempotency lookups)."""
    slug = "accountant-ghi-so-cuoi-thang"
    title = "Quy trình ghi sổ kế toán cuối tháng"
    full = _template_title(slug, title)
    assert _extract_slug_from_title(full) == slug


def test_extract_slug_returns_none_for_non_template_title():
    """Non-template titles return None (no false positives)."""
    assert _extract_slug_from_title("My regular user note") is None


# ===========================================================================
# VAL-TPL-001: Role-based templates appear in dashboard for matching users
# ===========================================================================


@pytest.mark.django_db
def test_stats_api_role_suggestions_include_templates_for_accountant(company, superuser):
    """An accountant sees the seeded accountant templates in role suggestions.

    The accountant has no notes of their own; the templates are owned by the
    superuser. The shared-template logic must surface them anyway.
    """
    _run_command()
    accountant = _make_user_with_role(company, "tpl_acc", "accountant")
    c = _client_for(accountant, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200, response.content
    data = response.json()

    assert "accountant" in data["user_role_codes"]
    # 2 templates are seeded for 'accountant'.
    assert data["role_suggestions_count"] == 2


@pytest.mark.django_db
def test_stats_api_role_suggestions_include_templates_for_sales(company, superuser):
    """A sales user sees only the sales templates (not accountant's)."""
    _run_command()
    sales_user = _make_user_with_role(company, "tpl_sales", "sales")
    c = _client_for(sales_user, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "sales" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 2  # 2 sales templates


@pytest.mark.django_db
def test_stats_api_role_suggestions_include_templates_for_hr(company, superuser):
    """An hr_officer sees the hr_officer templates."""
    _run_command()
    hr_user = _make_user_with_role(company, "tpl_hr", "hr_officer")
    c = _client_for(hr_user, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "hr_officer" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 2  # 2 hr templates


@pytest.mark.django_db
def test_stats_api_role_suggestions_include_templates_for_viewer(company, superuser):
    """A viewer sees the viewer template."""
    _run_command()
    viewer = _make_user_with_role(company, "tpl_viewer", "viewer")
    c = _client_for(viewer, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "viewer" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 1  # 1 viewer template


@pytest.mark.django_db
def test_stats_api_role_suggestions_empty_for_no_role(company, superuser):
    """A user with no role gets zero role suggestions even after seeding."""
    _run_command()
    # A plain user with no role assignment.
    plain = User.objects.create_user(
        username="tpl_plain", password="Test1234!", email="tpl_plain@t.co"
    )
    c = _client_for(plain, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["user_role_codes"] == []
    assert data["role_suggestions_count"] == 0


@pytest.mark.django_db
def test_stats_api_role_suggestions_exclude_non_matching_role(company, superuser):
    """A viewer does NOT see accountant templates."""
    _run_command()
    viewer = _make_user_with_role(company, "tpl_v_only", "viewer")
    c = _client_for(viewer, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    # Only 1 viewer template; the 2 accountant templates are excluded.
    assert data["role_suggestions_count"] == 1


@pytest.mark.django_db
def test_dashboard_ui_shows_accountant_templates(company, superuser):
    """Dashboard HTML renders the role suggestions list with accountant templates."""
    _run_command()
    accountant = _make_user_with_role(company, "tpl_acc_ui", "accountant")
    c = _client_for(accountant, company)

    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="role-suggestions-list"' in response.content
    # The title of one of the accountant templates should appear.
    content = response.content.decode("utf-8")
    assert "Quy tr\u00ecnh ghi s\u1ed5 k\u1ebf to\u00e1n cu\u1ed1i th\u00e1ng" in content


@pytest.mark.django_db
def test_dashboard_ui_hides_role_suggestions_for_unmatched_role(company, superuser):
    """A user with a role that has no seeded templates sees no suggestion list."""
    _run_command()
    # Give the user a role code that has no templates at all.
    odd_user = _make_user_with_role(company, "tpl_odd", "inventory_clerk")
    c = _client_for(odd_user, company)

    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="role-suggestions-list"' not in response.content


@pytest.mark.django_db
def test_dashboard_ui_no_role_suggestions_for_user_without_role(company, superuser):
    """A user whose role has no matching templates does not see suggestions."""
    _run_command()
    # A plain user with pkm.access permission but NO role assignment.
    plain = User.objects.create_user(
        username="tpl_plain_ui", password="Test1234!", email="tpl_plain_ui@t.co"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={
            "module": "pkm",
            "name": "PKM Access",
            "description": "Access PKM module",
        },
    )
    # Grant pkm.access directly via a placeholder role so the middleware
    # allows access. The role has a code that does NOT match any template.
    access_role = Role.objects.create(company=company, code="pkm_only", name="PKM Only")
    access_role.permissions.add(perm)
    UserCompanyRole.objects.create(user=plain, company=company, role=access_role, is_default=True)
    c = _client_for(plain, company)

    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="role-suggestions-list"' not in response.content


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_templates_isolated_per_company(company, superuser):
    """Templates seeded in company A are invisible to a user in company B."""
    other_company = Company.objects.create(code="TPL_OTHER", name="Other Co")
    _run_command()  # seeds into `company` (the first company)

    # Accountant in the OTHER company should see zero suggestions because
    # the templates live in `company`.
    other_acc = _make_user_with_role(other_company, "tpl_other_acc", "accountant")
    c = _client_for(other_acc, other_company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "accountant" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 0


# ---------------------------------------------------------------------------
# Combined: own notes + shared templates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_role_suggestions_combine_own_notes_and_templates(company, superuser):
    """A user's own role-tagged notes AND shared templates are both counted."""
    _run_command()
    accountant = _make_user_with_role(company, "tpl_acc_combo", "accountant")

    # Add a personal accountant note (not a template — no prefix).
    KnowledgeNote.objects.create(
        user=accountant,
        company=company,
        title="My own accounting tip",
        content="personal",
        role_context="accountant",
    )

    c = _client_for(accountant, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    # 2 shared templates + 1 personal note = 3.
    assert data["role_suggestions_count"] == 3
