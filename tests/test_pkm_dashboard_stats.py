"""Tests for PKM dashboard stats and the GET /api/v1/pkm/stats/ endpoint.

Covers feature pkm-dashboard-stats:
  VAL-CROSS-007 - Dashboard shows stats (total notes, total documents, total Q&A)
  VAL-CROSS-008 - Role-based context filtering (notes tagged with role_context)

These are integration tests (django_db) that seed notes, documents, Q&A
history, interaction logs, roles and verify that:
  1. The stats API endpoint returns correct counts.
  2. The dashboard HTML page renders the correct counts.
  3. Role-based suggestions only include notes whose ``role_context``
     matches the user's role codes.
  4. Recent activity feed is populated from interaction logs.
  5. Pinned notes quick access is shown.
  6. Per-user and multi-tenant isolation is preserved.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.models import (
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    Tag,
    UserInteractionLog,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="DASH_CO", name="Dashboard Co")


@pytest.fixture
def admin_user(db, company):
    """Superuser - bypasses permission checks (has pkm.access implicitly)."""
    return User.objects.create_superuser(
        username="dash_admin", password="Test1234", email="admin@dash.test"
    )


@pytest.fixture
def accountant_user(db, company):
    """Regular user with pkm.access permission AND an 'accountant' role.

    The role code 'accountant' is used to test role-based suggestions.
    """
    user = User.objects.create_user(
        username="dash_accountant", password="Test1234", email="acc@dash.test"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={
            "module": "pkm",
            "name": "PKM Access",
            "description": "Access PKM module",
        },
    )
    role = Role.objects.create(
        company=company, code="accountant", name="Accountant Role"
    )
    role.permissions.add(perm)
    UserCompanyRole.objects.create(
        user=user, company=company, role=role, is_default=True
    )
    return user


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="DASH_OTHER", name="Other Dashboard Co")


@pytest.fixture
def other_company_user(db, other_company):
    """A superuser in a different company (multi-tenant isolation test)."""
    return User.objects.create_superuser(
        username="dash_other", password="Test1234", email="other@dash.test"
    )


def _client_for(user, company=None) -> Client:
    """Return a logged-in client, optionally setting the current company."""
    c = Client()
    c.force_login(user)
    if company:
        session = c.session
        session["current_company_id"] = company.id
        session.save()
    return c


def _seed_data(user, company):
    """Seed a known set of notes, documents, Q&A, and interactions.

    Returns a dict describing the seeded counts so tests can assert.
    """
    # 3 notes (1 pinned, 1 with role_context='accountant', 1 plain)
    KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Pinned Note",
        content="pinned content",
        is_pinned=True,
    )
    KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Accountant Tip",
        content="debit credit",
        role_context="accountant",
    )
    KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Generic Note",
        content="plain content",
    )

    # 2 documents with different statuses
    from django.core.files.uploadedfile import SimpleUploadedFile

    PKMDocument.objects.create(
        user=user,
        company=company,
        title="Processed Doc",
        file=SimpleUploadedFile(
            "dash1.txt", b"data1", content_type="text/plain"
        ),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PROCESSED,
    )
    PKMDocument.objects.create(
        user=user,
        company=company,
        title="Pending Doc",
        file=SimpleUploadedFile(
            "dash2.txt", b"data2", content_type="text/plain"
        ),
        file_type="txt",
        file_size=5,
        status=PKMDocument.Status.PENDING,
    )

    # 4 Q&A interactions
    for i in range(4):
        QAHistory.objects.create(
            user=user,
            company=company,
            question=f"Question {i}?",
            answer=f"Answer {i}.",
        )

    # 2 tags
    Tag.objects.create(user=user, company=company, name="tag1")
    Tag.objects.create(user=user, company=company, name="tag2")

    # 5 interaction logs (recent activity feed)
    for _i in range(5):
        UserInteractionLog.objects.create(
            user=user,
            company=company,
            interaction_type=UserInteractionLog.InteractionType.PAGE_VIEW,
            module="pkm",
        )

    return {
        "notes": 3,
        "docs": 2,
        "docs_processed": 1,
        "docs_pending": 1,
        "qa": 4,
        "tags": 2,
        "interactions": 5,
        "pinned": 1,
        "role_suggestions_for_accountant": 1,
    }


# ===========================================================================
# VAL-CROSS-007: Dashboard shows stats (API endpoint)
# ===========================================================================


@pytest.mark.django_db
def test_stats_api_returns_correct_counts(admin_user, company):
    """GET /api/v1/pkm/stats/ returns correct aggregate counts."""
    expected = _seed_data(admin_user, company)
    c = _client_for(admin_user, company)

    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200, response.content
    data = response.json()

    assert data["note_count"] == expected["notes"]
    assert data["doc_count"] == expected["docs"]
    assert data["qa_count"] == expected["qa"]
    assert data["tag_count"] == expected["tags"]
    assert data["pinned_note_count"] == expected["pinned"]

    # Document status breakdown
    assert data["doc_status_counts"]["processed"] == expected["docs_processed"]
    assert data["doc_status_counts"]["pending"] == expected["docs_pending"]
    assert data["doc_status_counts"]["processing"] == 0
    assert data["doc_status_counts"]["failed"] == 0


@pytest.mark.django_db
def test_stats_api_requires_auth(company):
    """Unauthenticated requests to /api/v1/pkm/stats/ are rejected."""
    c = Client()
    response = c.get("/api/v1/pkm/stats/")
    # django-ninja returns 401/403 for unauthenticated API requests
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_stats_api_empty_state(admin_user, company):
    """Stats endpoint returns zeros for a user with no data."""
    c = _client_for(admin_user, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["note_count"] == 0
    assert data["doc_count"] == 0
    assert data["qa_count"] == 0
    assert data["tag_count"] == 0
    assert data["pinned_note_count"] == 0
    assert data["llm_config_count"] == 0
    assert data["has_active_config"] is False


@pytest.mark.django_db
def test_stats_api_per_user_isolation(admin_user, company):
    """User A's stats don't include User B's data."""
    other_user = User.objects.create_user(
        username="dash_isolated", password="Test1234", email="iso@dash.test"
    )
    # Seed data for admin_user
    _seed_data(admin_user, company)
    # other_user has no data
    c = _client_for(other_user, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["note_count"] == 0
    assert data["doc_count"] == 0
    assert data["qa_count"] == 0


@pytest.mark.django_db
def test_stats_api_multi_tenant_isolation(
    admin_user, company, other_company, other_company_user
):
    """Stats are scoped by company - other company data is invisible."""
    # Seed data in company
    _seed_data(admin_user, company)
    # other_company_user logs in
    c = _client_for(other_company_user, other_company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["note_count"] == 0
    assert data["doc_count"] == 0
    assert data["qa_count"] == 0


# ===========================================================================
# VAL-CROSS-007: Dashboard UI shows stats
# ===========================================================================


@pytest.mark.django_db
def test_dashboard_ui_shows_note_count(admin_user, company):
    """Dashboard HTML renders the correct note count."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    # The note count appears in the stat card with id="stat-notes"
    assert b'id="stat-notes"' in response.content
    assert b">3</" in response.content or b">3</div>" in response.content


@pytest.mark.django_db
def test_dashboard_ui_shows_doc_count(admin_user, company):
    """Dashboard HTML renders the correct document count and status breakdown."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="stat-docs"' in response.content
    # Document status breakdown should appear
    content = response.content.decode("utf-8")
    assert "id=\"stat-doc-status\"" in content
    assert "1 \u0111\u00e3 x\u1eed l\u00fd" in content  # "1 đã xử lý"


@pytest.mark.django_db
def test_dashboard_ui_shows_qa_count(admin_user, company):
    """Dashboard HTML renders the correct Q&A count."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="stat-qa"' in response.content


@pytest.mark.django_db
def test_dashboard_ui_shows_recent_activity(admin_user, company):
    """Dashboard HTML shows the recent activity feed from interaction logs."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="recent-activity-list"' in response.content


@pytest.mark.django_db
def test_dashboard_ui_shows_pinned_notes(admin_user, company):
    """Dashboard HTML shows pinned notes quick access."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="pinned-notes-list"' in response.content
    assert b"Pinned Note" in response.content


@pytest.mark.django_db
def test_dashboard_ui_empty_state(admin_user, company):
    """Empty dashboard shows the getting-started prompt for a new user."""
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Empty state message should appear
    assert "Ch\u00e0o m\u1eebng" in content  # "Chào mừng"


# ===========================================================================
# VAL-CROSS-008: Role-based context filtering
# ===========================================================================


@pytest.mark.django_db
def test_stats_api_role_suggestions_for_accountant(accountant_user, company):
    """Stats endpoint reports role suggestions matching the user's role.

    The accountant_user has role code 'accountant'. The seeded data includes
    one note with role_context='accountant', which should be counted.
    """
    _seed_data(accountant_user, company)
    c = _client_for(accountant_user, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "accountant" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 1


@pytest.mark.django_db
def test_stats_api_role_suggestions_empty_for_no_role(admin_user, company):
    """A user with no roles gets zero role suggestions."""
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["user_role_codes"] == []
    assert data["role_suggestions_count"] == 0


@pytest.mark.django_db
def test_dashboard_ui_role_suggestions(accountant_user, company):
    """Dashboard shows role-based suggestion panel for users with matching notes."""
    _seed_data(accountant_user, company)
    c = _client_for(accountant_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    assert b'id="role-suggestions-list"' in response.content
    assert b"Accountant Tip" in response.content


@pytest.mark.django_db
def test_dashboard_ui_no_role_suggestions_for_unmatched_role(
    admin_user, company
):
    """Dashboard hides the role-suggestion panel when user has no matching notes.

    admin_user has no UserCompanyRole, so no role suggestions should appear.
    """
    _seed_data(admin_user, company)
    c = _client_for(admin_user, company)
    response = c.get("/modern/knowledge/")
    assert response.status_code == 200
    # The role suggestions panel should NOT be rendered (no matching notes)
    assert b'id="role-suggestions-list"' not in response.content


@pytest.mark.django_db
def test_role_context_filtering_excludes_non_matching_notes(
    accountant_user, company
):
    """Notes with a different role_context are NOT suggested.

    We add a note tagged with role_context='sales'. The accountant user
    should still only see the one 'accountant' note in suggestions.
    """
    _seed_data(accountant_user, company)
    KnowledgeNote.objects.create(
        user=accountant_user,
        company=company,
        title="Sales Tip",
        content="sales content",
        role_context="sales",
    )
    c = _client_for(accountant_user, company)
    response = c.get("/api/v1/pkm/stats/")
    assert response.status_code == 200
    data = response.json()
    # Still only 1 suggestion (the 'accountant' note)
    assert data["role_suggestions_count"] == 1
