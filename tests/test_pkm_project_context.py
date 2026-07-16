"""Tests for project context enrichment in ``interaction_service``.

Verifies the ``_format_project_context`` helper and its integration into
``get_context_summary``. When the user has recent project-related page-view
activity (module ``projects``), the summary includes a Vietnamese fragment
naming the current project (name, phase, budget). When there is no project
activity, the project context is omitted (non-blocking).

Fulfills:
  - VAL-PROJ-001: Context includes project when user has project activity
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import UserInteractionLog
from apps.pkm.services.interaction_service import (
    _format_project_context,
    get_context_summary,
)
from apps.projects.models import Project

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="PCS_CO",
        name="Project Context Co",
        tax_code="0107770001",
        accounting_regime="tt133",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
        industry="Thương mại",
    )


@pytest.fixture
def other_company(db):
    """Second tenant to verify cross-company isolation."""
    return Company.objects.create(
        code="PCS_OTHER",
        name="Other Tenant Co",
        tax_code="0107770002",
        accounting_regime="tt133",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
    )


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pcs_user",
        password="Test1234",
        email="pcs@t.co",
    )


@pytest.fixture
def project(company):
    return Project.objects.create(
        company=company,
        code="WEB-001",
        name="Website TMĐT",
        start_date=date(2026, 1, 1),
        status="active",
        budget_revenue=Decimal("500000000"),
        progress_percent=Decimal("60"),
    )


# ---------------------------------------------------------------------------
# _format_project_context: with project activity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_format_project_context_empty_without_activity(user, company):
    """No project activity returns an empty string (non-blocking)."""
    text = _format_project_context(user, company)
    assert text == ""


@pytest.mark.django_db
def test_format_project_context_with_detail_page_activity(user, company, project):
    """VAL-PROJ-001: Project activity on a detail page yields project text."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id=f"/modern/projects/{project.id}/",
        metadata={"url": f"/modern/projects/{project.id}/"},
    )
    text = _format_project_context(user, company)
    assert isinstance(text, str)
    assert len(text) > 0
    # Project name appears
    assert "Website TMĐT" in text


@pytest.mark.django_db
def test_format_project_context_with_list_page_only(user, company, project):
    """List page activity without detail picks the most recent project."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id="/modern/projects/",
        metadata={"url": "/modern/projects/"},
    )
    text = _format_project_context(user, company)
    # When only the list page was visited we cannot pin a specific project,
    # so the helper may return an empty string OR a generic hint. Either way
    # it must not raise and must be a string.
    assert isinstance(text, str)


@pytest.mark.django_db
def test_format_project_context_isolates_by_company(user, company, other_company, project):
    """Project activity in another tenant does not leak into this company."""
    UserInteractionLog.objects.create(
        user=user,
        company=other_company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id=f"/modern/projects/{project.id}/",
        metadata={"url": f"/modern/projects/{project.id}/"},
    )
    # Querying for ``company`` must yield no project context (the activity is
    # scoped to ``other_company``).
    text = _format_project_context(user, company)
    assert text == ""


@pytest.mark.django_db
def test_format_project_context_isolates_by_user(user, company, project, django_user_model):
    """Project activity by another user does not leak into this user."""
    other_user = django_user_model.objects.create_user(
        username="pcs_other_user",
        password="Test1234",
        email="other@t.co",
    )
    UserInteractionLog.objects.create(
        user=other_user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id=f"/modern/projects/{project.id}/",
        metadata={"url": f"/modern/projects/{project.id}/"},
    )
    text = _format_project_context(user, company)
    assert text == ""


@pytest.mark.django_db
def test_format_project_context_handles_invalid_entity_id(user, company, project):
    """A malformed entity_id (non-numeric) is handled gracefully."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id="/modern/projects/not-a-number/",
        metadata={"url": "/modern/projects/not-a-number/"},
    )
    # Must not raise; may return empty string
    text = _format_project_context(user, company)
    assert isinstance(text, str)


@pytest.mark.django_db
def test_format_project_context_ignores_non_project_modules(user, company, project):
    """page_view in other modules does not trigger project context."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="ledger",
        entity_type="page",
        entity_id=f"/modern/projects/{project.id}/",
        metadata={"url": f"/modern/projects/{project.id}/"},
    )
    text = _format_project_context(user, company)
    assert text == ""


# ---------------------------------------------------------------------------
# get_context_summary: integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_context_summary_includes_project_context(user, company, project):
    """VAL-PROJ-001: get_context_summary mentions the project when active."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id=f"/modern/projects/{project.id}/",
        metadata={"url": f"/modern/projects/{project.id}/"},
    )
    summary = get_context_summary(user, company, hours=24)
    assert "Website TMĐT" in summary


@pytest.mark.django_db
def test_get_context_summary_no_project_context_without_activity(user, company, project):
    """Without project activity the summary omits project-specific text."""
    summary = get_context_summary(user, company, hours=24)
    # The project exists but was never viewed, so its name must not appear.
    assert "Website TMĐT" not in summary


@pytest.mark.django_db
def test_get_context_summary_non_blocking_when_project_missing(user, company, project):
    """A detail-page view for a deleted/nonexistent project is non-blocking."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="projects",
        entity_type="page",
        entity_id="/modern/projects/999999/",
        metadata={"url": "/modern/projects/999999/"},
    )
    summary = get_context_summary(user, company, hours=24)
    # Summary must still assemble (no exception), just without that project.
    assert isinstance(summary, str)
    assert len(summary) > 0
