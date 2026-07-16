"""RAG-powered Q&A service for the PKM module.

This module orchestrates the full Retrieval-Augmented Generation pipeline for
answering user questions:

    1.  Embed the question via ``llm_service.get_embedding``
    2.  Search for similar document chunks via ``vector_store.search_similar``
    3.  Search the user's notes by keyword (hybrid retrieval)
    4.  Build a context string from the retrieved chunks + notes
    5.  Construct a chat prompt (Vietnamese system message + context + question)
    6.  Call ``llm_service.get_completion`` (mocked in tests)
    7.  Collect source references (chunk_id, document_title, content preview)

All retrieval is scoped by ``user_id`` and ``company_id`` to enforce per-user
and multi-tenant isolation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Q

from apps.pkm.models import DocumentChunk, KnowledgeNote, QAHistory, UserLLMConfig
from apps.pkm.services.interaction_service import get_context_summary
from apps.pkm.services.llm_service import get_completion, get_embedding
from apps.pkm.services.vector_store import search_similar

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "answer_question",
    "build_prompt",
    "save_qa_history",
    "DEFAULT_TOP_K",
    "DEFAULT_NOTE_SEARCH_LIMIT",
    "PREVIEW_LENGTH",
    "SYSTEM_MESSAGE",
]

#: Number of similar chunks to retrieve from the vector store.
DEFAULT_TOP_K: int = 5

#: Maximum number of notes to retrieve via keyword search.
DEFAULT_NOTE_SEARCH_LIMIT: int = 5

#: Number of characters to include in a source/preview snippet.
PREVIEW_LENGTH: int = 200

#: System message instructing the LLM to answer in Vietnamese based on context.
SYSTEM_MESSAGE: str = (
    "Ban la tro ly AI cua nguoi dung trong he thong Quan Ly Tri Thuc Cá Nhan (PKM) "
    "cua phan mem ERP Visota. "
    "Tra loi cau hoi cua nguoi dung dua TREN thong tin duoc cung cap trong phan 'NGU CANH' "
    "(context) ben duoi. Neu thong tin khong co trong ngu canh, hay noi rang ban khong tim "
    "thay thong tin phu hop. Luon trich dan nguon (ten tai lieu hoac ghi chu) khi phan tich. "
    "Tra loi bang tieng Viet, ro rang va de hieu. "
    "Phan 'HOAT DONG NGUOI DUNG GAU DAY' mo ta cac hoat dong nghiep vu gan nhat cua nguoi dung "
    "(module hien tai, vai tro, cac su kien nghiep vu voi gia tri). "
    "Su dung thong tin nay de ca nhan hoa cau tra loi cho phu hop voi ngu canh cong viec cua ho."
)


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _extract_embedding_vector(response: Any) -> list[float]:
    """Extract a single embedding vector from a litellm embedding response.

    litellm returns an object with a ``.data`` list whose first element has an
    ``.embedding`` attribute. This helper normalises dict/object shapes into a
    flat ``list[float]``.
    """
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    if not data:
        raise ValueError("Embedding response contains no data.")

    first = data[0]
    emb = getattr(first, "embedding", None)
    if emb is None and isinstance(first, dict):
        emb = first.get("embedding")
    if not emb:
        raise ValueError("Embedding response item has no embedding attribute.")
    return list(emb)


def _search_notes(
    user: User,
    company: Company,
    question: str,
    limit: int = DEFAULT_NOTE_SEARCH_LIMIT,
) -> list[dict[str, Any]]:
    """Search the user's notes by keyword (title or content contains question terms).

    Performs a simple case-insensitive ``icontains`` match against the first
    significant word(s) of the question. Results are scoped by user + company.

    Returns a list of dicts with keys: ``id``, ``title``, ``content``,
    ``content_preview``, ``source_type``.
    """
    keywords = [w for w in question.strip().split() if len(w) >= 2]
    notes_qs = KnowledgeNote.objects.filter(user=user, company=company)
    if keywords:
        query = Q()
        for kw in keywords:
            query |= Q(title__icontains=kw) | Q(content__icontains=kw)
        notes_qs = notes_qs.filter(query).distinct()
    notes = list(notes_qs[:limit])

    return [
        {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "content_preview": note.content[:PREVIEW_LENGTH],
            "source_type": "note",
        }
        for note in notes
    ]


def _build_context_string(
    chunks: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    interaction_context: str | None = None,
) -> str:
    """Assemble a human-readable context string from retrieved chunks + notes.

    The context is labelled and structured so the LLM can distinguish between
    document chunks and personal notes.

    If ``interaction_context`` is provided (a summary of the user's recent
    activity from ``interaction_service.get_context_summary``), it is prepended
    as a 'Recent user activity' section so the LLM can personalise its answer.
    """
    parts: list[str] = []

    # Interaction context summary is prepended to the RAG context
    if interaction_context:
        parts.append("=== HOAT DONG NGUOI DUNG GAU DAY (Recent user activity) ===")
        parts.append(interaction_context)

    if chunks:
        parts.append("=== TAI LIEU / DOANH VAN BAN ===")
        for i, chunk in enumerate(chunks, start=1):
            doc_title = chunk.get("document_title", "Khong ro")
            parts.append(f"[Doan {i}] (Nguon: {doc_title}) {chunk['content']}")

    if notes:
        parts.append("\n=== GHI CHU CA NHAN ===")
        for i, note in enumerate(notes, start=1):
            parts.append(f"[Ghi chu {i}] (Tieu de: {note['title']}) {note['content_preview']}")

    return "\n\n".join(parts) if parts else "Khong co thong tin phu hop."


def _collect_sources(
    chunks: list[dict[str, Any]],
    notes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collect source references from retrieved chunks and notes.

    Each source dict has: ``chunk_id`` (or ``note_id``), ``document_title``,
    ``source_type``, ``content_preview``.
    """
    sources: list[dict[str, Any]] = []

    for chunk in chunks:
        sources.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "embedding_id": chunk.get("id"),
                "document_title": chunk.get("document_title", "Khong ro"),
                "content_preview": chunk["content"][:PREVIEW_LENGTH],
                "distance": chunk.get("distance"),
                "source_type": "document_chunk",
            }
        )

    for note in notes:
        sources.append(
            {
                "note_id": note["id"],
                "document_title": note["title"],
                "content_preview": note["content_preview"],
                "source_type": "note",
            }
        )

    return sources


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
            f"Khong tim thay cau hinh LLM hoat dong cho nguoi dung "
            f"{getattr(user, 'username', user)} trong cong ty nay. "
            "Vui long cau hinh provider truoc khi su dung Q&A."
        )
    return config


def _enrich_chunks_with_titles(
    raw_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach ``document_title`` to each chunk dict by resolving chunk -> document.

    The ``search_similar`` function returns ``chunk_id`` and ``content`` but
    not the parent document title. We batch-fetch the related chunks and their
    documents to enrich the result.
    """
    chunk_ids = [c["chunk_id"] for c in raw_chunks if c.get("chunk_id") is not None]
    if not chunk_ids:
        return raw_chunks

    # Fetch chunks -> document titles in a single query
    doc_titles: dict[int, str] = {}
    for chunk in DocumentChunk.objects.filter(id__in=chunk_ids).select_related("document"):
        doc_titles[chunk.id] = chunk.document.title

    for c in raw_chunks:
        cid: int | None = c.get("chunk_id")
        c["document_title"] = doc_titles.get(cid, "Khong ro") if cid is not None else "Khong ro"
    return raw_chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_prompt(
    context_chunks: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    question: str,
    interaction_context: str | None = None,
) -> list[dict[str, str]]:
    """Construct the chat message list for the LLM completion call.

    The messages list follows the OpenAI chat format:

        [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": "<context>\\n\\n<question>"},
        ]

    Args:
        context_chunks: List of retrieved chunk dicts (from search_similar +
            enriched with ``document_title``).
        notes: List of retrieved note dicts (from ``_search_notes``).
        question: The user's original question.
        interaction_context: Optional summary of the user's recent activity
            (from ``interaction_service.get_context_summary``). Prepended to
            the RAG context as a 'Recent user activity' section.

    Returns:
        A list of message dicts ready for ``llm_service.get_completion``.
    """
    context_str = _build_context_string(context_chunks, notes, interaction_context)
    user_content = (
        f"NGU CANH (Context):\n{context_str}\n\n"
        f"CAU HOI:\n{question}\n\n"
        "Vui long tra loi cau hoi dua tren ngu canh tren. Trich dan nguon."
    )
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_content},
    ]


def answer_question(
    user: User,
    company: Company,
    question: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    note_limit: int = DEFAULT_NOTE_SEARCH_LIMIT,
) -> dict[str, Any]:
    """Answer a question using RAG (Retrieval-Augmented Generation).

    Pipeline:
        1.  Resolve the user's active LLM config.
        2.  Embed the question via ``llm_service.get_embedding``.
        3.  Search for similar document chunks (vector search, per-user scoped).
        4.  Search the user's notes by keyword.
        5.  Enrich chunks with document titles.
        6.  Build the prompt (system + context + question).
        7.  Call ``llm_service.get_completion`` for the answer.
        8.  Collect source references.
        9.  Save Q&A history.

    Args:
        user: The authenticated user (per-user isolation).
        company: The user's current company (multi-tenant isolation).
        question: The question text.
        top_k: Maximum number of document chunks to retrieve.
        note_limit: Maximum number of notes to retrieve.

    Returns:
        A dict with keys:
            - ``answer``: The generated answer text.
            - ``sources``: List of source reference dicts.
            - ``context_used``: List of context chunk/note summaries.

    Raises:
        ValueError: If the question is empty or no active LLM config exists.
        LLMError: If the LLM/embedding API call fails.
    """
    if not question or not question.strip():
        raise ValueError("Cau hoi khong duoc de trong.")

    question = question.strip()

    # Step 1: Resolve LLM config (raises ValueError if none)
    llm_config = _resolve_llm_config(user, company)

    # Step 2: Embed the question
    embed_response = get_embedding(llm_config, [question])
    query_vector = _extract_embedding_vector(embed_response)

    # Step 3: Search for similar document chunks (per-user + company scoped)
    raw_chunks = search_similar(
        user_id=user.id,
        company_id=company.id,
        query_embedding=query_vector,
        top_k=top_k,
    )

    # Step 5: Enrich chunks with document titles
    context_chunks = _enrich_chunks_with_titles(raw_chunks)

    # Step 4: Search the user's notes (keyword)
    notes = _search_notes(user, company, question, limit=note_limit)

    # Step 5: Build interaction context summary (smart context enrichment)
    interaction_context = get_context_summary(user, company)

    # Step 6: Build prompt (includes interaction context as 'Recent user activity')
    messages = build_prompt(context_chunks, notes, question, interaction_context)

    # Step 7: Call LLM for completion
    response = get_completion(llm_config, messages, stream=False)
    answer = _extract_completion_text(response)

    # Step 8: Collect sources
    sources = _collect_sources(context_chunks, notes)

    # Build context_used summary for the response + history
    context_used = [
        {
            "type": "document_chunk",
            "chunk_id": c.get("chunk_id"),
            "document_title": c.get("document_title"),
            "distance": c.get("distance"),
        }
        for c in context_chunks
    ] + [
        {
            "type": "note",
            "note_id": n["id"],
            "title": n["title"],
        }
        for n in notes
    ]

    # Step 9: Save Q&A history (includes interaction context summary)
    save_qa_history(
        user,
        company,
        question,
        answer,
        sources,
        context_used,
        interaction_context=interaction_context,
    )

    logger.info(
        "answer_question: answered question for user %s (%d chunks, %d notes retrieved)",
        getattr(user, "username", user),
        len(context_chunks),
        len(notes),
    )

    return {
        "answer": answer,
        "sources": sources,
        "context_used": context_used,
        "interaction_context": interaction_context,
    }


def save_qa_history(
    user: User,
    company: Company,
    question: str,
    answer: str,
    sources: list[dict[str, Any]],
    context_used: list[dict[str, Any]] | None = None,
    interaction_context: str | None = None,
) -> QAHistory:
    """Persist a Q&A interaction to the database.

    Args:
        user: The user who asked the question.
        company: The user's current company.
        question: The original question.
        answer: The generated answer.
        sources: List of source reference dicts.
        context_used: Optional list of context summaries used in the prompt.
        interaction_context: Optional summary of the user's recent activity
            (from ``interaction_service.get_context_summary``).

    Returns:
        The created ``QAHistory`` instance.
    """
    return QAHistory.objects.create(
        user=user,
        company=company,
        question=question,
        answer=answer,
        sources=sources,
        context_used=context_used or [],
        interaction_context=interaction_context or "",
    )


def _extract_completion_text(response: Any) -> str:
    """Extract the text content from a litellm completion response.

    litellm returns an object with ``.choices[0].message.content``. This helper
    normalises object/dict response shapes.
    """
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
