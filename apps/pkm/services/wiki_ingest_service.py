"""Wiki ingest service (Karpathy LLM Wiki pattern, Layer 2 operations).

The **ingest** operation is the write-side of the LLM wiki.  When a user
uploads a new document or creates a note, this service:

  1.  Reads the source chunks/content (masked before LLM call).
  2.  Asks the LLM to produce a markdown **summary page** for the source.
  3.  Reads existing concept/entity pages for context (so the LLM can merge,
      not duplicate).
  4.  Creates or **updates** matching concept/entity pages (merge semantics:
      new info appended to existing content, page reused by title).
  5.  Updates cross-references between pages via ``linked_pages``.
  6.  Re-generates the **index page** (catalog of all wiki pages).
  7.  Appends a timestamped entry to the **log page**.

All operations are scoped per (user, company) for multi-tenant isolation.

The service is designed to be invoked asynchronously via ``django-q2`` (see
``schedule_document_ingest`` / ``schedule_note_ingest``).  In test mode
(``Q_CLUSTER = {"sync": True}``) it runs synchronously.

Security: every string that leaves this process for an external LLM provider
passes through ``data_masker.mask_all`` so that MST (tax IDs), VND amounts,
phone numbers, and emails are masked.  This is the default; users may opt out
per-provider via ``UserLLMConfig.disable_masking`` (wired by the PII masking
feature).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.utils import timezone

from apps.pkm.models import (
    DocumentChunk,
    KnowledgeNote,
    PKMDocument,
    UserLLMConfig,
    WikiPage,
)
from apps.pkm.services.data_masker import mask_all
from apps.pkm.services.llm_service import get_completion

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "INDEX_PAGE_TITLE",
    "LOG_PAGE_TITLE",
    "INGEST_SYSTEM_MESSAGE",
    "build_ingest_prompt",
    "ingest_document",
    "ingest_note",
    "maintain_index_page",
    "append_log_entry",
    "schedule_document_ingest",
    "schedule_note_ingest",
    "TASK_TIMEOUT",
]

#: Reserved titles for the auto-maintained system pages.
INDEX_PAGE_TITLE: str = "Index"
LOG_PAGE_TITLE: str = "Log"

#: django-q2 task configuration (mirrors rag_pipeline).
TASK_TIMEOUT: int = 300

#: System message instructing the LLM how to build the wiki pages from a source.
#: The LLM must return a JSON object with ``summary`` (markdown) and
#: ``concepts`` (list of {title, page_type, content}) so we can persist them
#: deterministically.
INGEST_SYSTEM_MESSAGE: str = (
    "You are the wiki builder for the Visota PKM system. "
    "Given raw source text (a document or note), produce a persistent markdown wiki. "
    "Read the existing concept/entity titles provided and MERGE with them; "
    "do not duplicate an existing concept. "
    "Respond ONLY with a JSON object: "
    '{"summary": "<markdown summary of this source>", '
    '"concepts": [{"title": "...", "page_type": "concept|entity", "content": "<markdown>"}]}. '
    "The summary should be a concise digest of the source. "
    "Each concept entry should capture one recurring concept or entity mentioned in the source. "
    "Use markdown formatting (headings, lists, [[wikilinks]])."
)

#: Maximum chars of source content to send to the LLM in one call.
MAX_SOURCE_CHARS: int = 8000


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _resolve_llm_config(user: User, company: Company) -> UserLLMConfig:
    """Return the user's active LLM config for this company.

    Raises ``ValueError`` if no active config is found.
    """
    config = UserLLMConfig.objects.filter(
        user=user,
        company=company,
        is_active=True,
    ).first()
    if config is None:
        raise ValueError(
            f"No active LLM configuration for user "
            f"{getattr(user, 'username', user)} in this company. "
            "Configure a provider before ingesting into the wiki."
        )
    return config


def _get_existing_concepts_summary(user: User, company: Company) -> str:
    """Return a newline-separated list of existing concept/entity page titles.

    This gives the LLM the context it needs to merge rather than duplicate.
    Returns an empty string if no concept/entity pages exist yet.
    """
    existing = WikiPage.objects.filter(
        user=user,
        company=company,
        page_type__in=[WikiPage.PageType.CONCEPT, WikiPage.PageType.ENTITY],
    ).values_list("title", flat=True)
    titles = list(existing)
    if not titles:
        return ""
    return "Existing concept/entity pages: " + ", ".join(titles)


def _chunks_to_text(chunks: list[DocumentChunk]) -> str:
    """Concatenate chunk contents into a single source-text string.

    Truncated to ``MAX_SOURCE_CHARS`` to keep the LLM prompt bounded.
    """
    parts = [c.content for c in chunks if c.content]
    combined = "\n\n".join(parts)
    if len(combined) > MAX_SOURCE_CHARS:
        combined = combined[:MAX_SOURCE_CHARS] + "\n\n[...truncated...]"
    return combined


def _extract_completion_text(response: Any) -> str:
    """Extract the text content from a litellm completion response (object/dict)."""
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message")
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    return str(content) if content else ""


def _parse_ingest_response(raw: str) -> dict[str, Any]:
    """Parse the JSON object returned by the LLM into a dict.

    Tolerates surrounding markdown code fences (```json ... ```). Falls back to
    an empty result (no concepts) if parsing fails, so a malformed LLM output
    never breaks the ingest pipeline.
    """
    text = raw.strip()
    # Strip markdown code fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the first fence line and the trailing fence line.
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("wiki_ingest: failed to parse LLM JSON response; using empty result.")
        return {"summary": "", "concepts": []}

    if not isinstance(parsed, dict):
        return {"summary": "", "concepts": []}
    parsed.setdefault("summary", "")
    parsed.setdefault("concepts", [])
    if not isinstance(parsed["concepts"], list):
        parsed["concepts"] = []
    return parsed


def _build_summary_title(source_title: str) -> str:
    """Derive a unique-ish title for a source's summary wiki page."""
    return f"Summary: {source_title}"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_ingest_prompt(
    *,
    source_title: str,
    chunks_text: str,
    existing_concepts: str,
    mask: bool = True,
) -> list[dict[str, str]]:
    """Construct the chat message list for the wiki ingest LLM call.

    The user message contains the source content, the source title, and the
    list of existing concept titles so the LLM can merge.

    When ``mask`` is True (the default) the source text and existing concept
    summary are passed through :func:`data_masker.mask_all` so MST, VND
    amounts, phone numbers and emails are obfuscated before the LLM call.
    Callers pass ``mask=False`` when the user's
    ``UserLLMConfig.disable_masking`` flag is True (e.g. local Ollama).

    Args:
        source_title: Title of the source document or note.
        chunks_text: Concatenated source text (will be masked before sending).
        existing_concepts: Summary of existing concept/entity titles (for merge).
        mask: When True, apply PII masking before building the prompt.

    Returns:
        A list of message dicts (system + user) for ``get_completion``.
    """
    if mask:
        masked_source = mask_all(chunks_text)
        masked_existing = mask_all(existing_concepts)
    else:
        masked_source = chunks_text
        masked_existing = existing_concepts
    user_content = (
        f"Source title: {source_title}\n\n"
        f"Existing context:\n{masked_existing or '(none)'}\n\n"
        f"Source content (masked):\n{masked_source}\n\n"
        "Build the wiki summary and concept pages as instructed."
    )
    return [
        {"role": "system", "content": INGEST_SYSTEM_MESSAGE},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Core: create/update wiki pages from parsed LLM output
# ---------------------------------------------------------------------------


def _upsert_concept_page(
    *,
    user: User,
    company: Company,
    title: str,
    page_type: str,
    content: str,
    source_doc: PKMDocument | None,
) -> WikiPage:
    """Create or update a concept/entity page (merge, not duplicate).

    If a page with the same title exists for this (user, company), the new
    content is **appended** under a "Updated" heading and ``last_ingest_at`` is
    refreshed.  Otherwise a new page is created.

    Returns the upserted WikiPage.
    """
    valid_types = {WikiPage.PageType.CONCEPT, WikiPage.PageType.ENTITY}
    if page_type not in valid_types:
        page_type = WikiPage.PageType.CONCEPT

    now = timezone.now()
    page = WikiPage.objects.filter(
        user=user,
        company=company,
        title=title,
    ).first()

    if page is not None:
        # Merge: append the new info, preserve original content.
        separator = "\n\n" if page.content else ""
        update_block = f"### Updated {now.strftime('%Y-%m-%d %H:%M')}\n\n{content}"
        page.content = f"{page.content}{separator}{update_block}"
        page.page_type = page_type  # normalise type if changed
        page.is_ai_generated = True
        page.last_ingest_at = now
        page.save(
            update_fields=[
                "content",
                "page_type",
                "is_ai_generated",
                "last_ingest_at",
                "updated_at",
            ]
        )
    else:
        page = WikiPage.objects.create(
            user=user,
            company=company,
            title=title,
            content=content,
            page_type=page_type,
            is_ai_generated=True,
            last_ingest_at=now,
        )

    if source_doc is not None:
        page.source_refs.add(source_doc)

    return page


def _create_summary_page(
    *,
    user: User,
    company: Company,
    source_title: str,
    summary_md: str,
    source_doc: PKMDocument | None,
) -> WikiPage:
    """Create (or replace) the summary page for a source.

    A summary page is unique per source; re-ingesting a source replaces the
    summary content rather than accumulating it (summaries are meant to reflect
    the latest digest of the source).
    """
    now = timezone.now()
    title = _build_summary_title(source_title)
    page, created = WikiPage.objects.update_or_create(
        user=user,
        company=company,
        title=title,
        defaults={
            "content": summary_md,
            "page_type": WikiPage.PageType.SUMMARY,
            "is_ai_generated": True,
            "last_ingest_at": now,
        },
    )
    if source_doc is not None:
        page.source_refs.add(source_doc)
    _ = created  # noqa: F841 -- kept for debuggability
    return page


# ---------------------------------------------------------------------------
# Index page (catalog)
# ---------------------------------------------------------------------------


def maintain_index_page(user: User, company: Company) -> WikiPage:
    """Re-generate the index page listing all wiki pages for this tenant.

    The index is an ``overview`` page titled ``INDEX_PAGE_TITLE``.  It groups
    pages by ``page_type`` and includes the title + a one-line summary (the
    first non-empty line of the page's content).

    The index page itself is excluded from the listing to avoid recursion.
    The log page is also excluded (it is a special append-only artifact).
    """
    now = timezone.now()
    pages = (
        WikiPage.objects.filter(user=user, company=company)
        .exclude(title__in=[INDEX_PAGE_TITLE, LOG_PAGE_TITLE])
        .order_by("page_type", "title")
    )

    type_labels: dict[str, str] = {
        WikiPage.PageType.SUMMARY: "Summaries",
        WikiPage.PageType.CONCEPT: "Concepts",
        WikiPage.PageType.ENTITY: "Entities",
        WikiPage.PageType.OVERVIEW: "Overview",
        WikiPage.PageType.SYNTHESIS: "Synthesis",
    }

    sections: list[str] = []
    current_type: str | None = None
    for page in pages:
        if page.page_type != current_type:
            current_type = page.page_type
            label = type_labels.get(current_type, current_type.capitalize())
            sections.append(f"\n## {label}\n")
        one_liner = _extract_one_liner(page.content)
        sections.append(f"- **[[{page.title}]]** -- {one_liner}")

    body = "\n".join(sections).strip() or "_(No wiki pages yet.)_"
    content = (
        f"# Wiki Index\n\n"
        f"Auto-maintained catalog of all wiki pages. "
        f"Last updated: {now.strftime('%Y-%m-%d %H:%M')}.\n\n{body}\n"
    )

    index_page, _ = WikiPage.objects.update_or_create(
        user=user,
        company=company,
        title=INDEX_PAGE_TITLE,
        defaults={
            "content": content,
            "page_type": WikiPage.PageType.OVERVIEW,
            "is_ai_generated": True,
            "is_system": True,
            "last_ingest_at": now,
        },
    )
    return index_page


def _extract_one_liner(content: str) -> str:
    """Extract a one-line summary from markdown content.

    Returns the first non-empty, non-heading line, truncated to 100 chars.
    Falls back to the first heading without the ``#`` prefix.
    """
    if not content:
        return ""
    for line in content.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            if len(stripped) > 100:
                return stripped[:97] + "..."
            return stripped
    return ""


# ---------------------------------------------------------------------------
# Log page (append-only)
# ---------------------------------------------------------------------------


def append_log_entry(
    user: User,
    company: Company,
    *,
    operation: str,
    detail: str = "",
) -> WikiPage:
    """Append a timestamped entry to the log page (creating it if needed).

    The log page is an ``overview`` page titled ``LOG_PAGE_TITLE``.  Entries
    are appended in chronological order (newest at the bottom).

    Args:
        user: The user whose wiki the log belongs to.
        company: The company scope.
        operation: Short operation name (e.g. "ingest", "query", "lint").
        detail: Human-readable detail (e.g. source title).

    Returns the log WikiPage.
    """
    now = timezone.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    entry_line = f"- [{timestamp}] {operation}: {detail}".strip()

    log_page = WikiPage.objects.filter(
        user=user,
        company=company,
        title=LOG_PAGE_TITLE,
    ).first()

    if log_page is None:
        content = f"# Wiki Log\n\nAppend-only timeline of wiki operations.\n\n{entry_line}\n"
        log_page = WikiPage.objects.create(
            user=user,
            company=company,
            title=LOG_PAGE_TITLE,
            content=content,
            page_type=WikiPage.PageType.OVERVIEW,
            is_ai_generated=True,
            is_system=True,
            last_ingest_at=now,
        )
    else:
        separator = "\n" if log_page.content and not log_page.content.endswith("\n") else ""
        log_page.content = f"{log_page.content}{separator}{entry_line}"
        log_page.last_ingest_at = now
        log_page.save(update_fields=["content", "last_ingest_at", "updated_at"])

    return log_page


# ---------------------------------------------------------------------------
# Public: ingest entry points
# ---------------------------------------------------------------------------


def ingest_document(document_id: int) -> dict[str, Any]:
    """Ingest a PKMDocument into the wiki (summary + concepts + index + log).

    Pipeline:
        1. Load the document (must belong to a user+company).
        2. Resolve the user's active LLM config.
        3. Collect document chunks as source text.
        4. Gather existing concept titles for merge context.
        5. Build the prompt (source + context, masked).
        6. Call the LLM and parse summary + concepts.
        7. Create the summary page, upsert concept/entity pages.
        8. Link the summary to its concepts via ``linked_pages``.
        9. Refresh the index page.
       10. Append a log entry.

    Args:
        document_id: Primary key of the PKMDocument to ingest.

    Returns:
        A dict with ``summary_page_id`` and ``concept_page_ids``.

    Raises:
        PKMDocument.DoesNotExist: If the document does not exist.
        ValueError: If no active LLM config exists for the document's user.
    """
    document = PKMDocument.objects.get(pk=document_id)
    user = document.user
    company = document.company

    llm_config = _resolve_llm_config(user, company)
    mask_enabled = not getattr(llm_config, "disable_masking", False)

    chunks = list(DocumentChunk.objects.filter(document=document).order_by("chunk_index"))
    chunks_text = _chunks_to_text(chunks)
    existing_concepts = _get_existing_concepts_summary(user, company)

    messages = build_ingest_prompt(
        source_title=document.title,
        chunks_text=chunks_text,
        existing_concepts=existing_concepts,
        mask=mask_enabled,
    )

    response = get_completion(llm_config, messages, stream=False)
    raw_content = _extract_completion_text(response)
    parsed = _parse_ingest_response(raw_content)

    with transaction.atomic():
        # 1. Summary page
        summary_md = parsed.get("summary") or (
            f"# Summary of {document.title}\n\n(No summary generated.)"
        )
        summary_page = _create_summary_page(
            user=user,
            company=company,
            source_title=document.title,
            summary_md=summary_md,
            source_doc=document,
        )

        # 2. Concept/entity pages (upsert)
        concept_pages: list[WikiPage] = []
        for concept in parsed.get("concepts", []):
            title = str(concept.get("title", "")).strip()
            if not title:
                continue
            page_type = str(concept.get("page_type", "concept")).strip()
            content = str(concept.get("content", "")).strip()
            page = _upsert_concept_page(
                user=user,
                company=company,
                title=title,
                page_type=page_type,
                content=content,
                source_doc=document,
            )
            concept_pages.append(page)

        # 3. Cross-reference summary <-> concepts
        if concept_pages:
            summary_page.linked_pages.add(*concept_pages)

        # 4. Index page
        maintain_index_page(user, company)

        # 5. Log entry
        append_log_entry(
            user,
            company,
            operation="ingest",
            detail=f'Document "{document.title}" (id={document.id})',
        )

    logger.info(
        "ingest_document: ingested document %s for user %s (%d concept pages)",
        document_id,
        getattr(user, "username", user),
        len(concept_pages),
    )

    return {
        "summary_page_id": summary_page.id,
        "concept_page_ids": [p.id for p in concept_pages],
    }


def ingest_note(note_id: int) -> dict[str, Any]:
    """Ingest a KnowledgeNote into the wiki.

    Works analogously to :func:`ingest_document` but the source text comes
    from the note's ``content`` field instead of document chunks.

    Args:
        note_id: Primary key of the KnowledgeNote to ingest.

    Returns:
        A dict with ``summary_page_id`` and ``concept_page_ids``.
    """
    note = KnowledgeNote.objects.get(pk=note_id)
    user = note.user
    company = note.company

    llm_config = _resolve_llm_config(user, company)
    mask_enabled = not getattr(llm_config, "disable_masking", False)

    chunks_text = note.content or ""
    if len(chunks_text) > MAX_SOURCE_CHARS:
        chunks_text = chunks_text[:MAX_SOURCE_CHARS] + "\n\n[...truncated...]"
    existing_concepts = _get_existing_concepts_summary(user, company)

    messages = build_ingest_prompt(
        source_title=note.title,
        chunks_text=chunks_text,
        existing_concepts=existing_concepts,
        mask=mask_enabled,
    )

    response = get_completion(llm_config, messages, stream=False)
    raw_content = _extract_completion_text(response)
    parsed = _parse_ingest_response(raw_content)

    with transaction.atomic():
        summary_md = parsed.get("summary") or (
            f"# Summary of {note.title}\n\n(No summary generated.)"
        )
        # Notes have no PKMDocument to reference; pass None as the source doc.
        summary_page = _create_summary_page(
            user=user,
            company=company,
            source_title=note.title,
            summary_md=summary_md,
            source_doc=None,
        )

        concept_pages: list[WikiPage] = []
        for concept in parsed.get("concepts", []):
            title = str(concept.get("title", "")).strip()
            if not title:
                continue
            page_type = str(concept.get("page_type", "concept")).strip()
            content = str(concept.get("content", "")).strip()
            page = _upsert_concept_page(
                user=user,
                company=company,
                title=title,
                page_type=page_type,
                content=content,
                source_doc=None,
            )
            concept_pages.append(page)

        if concept_pages:
            summary_page.linked_pages.add(*concept_pages)

        maintain_index_page(user, company)
        append_log_entry(
            user,
            company,
            operation="ingest",
            detail=f'Note "{note.title}" (id={note.id})',
        )

    logger.info(
        "ingest_note: ingested note %s for user %s (%d concept pages)",
        note_id,
        getattr(user, "username", user),
        len(concept_pages),
    )

    return {
        "summary_page_id": summary_page.id,
        "concept_page_ids": [p.id for p in concept_pages],
    }


# ---------------------------------------------------------------------------
# Async scheduling (django-q2)
# ---------------------------------------------------------------------------


def schedule_document_ingest(document_id: int) -> Any:
    """Enqueue ``ingest_document`` as a django-q2 async task.

    Args:
        document_id: Primary key of the PKMDocument to ingest.

    Returns:
        The result of ``async_task`` (task id or sync result).
    """
    from django_q.tasks import async_task

    return async_task(
        "apps.pkm.services.wiki_ingest_service.ingest_document",
        document_id,
        timeout=TASK_TIMEOUT,
    )


def schedule_note_ingest(note_id: int) -> Any:
    """Enqueue ``ingest_note`` as a django-q2 async task.

    Args:
        note_id: Primary key of the KnowledgeNote to ingest.

    Returns:
        The result of ``async_task`` (task id or sync result).
    """
    from django_q.tasks import async_task

    return async_task(
        "apps.pkm.services.wiki_ingest_service.ingest_note",
        note_id,
        timeout=TASK_TIMEOUT,
    )
