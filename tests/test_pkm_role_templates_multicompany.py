"""Tests for multi-company role template seeding (VAL-EXPORT-002).

Covers:

  * ``seed_pkm_templates`` now seeds role templates for ALL companies
    (not just the first), closing the multi-company gap.
  * Each company receives its own per-company set of role templates.
  * Idempotency per (company, role_context, title) — re-running the
    command does not duplicate templates within a company.
  * The summary output reflects multi-company counts.

Fulfils:
  - **VAL-EXPORT-002**: Given 3 companies exist, when seed_pkm_templates
    runs, then each company has role template notes.
"""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.management.commands._role_template_content import (
    ROLE_TEMPLATES,
    TEMPLATE_TITLE_PREFIX,
)
from apps.pkm.models import KnowledgeNote

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="mcs_admin", password="Test1234!", email="mcs@t.co"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_command(*args: str) -> str:
    """Run seed_pkm_templates and return stdout output."""
    out = io.StringIO()
    call_command("seed_pkm_templates", *args, stdout=out, stderr=out)
    return out.getvalue()


def _templates_for_company(company: Company) -> list[KnowledgeNote]:
    return list(
        KnowledgeNote.objects.filter(
            company=company, title__startswith=TEMPLATE_TITLE_PREFIX
        ).order_by("title")
    )


# ===========================================================================
# VAL-EXPORT-002: Role templates seeded for multiple companies
# ===========================================================================


@pytest.mark.django_db
def test_seed_creates_templates_for_all_companies(superuser):
    """VAL-EXPORT-002: each of 3 companies receives the full template set."""
    companies = [Company.objects.create(code=f"MC_{i}", name=f"Multi Co {i}") for i in range(3)]
    assert Company.objects.count() == 3

    _run_command()

    for company in companies:
        templates = _templates_for_company(company)
        assert len(templates) == len(ROLE_TEMPLATES), (
            f"Company {company.code} has {len(templates)} templates, expected {len(ROLE_TEMPLATES)}"
        )
        # Each role is represented.
        seeded_roles = {t.role_context for t in templates}
        assert seeded_roles == {"accountant", "sales", "hr_officer", "viewer"}
        # All pinned.
        for tpl in templates:
            assert tpl.is_pinned is True


@pytest.mark.django_db
def test_seed_per_company_templates_are_distinct_rows(superuser):
    """Each company's templates are distinct database rows (not shared)."""
    co_a = Company.objects.create(code="MC_A", name="Co A")
    co_b = Company.objects.create(code="MC_B", name="Co B")

    _run_command()

    a_ids = {t.id for t in _templates_for_company(co_a)}
    b_ids = {t.id for t in _templates_for_company(co_b)}
    assert a_ids and b_ids
    assert a_ids.isdisjoint(b_ids), "Template rows should not be shared across companies"


@pytest.mark.django_db
def test_seed_idempotent_per_company(superuser):
    """Re-running does not duplicate templates within any company."""
    companies = [Company.objects.create(code=f"MC_ID_{i}", name=f"Co {i}") for i in range(3)]

    _run_command()
    counts_after_first = {c.code: len(_templates_for_company(c)) for c in companies}

    output = _run_command()
    counts_after_second = {c.code: len(_templates_for_company(c)) for c in companies}

    assert counts_after_first == counts_after_second
    for c in companies:
        assert counts_after_first[c.code] == len(ROLE_TEMPLATES)
    # Output should report 0 newly-created across the second run.
    assert "0 new" in output


@pytest.mark.django_db
def test_seed_summary_message_mentions_all_companies(superuser):
    """The summary message reflects multi-company counts."""
    for i in range(3):
        Company.objects.create(code=f"MC_MSG_{i}", name=f"Co {i}")

    output = _run_command()

    # Per-template count is consistent.
    assert f"Seeded {len(ROLE_TEMPLATES)} role template(s) per company" in output
    # The summary mentions the number of companies.
    assert "3 company" in output
    # And each company is listed in the per-company report.
    for i in range(3):
        assert f"MC_MSG_{i}" in output


@pytest.mark.django_db
def test_seed_creates_new_templates_for_new_companies_on_rerun(superuser):
    """Re-running after adding a new company seeds templates for it too."""
    co_a = Company.objects.create(code="MC_RR_A", name="Co A")
    _run_command()
    assert len(_templates_for_company(co_a)) == len(ROLE_TEMPLATES)

    # Add a second company and re-run.
    co_b = Company.objects.create(code="MC_RR_B", name="Co B")
    output = _run_command()

    # Co B now has its own template set.
    assert len(_templates_for_company(co_b)) == len(ROLE_TEMPLATES)
    # Co A still has exactly one set (no duplication).
    assert len(_templates_for_company(co_a)) == len(ROLE_TEMPLATES)
    # The output reflects that 7 new templates were created for the new company.
    assert f"{len(ROLE_TEMPLATES)} new" in output


@pytest.mark.django_db
def test_seed_each_company_has_all_role_codes(superuser):
    """Each company has templates for all four role codes."""
    companies = [Company.objects.create(code=f"MC_RC_{i}", name=f"Co {i}") for i in range(2)]
    _run_command()

    for company in companies:
        templates = _templates_for_company(company)
        by_role: dict[str, int] = {}
        for tpl in templates:
            by_role[tpl.role_context] = by_role.get(tpl.role_context, 0) + 1
        assert by_role == {"accountant": 2, "sales": 2, "hr_officer": 2, "viewer": 1}


@pytest.mark.django_db
def test_seed_single_company_still_works(superuser):
    """When only one company exists, the command behaves as before."""
    company = Company.objects.create(code="MC_SINGLE", name="Single Co")
    _run_command()

    templates = _templates_for_company(company)
    assert len(templates) == len(ROLE_TEMPLATES)
