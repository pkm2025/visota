"""Wiki lint service (Karpathy LLM Wiki pattern, health check operation).

The **lint** operation is the health-check of the LLM wiki.  It scans a
tenant's wiki pages and produces a structured health report highlighting
issues that need attention:

  1.  **Orphan pages** — pages with no inbound ``linked_pages`` (nothing
      references them).  These are "dead ends" in the wiki graph.
  2.  **Potential contradictions** — the same concept may appear in
      multiple pages (overlapping titles or shared source references),
      indicating possible duplicate or conflicting definitions.
  3.  **Stale pages** — a page whose ``last_ingest_at`` is older than the
      newest source document ingested for this tenant.  The page may not
      reflect the latest information.
  4.  **Missing concept pages** — a ``[[wikilink]]`` in page content that
      points to a title with no corresponding WikiPage.  The wiki has a
      dangling reference.

The lint also generates a **health report** as a ``WikiPage``
(``page_type=overview``) summarising all findings.  This report is itself
a persistent, compounding artifact (re-generated on each lint run).

All checks are scoped per (user, company) for multi-tenant isolation.
Lint is a deterministic, local analysis — no LLM calls are made.

Security: no data leaves the process; lint operates entirely on stored
wiki content.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.pkm.models import PKMDocument, WikiPage
from apps.pkm.services.wiki_ingest_service import (
    INDEX_PAGE_TITLE,
    LOG_PAGE_TITLE,
    append_log_entry,
)

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "HEALTH_REPORT_TITLE",
    "find_orphan_pages",
    "find_contradictions",
    "find_stale_pages",
    "find_missing_concept_pages",
    "generate_health_report",
    "lint_wiki",
]

#: Reserved title for the auto-generated health report page.
HEALTH_REPORT_TITLE: str = "Wiki Health Report"

#: Special system pages that should never be flagged as orphans or stale.
_SYSTEM_PAGE_TITLES: frozenset[str] = frozenset(
    {INDEX_PAGE_TITLE, LOG_PAGE_TITLE, HEALTH_REPORT_TITLE}
)

#: Regex for extracting [[wikilinks]] from markdown content.
_WIKILINK_RE: re.Pattern[str] = re.compile(r"\[\[([^\]]+)\]\]")

#: Minimum title similarity for contradiction detection (Jaccard on word sets).
_CONTRADICTION_TITLE_THRESHOLD: float = 0.3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _base_queryset(user: User, company: Company):
    """Return the base WikiPage queryset scoped to this user+company."""
    return WikiPage.objects.filter(user=user, company=company)


def _user_pages_excluding_system(user: User, company: Company):
    """Return wiki pages excluding the auto-maintained system pages."""
    return _base_queryset(user, company).exclude(title__in=_SYSTEM_PAGE_TITLES)


def _word_set(title: str) -> set[str]:
    """Tokenise a title into a lowercased word set for similarity comparison."""
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]+", title) if len(w) > 1}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two word sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# 1. Orphan page detection
# ---------------------------------------------------------------------------


def find_orphan_pages(user: User, company: Company) -> list[WikiPage]:
    """Find wiki pages with no inbound ``linked_pages`` references.

    A page is an orphan if no other page (within the same tenant) links to
    it via ``linked_pages``.  Since ``linked_pages`` is a symmetrical M2M,
    we need to check whether the page appears in any other page's
    ``linked_pages`` set.

    The auto-maintained system pages (Index, Log, Health Report) are
    excluded — they are reference artifacts, not content pages.

    Args:
        user: The wiki owner.
        company: The company scope.

    Returns:
        A list of WikiPage objects that are orphans.
    """
    candidate_pages = list(_user_pages_excluding_system(user, company))
    if not candidate_pages:
        return []

    candidate_ids = {p.id for p in candidate_pages}

    # Collect all page IDs that are linked-to by some other page.
    # linked_pages is symmetrical, so if A links B, then B.linked_pages
    # includes A. We need pages that have at least one linked_page that is
    # NOT themselves (i.e. someone references them). Since it's symmetrical,
    # any link relationship means the page is "connected". But for true
    # "inbound" semantics, we want: is this page referenced by another page?
    #
    # With symmetrical M2M, A.linked_pages.add(B) makes both A->B and B->A.
    # So any page that has at least one linked_pages entry pointing to
    # another content page is NOT an orphan.
    linked_page_ids: set[int] = set()
    for page in candidate_pages:
        for linked in page.linked_pages.all():
            if linked.id in candidate_ids and linked.id != page.id:
                # `page` links to `linked`, so `linked` has an inbound link.
                linked_page_ids.add(linked.id)

    return [p for p in candidate_pages if p.id not in linked_page_ids]


# ---------------------------------------------------------------------------
# 2. Contradiction detection (same concept in multiple pages)
# ---------------------------------------------------------------------------


def find_contradictions(user: User, company: Company) -> list[dict[str, Any]]:
    """Detect potential contradictions: same concept across multiple pages.

    Two heuristics are used:
      - **Title similarity**: Two concept/entity pages with very similar
        titles (Jaccard word-set similarity >= threshold) may describe the
        same concept with conflicting definitions.
      - **Shared source references**: Two pages citing the exact same
        source document(s) may be duplicating information.

    Args:
        user: The wiki owner.
        company: The company scope.

    Returns:
        A list of dicts, each describing a potential contradiction:
        ``{"pages": [WikiPage, WikiPage], "reason": str}``.
    """
    pages = list(
        _user_pages_excluding_system(user, company).filter(
            page_type__in=[WikiPage.PageType.CONCEPT, WikiPage.PageType.ENTITY]
        )
    )

    contradictions: list[dict[str, Any]] = []
    seen_pairs: set[frozenset[int]] = set()

    # Heuristic 1: Title similarity (Jaccard on word sets OR substring containment)
    title_words: dict[int, set[str]] = {p.id: _word_set(p.title) for p in pages}
    for i, p1 in enumerate(pages):
        for p2 in pages[i + 1 :]:
            pair_key = frozenset({p1.id, p2.id})
            if pair_key in seen_pairs:
                continue
            sim = _jaccard_similarity(title_words[p1.id], title_words[p2.id])
            # Also check substring containment: "VAT" is contained in "VAT (Value Added Tax)"
            t1_lower = p1.title.lower()
            t2_lower = p2.title.lower()
            contains = (t1_lower in t2_lower or t2_lower in t1_lower) and (t1_lower != t2_lower)
            if sim >= _CONTRADICTION_TITLE_THRESHOLD or contains:
                seen_pairs.add(pair_key)
                contradictions.append(
                    {
                        "pages": [p1, p2],
                        "reason": f"Similar titles (similarity={sim:.2f})",
                    }
                )

    # Heuristic 2: Shared source references
    for i, p1 in enumerate(pages):
        p1_sources = set(p1.source_refs.values_list("id", flat=True))
        if not p1_sources:
            continue
        for p2 in pages[i + 1 :]:
            p2_sources = set(p2.source_refs.values_list("id", flat=True))
            shared = p1_sources & p2_sources
            if shared:
                pair_key = frozenset({p1.id, p2.id})
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    contradictions.append(
                        {
                            "pages": [p1, p2],
                            "reason": f"Shared source references ({len(shared)} doc(s))",
                        }
                    )

    return contradictions


# ---------------------------------------------------------------------------
# 3. Stale page detection
# ---------------------------------------------------------------------------


def find_stale_pages(user: User, company: Company) -> list[WikiPage]:
    """Find pages not updated after a newer source document was ingested.

    A page is stale if:
      - It has a ``last_ingest_at`` timestamp, AND
      - There exists a ``PKMDocument`` (status=processed) for this tenant
        with ``created_at`` later than the page's ``last_ingest_at``.

    Pages without ``last_ingest_at`` are excluded (they were never ingested
    by the AI pipeline and have no basis for staleness comparison).

    System pages (Index, Log, Health Report) are excluded.

    Args:
        user: The wiki owner.
        company: The company scope.

    Returns:
        A list of stale WikiPage objects.
    """
    newest_source = (
        PKMDocument.objects.filter(user=user, company=company).order_by("-created_at").first()
    )
    if newest_source is None:
        return []

    pages = list(_user_pages_excluding_system(user, company).filter(last_ingest_at__isnull=False))
    if not pages:
        return []

    return [
        p
        for p in pages
        if p.last_ingest_at is not None and p.last_ingest_at < newest_source.created_at
    ]


# ---------------------------------------------------------------------------
# 4. Missing concept page detection ([[wikilinks]] without a target)
# ---------------------------------------------------------------------------


def find_missing_concept_pages(user: User, company: Company) -> list[str]:
    """Find ``[[wikilinks]]`` in content that point to non-existent pages.

    Scans all wiki page content for ``[[Title]]`` style links and reports
    titles that do not have a corresponding WikiPage in this tenant.

    The system page titles (Index, Log, Health Report) and existing page
    titles are excluded from the results.

    Args:
        user: The wiki owner.
        company: The company scope.

    Returns:
        A sorted list of missing concept titles (deduplicated).
    """
    existing_titles: set[str] = set(_base_queryset(user, company).values_list("title", flat=True))
    existing_titles.update(_SYSTEM_PAGE_TITLES)

    missing: set[str] = set()
    for page in _base_queryset(user, company):
        for match in _WIKILINK_RE.finditer(page.content or ""):
            title = match.group(1).strip()
            if title and title not in existing_titles:
                missing.add(title)

    return sorted(missing)


# ---------------------------------------------------------------------------
# 5. Health report generation
# ---------------------------------------------------------------------------


def _format_report_content(
    *,
    orphans: list[WikiPage],
    contradictions: list[dict[str, Any]],
    stale: list[WikiPage],
    missing_concepts: list[str],
) -> str:
    """Render the markdown body of the health report."""
    now = timezone.now()
    sections: list[str] = [
        f"# {HEALTH_REPORT_TITLE}",
        "",
        f"Auto-generated wiki health report. Last updated: {now.strftime('%Y-%m-%d %H:%M')}.",
        "",
    ]

    # Summary counts
    sections.append("## Summary")
    sections.append("")
    sections.append(f"- Orphan pages: **{len(orphans)}**")
    sections.append(f"- Potential contradictions: **{len(contradictions)}**")
    sections.append(f"- Stale pages: **{len(stale)}**")
    sections.append(f"- Missing concept pages: **{len(missing_concepts)}**")
    sections.append("")

    # Orphan pages
    sections.append("## Orphan Pages")
    sections.append("")
    if orphans:
        for p in orphans:
            sections.append(f"- **{p.title}** ({p.page_type}) — no inbound links")
    else:
        sections.append("_(No orphan pages detected.)_")
    sections.append("")

    # Contradictions
    sections.append("## Potential Contradictions")
    sections.append("")
    if contradictions:
        for c in contradictions:
            titles = ", ".join(p.title for p in c["pages"])
            sections.append(f"- {titles} — {c['reason']}")
    else:
        sections.append("_(No potential contradictions detected.)_")
    sections.append("")

    # Stale pages
    sections.append("## Stale Pages")
    sections.append("")
    if stale:
        for p in stale:
            sections.append(
                f"- **{p.title}** — last ingested {p.last_ingest_at.strftime('%Y-%m-%d %H:%M')}"
            )
    else:
        sections.append("_(No stale pages detected.)_")
    sections.append("")

    # Missing concepts
    sections.append("## Missing Concept Pages")
    sections.append("")
    if missing_concepts:
        for title in missing_concepts:
            sections.append(f"- [[{title}]] — mentioned but no page exists")
    else:
        sections.append("_(No missing concept pages detected.)_")
    sections.append("")

    return "\n".join(sections)


def generate_health_report(
    user: User,
    company: Company,
    *,
    findings: dict[str, Any] | None = None,
) -> WikiPage:
    """Generate (or update) the health report WikiPage.

    If ``findings`` is not provided, the lint checks are run automatically.
    The report is saved as a ``WikiPage`` with ``page_type=overview`` and
    title ``HEALTH_REPORT_TITLE``.  Re-running lint updates the same page
    (idempotent via ``update_or_create``).

    Args:
        user: The wiki owner.
        company: The company scope.
        findings: Pre-computed findings dict (optional). Keys: ``orphans``,
            ``contradictions``, ``stale``, ``missing_concepts``.

    Returns:
        The health report WikiPage.
    """
    if findings is None:
        findings = {
            "orphans": find_orphan_pages(user, company),
            "contradictions": find_contradictions(user, company),
            "stale": find_stale_pages(user, company),
            "missing_concepts": find_missing_concept_pages(user, company),
        }

    content = _format_report_content(
        orphans=findings["orphans"],
        contradictions=findings["contradictions"],
        stale=findings["stale"],
        missing_concepts=findings["missing_concepts"],
    )

    now = timezone.now()
    report, _ = WikiPage.objects.update_or_create(
        user=user,
        company=company,
        title=HEALTH_REPORT_TITLE,
        defaults={
            "content": content,
            "page_type": WikiPage.PageType.OVERVIEW,
            "is_ai_generated": True,
            "is_system": True,
            "last_ingest_at": now,
        },
    )
    return report


# ---------------------------------------------------------------------------
# Orchestrator: lint_wiki
# ---------------------------------------------------------------------------


def lint_wiki(user: User, company: Company) -> dict[str, Any]:
    """Run all lint checks and generate the health report.

    This is the main entry point for the lint operation.  It runs all four
    checks, generates the health report page, and appends a log entry.

    Args:
        user: The wiki owner.
        company: The company scope.

    Returns:
        A dict with keys:
        - ``orphans``: list of orphan WikiPage objects.
        - ``contradictions``: list of contradiction dicts.
        - ``stale``: list of stale WikiPage objects.
        - ``missing_concepts``: list of missing concept title strings.
        - ``report_page_id``: PK of the generated health report WikiPage.
    """
    orphans = find_orphan_pages(user, company)
    contradictions = find_contradictions(user, company)
    stale = find_stale_pages(user, company)
    missing_concepts = find_missing_concept_pages(user, company)

    findings = {
        "orphans": orphans,
        "contradictions": contradictions,
        "stale": stale,
        "missing_concepts": missing_concepts,
    }

    report = generate_health_report(user, company, findings=findings)

    append_log_entry(
        user,
        company,
        operation="lint",
        detail=(
            f"Wiki health check: {len(orphans)} orphan(s), "
            f"{len(contradictions)} contradiction(s), "
            f"{len(stale)} stale, {len(missing_concepts)} missing concept(s)"
        ),
    )

    logger.info(
        "lint_wiki: user=%s company=%s orphans=%d contradictions=%d stale=%d missing=%d",
        getattr(user, "username", user),
        getattr(company, "code", company),
        len(orphans),
        len(contradictions),
        len(stale),
        len(missing_concepts),
    )

    return {
        "orphans": orphans,
        "contradictions": contradictions,
        "stale": stale,
        "missing_concepts": missing_concepts,
        "report_page_id": report.id,
    }
