"""Tests for the PKM wiki lint service (Karpathy LLM Wiki pattern).

The **lint** operation is the health-check of the LLM wiki.  It scans the
tenant's wiki pages and detects:

  1.  **Orphan pages** — no inbound ``linked_pages`` (nothing references them).
  2.  **Potential contradictions** — the same concept appears in multiple
      pages (possible duplicate / conflicting definitions).
  3.  **Stale pages** — a page has not been updated after a newer source
      document was ingested (``last_ingest_at`` < source ``created_at``).
  4.  **Missing concept pages** — a concept is mentioned in wiki content via
      ``[[wikilinks]]`` but no page with that title exists.
  5.  **Health report** — the lint produces a ``WikiPage`` with
      ``page_type=overview`` summarising all findings.

All checks are scoped per (user, company) for multi-tenant isolation.  No
LLM calls are made — lint is a deterministic, local analysis.

Fulfills VAL-LINT-001: Lint detects orphan pages.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import PKMDocument, WikiPage
from apps.pkm.services.wiki_ingest_service import INDEX_PAGE_TITLE, LOG_PAGE_TITLE
from apps.pkm.services.wiki_lint_service import (
    HEALTH_REPORT_TITLE,
    find_contradictions,
    find_missing_concept_pages,
    find_orphan_pages,
    find_stale_pages,
    generate_health_report,
    lint_wiki,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="WIKI_LINT", name="Wiki Lint Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="wiki_lint_user", password="Test1234", email="wlint@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="wiki_lint_other", password="Test1234", email="wlo@t.co"
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="WIKI_LINT2", name="Wiki Lint Other Co")


# ---------------------------------------------------------------------------
# Helper to create wiki pages quickly
# ---------------------------------------------------------------------------


def _make_page(
    user,
    company,
    title,
    content="",
    page_type=WikiPage.PageType.CONCEPT,
    last_ingest_at=None,
    **kwargs,
):
    return WikiPage.objects.create(
        user=user,
        company=company,
        title=title,
        content=content,
        page_type=page_type,
        last_ingest_at=last_ingest_at,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# VAL-LINT-001: Orphan page detection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_find_orphan_pages_detects_unlinked_page(user, company):
    """A page with no inbound linked_pages is flagged as orphan."""
    linked_a = _make_page(user, company, "Linked A", content="linked")
    linked_b = _make_page(user, company, "Linked B", content="linked")
    _make_page(user, company, "Orphan Page", content="no links to me")

    # Create a link A -> B, so B has an inbound link; orphan has none
    linked_a.linked_pages.add(linked_b)

    orphans = find_orphan_pages(user, company)
    orphan_titles = {p.title for p in orphans}

    assert "Orphan Page" in orphan_titles
    assert "Linked B" not in orphan_titles  # B has inbound link from A


@pytest.mark.django_db
def test_find_orphan_pages_excludes_index_and_log(user, company):
    """The auto-maintained Index and Log pages are never treated as orphans."""
    _make_page(user, company, INDEX_PAGE_TITLE, page_type=WikiPage.PageType.OVERVIEW)
    _make_page(user, company, LOG_PAGE_TITLE, page_type=WikiPage.PageType.OVERVIEW)
    _make_page(user, company, "Orphan Concept", page_type=WikiPage.PageType.CONCEPT)

    orphans = find_orphan_pages(user, company)
    orphan_titles = {p.title for p in orphans}

    assert "Orphan Concept" in orphan_titles
    assert INDEX_PAGE_TITLE not in orphan_titles
    assert LOG_PAGE_TITLE not in orphan_titles


@pytest.mark.django_db
def test_find_orphan_pages_empty_wiki(user, company):
    """No wiki pages means no orphans."""
    orphans = find_orphan_pages(user, company)
    assert list(orphans) == []


@pytest.mark.django_db
def test_find_orphan_pages_isolated_by_user(user, company, other_user):
    """Orphan detection respects user scoping."""
    _make_page(user, company, "My Orphan")
    _make_page(other_user, company, "Other Orphan")

    my_orphans = find_orphan_pages(user, company)
    assert {p.title for p in my_orphans} == {"My Orphan"}


@pytest.mark.django_db
def test_find_orphan_pages_isolated_by_company(user, company, other_company):
    """Orphan detection respects company scoping."""
    _make_page(user, company, "Co A Orphan")
    _make_page(user, other_company, "Co B Orphan")

    my_orphans = find_orphan_pages(user, company)
    assert {p.title for p in my_orphans} == {"Co A Orphan"}


# ---------------------------------------------------------------------------
# Contradiction detection (same concept in multiple pages)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_find_contradictions_detects_duplicate_concept_titles(user, company):
    """Multiple concept pages with very similar titles are flagged."""
    _make_page(user, company, "VAT", content="VAT is 10%", page_type=WikiPage.PageType.CONCEPT)
    _make_page(
        user,
        company,
        "VAT (Value Added Tax)",
        content="VAT is 8%",
        page_type=WikiPage.PageType.CONCEPT,
    )

    contradictions = find_contradictions(user, company)
    # At least one contradiction pair should be detected
    assert len(contradictions) >= 1


@pytest.mark.django_db
def test_find_contradictions_detects_overlapping_source_refs(user, company):
    """Two pages sharing the same source_refs are flagged as potential duplicates."""
    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Shared Doc",
        file=SimpleUploadedFile("s.txt", b"x"),
        file_type="txt",
    )
    p1 = _make_page(user, company, "Concept One", content="c1")
    p2 = _make_page(user, company, "Concept Two", content="c2")
    p1.source_refs.add(doc)
    p2.source_refs.add(doc)

    contradictions = find_contradictions(user, company)
    assert len(contradictions) >= 1


@pytest.mark.django_db
def test_find_contradictions_none_for_distinct_concepts(user, company):
    """Unrelated concept pages produce no contradictions."""
    _make_page(user, company, "VAT", content="tax")
    _make_page(user, company, "PIT", content="income tax")
    _make_page(user, company, "Invoice", content="billing")

    contradictions = find_contradictions(user, company)
    assert contradictions == []


# ---------------------------------------------------------------------------
# Stale page detection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_find_stale_pages_detects_outdated_page(user, company):
    """A page with last_ingest_at before a newer source document is stale."""
    old_time = timezone.now() - timedelta(days=10)
    _make_page(
        user,
        company,
        "Old Concept",
        content="old info",
        last_ingest_at=old_time,
    )

    # A newer source document was ingested after the page was last updated
    PKMDocument.objects.create(
        user=user,
        company=company,
        title="New Source",
        file=SimpleUploadedFile("n.txt", b"x"),
        file_type="txt",
        status=PKMDocument.Status.PROCESSED,
    )

    stale = find_stale_pages(user, company)
    stale_titles = {p.title for p in stale}

    assert "Old Concept" in stale_titles


@pytest.mark.django_db
def test_find_stale_pages_excludes_fresh_pages(user, company):
    """A page updated after the newest source is NOT stale."""
    # Source document was created earlier
    old_doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Old Source",
        file=SimpleUploadedFile("o.txt", b"x"),
        file_type="txt",
        status=PKMDocument.Status.PROCESSED,
    )
    # Force created_at to the past (auto_now_add prevents setting on create)
    old_time = timezone.now() - timedelta(days=5)
    PKMDocument.objects.filter(pk=old_doc.pk).update(created_at=old_time)

    # Page was ingested after the source, so it's fresh
    _make_page(
        user,
        company,
        "Fresh Concept",
        content="up to date",
        last_ingest_at=timezone.now(),
    )

    stale = find_stale_pages(user, company)
    stale_titles = {p.title for p in stale}

    assert "Fresh Concept" not in stale_titles


@pytest.mark.django_db
def test_find_stale_pages_excludes_index_and_log(user, company):
    """System pages (Index, Log) are never flagged as stale."""
    old_time = timezone.now() - timedelta(days=30)
    _make_page(
        user,
        company,
        INDEX_PAGE_TITLE,
        page_type=WikiPage.PageType.OVERVIEW,
        last_ingest_at=old_time,
    )
    _make_page(
        user,
        company,
        LOG_PAGE_TITLE,
        page_type=WikiPage.PageType.OVERVIEW,
        last_ingest_at=old_time,
    )

    stale = find_stale_pages(user, company)
    stale_titles = {p.title for p in stale}
    assert INDEX_PAGE_TITLE not in stale_titles
    assert LOG_PAGE_TITLE not in stale_titles


# ---------------------------------------------------------------------------
# Missing concept page detection ([[wikilinks]] without a target page)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_find_missing_concept_pages(user, company):
    """A [[wikilink]] pointing to a non-existent page is flagged."""
    _make_page(
        user,
        company,
        "VAT",
        content="See [[PIT]] for personal income tax details.",
    )

    missing = find_missing_concept_pages(user, company)
    missing_set = set(missing)

    assert "PIT" in missing_set


@pytest.mark.django_db
def test_find_missing_concept_pages_excludes_existing(user, company):
    """A [[wikilink]] to a page that exists is NOT flagged."""
    _make_page(user, company, "VAT", content="See [[PIT]] for details.")
    _make_page(user, company, "PIT", content="income tax")

    missing = find_missing_concept_pages(user, company)
    assert "PIT" not in set(missing)


@pytest.mark.django_db
def test_find_missing_concept_pages_multiple(user, company):
    """Multiple missing [[wikilinks]] are all captured."""
    _make_page(
        user,
        company,
        "Overview",
        content="See [[A]] and [[B]] and [[C]].",
        page_type=WikiPage.PageType.OVERVIEW,
    )

    missing = set(find_missing_concept_pages(user, company))
    assert "A" in missing
    assert "B" in missing
    assert "C" in missing


# ---------------------------------------------------------------------------
# Health report generation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_generate_health_report_creates_overview_page(user, company):
    """The health report is saved as a WikiPage with page_type=overview."""
    _make_page(user, company, "Orphan", content="orphan page")

    report = generate_health_report(user, company)

    assert report.page_type == WikiPage.PageType.OVERVIEW
    assert report.title == HEALTH_REPORT_TITLE
    assert report.is_ai_generated is True
    assert report.pk is not None


@pytest.mark.django_db
def test_generate_health_report_contains_findings(user, company):
    """The report content includes orphan/stale/contradiction findings."""
    _make_page(user, company, "Orphan Concept", content="nobody links to me")

    report = generate_health_report(user, company)

    assert "Orphan Concept" in report.content
    assert "orphan" in report.content.lower() or "Orphan" in report.content


@pytest.mark.django_db
def test_generate_health_report_idempotent(user, company):
    """Generating the report twice updates the same page, not duplicates."""
    _make_page(user, company, "Some Page", content="x")

    report1 = generate_health_report(user, company)
    report2 = generate_health_report(user, company)

    assert report1.pk == report2.pk
    assert (
        WikiPage.objects.filter(user=user, company=company, title=HEALTH_REPORT_TITLE).count() == 1
    )


# ---------------------------------------------------------------------------
# Full lint_wiki orchestration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lint_wiki_returns_structured_result(user, company):
    """lint_wiki returns a dict with keys for each check category."""
    _make_page(user, company, "Orphan", content="orphan")

    result = lint_wiki(user, company)

    assert "orphans" in result
    assert "contradictions" in result
    assert "stale" in result
    assert "missing_concepts" in result
    assert "report_page_id" in result


@pytest.mark.django_db
def test_lint_wiki_creates_report_page(user, company):
    """lint_wiki generates and persists the health report."""
    _make_page(user, company, "Orphan", content="orphan")

    result = lint_wiki(user, company)

    report = WikiPage.objects.get(pk=result["report_page_id"])
    assert report.page_type == WikiPage.PageType.OVERVIEW
    assert report.title == HEALTH_REPORT_TITLE


@pytest.mark.django_db
def test_lint_wiki_detects_orphans_in_result(user, company):
    """lint_wiki result lists orphan pages (VAL-LINT-001)."""
    linked_a = _make_page(user, company, "Linked A")
    linked_b = _make_page(user, company, "Linked B")
    _make_page(user, company, "Orphan Result")
    linked_a.linked_pages.add(linked_b)

    result = lint_wiki(user, company)

    orphan_titles = {p.title for p in result["orphans"]}
    assert "Orphan Result" in orphan_titles
    assert "Linked B" not in orphan_titles


@pytest.mark.django_db
def test_lint_wiki_isolated_by_company(user, company, other_company):
    """Lint only inspects pages for the given user+company."""
    _make_page(user, company, "Co A Orphan")
    _make_page(user, other_company, "Co B Orphan")

    result = lint_wiki(user, company)
    orphan_titles = {p.title for p in result["orphans"]}
    assert "Co A Orphan" in orphan_titles
    assert "Co B Orphan" not in orphan_titles


@pytest.mark.django_db
def test_lint_wiki_appends_log_entry(user, company):
    """lint_wiki appends an entry to the wiki log page."""
    from apps.pkm.services.wiki_ingest_service import LOG_PAGE_TITLE

    _make_page(user, company, "Orphan", content="x")

    lint_wiki(user, company)

    log = WikiPage.objects.get(user=user, company=company, title=LOG_PAGE_TITLE)
    assert "lint" in log.content.lower()


@pytest.mark.django_db
def test_lint_wiki_excludes_health_report_from_orphans(user, company):
    """The health report page itself should not be counted as an orphan."""
    # First lint creates the health report page
    lint_wiki(user, company)

    # Second lint: the health report page exists, should not appear as orphan
    result = lint_wiki(user, company)
    orphan_titles = {p.title for p in result["orphans"]}
    assert HEALTH_REPORT_TITLE not in orphan_titles
