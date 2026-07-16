"""Export service for PKM data (notes + wiki pages + QA history).

Provides a reusable, side-effect-free exporter used by both:

  * The ``GET /api/v1/pkm/export/`` REST endpoint (JSON response).
  * The ``export_pkm_data`` management command (writes a file).

The exporter is **scoped** by ``(user, company)`` for multi-tenant
isolation. It never exports encrypted credentials (``UserLLMConfig``) or
ephemeral data (``UserInteractionLog``).

Output shape (JSON)::

    {
      "user": {"id": 1, "username": "admin"},
      "company": {"id": 1, "code": "ACME"},
      "exported_at": "2026-07-17T10:00:00Z",
      "notes": [
        {"id": 1, "title": "...", "content": "...", "tags": ["vat", "hbh"],
         "role_context": "accountant", "is_pinned": false,
         "created_at": "...", "updated_at": "..."}
      ],
      "wiki_pages": [
        {"id": 1, "title": "...", "content": "...", "page_type": "summary",
         "tags": [], "is_ai_generated": true, "is_system": false,
         "last_ingest_at": "...", "created_at": "...", "updated_at": "..."}
      ]
    }

Markdown output bundles everything into a single ``.md`` file with H1
sections per note / wiki page.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import KnowledgeNote, WikiPage

logger = logging.getLogger(__name__)


def export_user_pkm_data(
    *,
    user: User,
    company: Company,
    include_notes: bool = True,
    include_wiki: bool = True,
) -> dict[str, Any]:
    """Build the export payload dict for ``user`` scoped to ``company``.

    This is the canonical exporter used by both the API endpoint and the
    management command. The result is JSON-serialisable.

    Parameters
    ----------
    user
        The user whose data is being exported.
    company
        The company scope (multi-tenant isolation).
    include_notes
        Whether to include knowledge notes (default True).
    include_wiki
        Whether to include wiki pages (default True).
    """
    notes_qs = (
        KnowledgeNote.objects.filter(user=user, company=company)
        .prefetch_related("tags")
        .order_by("-is_pinned", "-updated_at", "id")
    )
    wiki_qs = (
        WikiPage.objects.filter(user=user, company=company)
        .prefetch_related("tags")
        .order_by("-updated_at", "id")
    )

    payload: dict[str, Any] = {
        "user": {"id": user.id, "username": user.username},
        "company": {"id": company.id, "code": company.code},
        "exported_at": timezone.now().isoformat(),
    }

    if include_notes:
        payload["notes"] = [_serialize_note(n) for n in notes_qs]
    if include_wiki:
        payload["wiki_pages"] = [_serialize_wiki_page(w) for w in wiki_qs]

    return payload


def _serialize_note(note: KnowledgeNote) -> dict[str, Any]:
    """Serialise a KnowledgeNote to a plain JSON-friendly dict."""
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": [t.name for t in note.tags.all()],
        "role_context": note.role_context,
        "is_pinned": note.is_pinned,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


def _serialize_wiki_page(page: WikiPage) -> dict[str, Any]:
    """Serialise a WikiPage to a plain JSON-friendly dict."""
    return {
        "id": page.id,
        "title": page.title,
        "content": page.content,
        "page_type": page.page_type,
        "tags": [t.name for t in page.tags.all()],
        "is_ai_generated": page.is_ai_generated,
        "is_system": page.is_system,
        "last_ingest_at": page.last_ingest_at.isoformat() if page.last_ingest_at else None,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_export_markdown(payload: dict[str, Any]) -> str:
    """Render an export payload (from ``export_user_pkm_data``) as Markdown.

    Produces a single self-contained ``.md`` document with one H1 per
    note / wiki page, preserving the Karpathy wiki-as-markdown convention.
    """
    user = payload.get("user", {})
    company = payload.get("company", {})
    exported_at = payload.get("exported_at", "")

    lines: list[str] = []
    lines.append(f"# PKM Export — {user.get('username', '')}")
    lines.append("")
    lines.append(f"- User: {user.get('username', '')} (id={user.get('id', '')})")
    lines.append(f"- Company: {company.get('code', '')} (id={company.get('id', '')})")
    lines.append(f"- Exported at: {exported_at}")
    lines.append("")

    notes = payload.get("notes", [])
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"### {note.get('title', '')}")
            tags = note.get("tags", [])
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            lines.append("")
            lines.append(note.get("content", "") or "")
            lines.append("")
            lines.append("---")
            lines.append("")

    wiki_pages = payload.get("wiki_pages", [])
    if wiki_pages:
        lines.append("## Wiki Pages")
        lines.append("")
        for page in wiki_pages:
            lines.append(f"### {page.get('title', '')}")
            lines.append(f"Type: {page.get('page_type', '')}")
            tags = page.get("tags", [])
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            lines.append("")
            lines.append(page.get("content", "") or "")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def parse_exported_at(payload: dict[str, Any]) -> datetime | None:
    """Best-effort parse of the ``exported_at`` ISO timestamp."""
    raw = payload.get("exported_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
