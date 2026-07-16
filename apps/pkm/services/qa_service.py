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
import re
from typing import TYPE_CHECKING, Any

from django.db.models import Q

from apps.pkm.models import DocumentChunk, KnowledgeNote, QAHistory, UserLLMConfig, WikiPage
from apps.pkm.services.data_masker import mask_all
from apps.pkm.services.interaction_service import get_context_summary
from apps.pkm.services.llm_service import get_completion, get_embedding
from apps.pkm.services.vector_store import search_similar
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
    "answer_question",
    "build_prompt",
    "save_qa_history",
    "query_wiki",
    "DEFAULT_TOP_K",
    "DEFAULT_NOTE_SEARCH_LIMIT",
    "PREVIEW_LENGTH",
    "SYSTEM_MESSAGE",
    "WIKI_SYSTEM_MESSAGE",
    "MAX_WIKI_PAGES_PER_QUERY",
    "ACCOUNTING_KEYWORDS",
    "REGULATION_BOOST_DISTANCE_BONUS",
]

#: Number of similar chunks to retrieve from the vector store.
DEFAULT_TOP_K: int = 5

#: Maximum number of notes to retrieve via keyword search.
DEFAULT_NOTE_SEARCH_LIMIT: int = 5

#: Number of characters to include in a source/preview snippet.
PREVIEW_LENGTH: int = 200

#: Bonus (subtracted from distance) applied to system regulation chunks when
#: the question contains accounting/tax keywords. Lower distance == higher rank.
REGULATION_BOOST_DISTANCE_BONUS: float = 0.15

#: Vietnamese + English accounting / tax keywords that trigger regulation
#: chunk boosting. Matching is case-insensitive substring.
ACCOUNTING_KEYWORDS: tuple[str, ...] = (
    # Vietnamese
    "thuế",
    "kế toán",
    "hóa đơn",
    "hoadon",
    "chứng từ",
    "tài khoản",
    "ghi sổ",
    "khấu hao",
    "GTGT",
    "TNDN",
    "TNCN",
    "BHXH",
    "BCTC",
    "báo cáo tài chính",
    "TT58",
    "TT133",
    "TT200",
    "NĐ253",
    "NĐ254",
    "TT87",
    "TT91",
    "PIT",
    "CIT",
    "VAT",
    "định khoản",
    "công nợ",
    "lương",
    "ngân sách",
    # English fallbacks
    "tax",
    "accounting",
    "invoice",
    "depreciation",
    "ledger",
    "payroll",
)

#: System message instructing the LLM to act as a Visota accounting assistant
#: grounded in current Vietnamese regulations and the user's activity context.
#: Must contain the substrings required by VAL-RAG-003 ("trợ lý kế toán").
#:
#: The message also instructs the model to be aware of the user's **bối cảnh
#: doanh nghiệp** (company context) section that ``get_context_summary``
#: prepends to the prompt context. That section carries the company's
#: accounting regime (e.g. TT58/2026, TT133/2016), entity type, tax method
#: group, VAT/TNDN methods, and industry, so the LLM can personalise its
#: answers to the user's accounting and tax configuration.
SYSTEM_MESSAGE: str = (
    "Bạn là trợ lý kế toán ERP Visota. "
    "Trả lời dựa trên quy định pháp luật Việt Nam hiện hành "
    "và ngữ cảnh hoạt động của người dùng. "
    "Sử dụng thông tin trong phần 'NGU CANH' (context) bên dưới để trả lời câu hỏi. "
    "Nếu thông tin không có trong ngữ cảnh, hãy nói rằng bạn không tìm thấy thông tin phù hợp. "
    "Luôn trích dẫn nguồn (tên tài liệu hoặc ghi chú) khi phân tích. "
    "Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu. "
    "Phần 'HOAT DONG NGUOI DUNG GAU DAY' mô tả các hoạt động nghiệp vụ gần nhất của người dùng "
    "(module hiện tại, vai trò, các sự kiện nghiệp vụ với giá trị). "
    "Phần này cũng chứa **bối cảnh doanh nghiệp** (company context): loại hình doanh nghiệp, "
    "chế độ kế toán (ví dụ TT58/2026, TT133/2016, TT200/2014), nhóm phương pháp thuế, "
    "phương pháp GTGT/TNDN, và ngành nghề kinh doanh. "
    "Sử dụng thông tin này để cá nhân hóa câu trả lời cho phù hợp với ngữ cảnh công việc "
    "và cấu hình kế toán / thuế của doanh nghiệp người dùng. "
    "Khi trả lời câu hỏi kế toán/thuế, hãy xem xét chế độ kế toán và "
    "phương pháp nộp thuế của doanh nghiệp người dùng."
)


#: System message for wiki-grounded Q&A. When the wiki has relevant pages the
#: LLM is asked to synthesise the answer directly from those pages (the
#: persistent, compounding artifact) rather than re-running vector search.
#: The prompt instructs the model to rely on the wiki section first and to say
#: so explicitly when the wiki does not contain enough information.
WIKI_SYSTEM_MESSAGE: str = (
    "Bạn là trợ lý kế toán ERP Visota. "
    "Phần 'WIKI' bên dưới là tài liệu nội bộ do AI tổng hợp và duy trì liên tục "
    "(theo Karpathy LLM Wiki pattern). "
    "Trả lời câu hỏi dựa trên nội dung wiki này trước. "
    "Trích dẫn tên trang wiki khi giải đáp. "
    "Chỉ khi wiki không đủ thông tin mới trả lời 'wiki chưa có thông tin'. "
    "Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu."
)

#: Maximum number of wiki pages to include in a single Q&A prompt. Keeps the
#: LLM context bounded while still allowing cross-page synthesis.
MAX_WIKI_PAGES_PER_QUERY: int = 5


# ---------------------------------------------------------------------------
# Helpers (internal)
# ---------------------------------------------------------------------------


def _contains_accounting_keywords(question: str) -> bool:
    """Return True if ``question`` mentions accounting/tax regulation keywords.

    Used to decide whether to boost system regulation chunks in retrieval.
    Matching is case-insensitive substring against :data:`ACCOUNTING_KEYWORDS`.
    """
    if not question:
        return False
    lowered = question.lower()
    return any(kw.lower() in lowered for kw in ACCOUNTING_KEYWORDS)


def _boost_regulation_chunks(
    chunks: list[dict[str, Any]],
    bonus: float = REGULATION_BOOST_DISTANCE_BONUS,
) -> list[dict[str, Any]]:
    """Re-rank retrieved chunks so system regulation chunks are prioritised.

    System chunks (``is_system=True``) get their cosine ``distance`` reduced by
    ``bonus`` (lower distance == higher rank), then the list is re-sorted by
    ascending adjusted distance. The original ``distance`` value is preserved
    on each chunk under the ``original_distance`` key for transparency.

    Non-system chunks are left unchanged. This is a soft boost: a regulation
    chunk whose true distance is much worse than a user chunk's will still
    rank below it.
    """
    adjusted: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        distance = chunk.get("distance")
        original_distance = distance
        if chunk.get("is_system") and distance is not None:
            distance = max(0.0, distance - bonus)
        chunk["original_distance"] = original_distance
        sort_key = distance if distance is not None else float("inf")
        adjusted.append((sort_key, chunk))
    adjusted.sort(key=lambda pair: pair[0])
    return [chunk for _, chunk in adjusted]


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


# ---------------------------------------------------------------------------
# Wiki query (Karpathy LLM Wiki pattern, read-side)
# ---------------------------------------------------------------------------


def _extract_keywords(question: str, *, min_length: int = 2) -> list[str]:
    """Extract significant keywords from ``question``.

    Strips common punctuation so that trailing periods / commas / question
    marks do not prevent substring matching (e.g. ``"VAT?"`` -> ``"VAT"``).
    Very short tokens (below ``min_length`` characters) are dropped.
    """
    if not question:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", question)
    return [w for w in cleaned.split() if len(w) >= min_length]


def query_wiki(
    user: User,
    company: Company,
    question: str,
    *,
    limit: int = MAX_WIKI_PAGES_PER_QUERY,
) -> list[dict[str, Any]]:
    """Read the wiki index and select pages relevant to ``question``.

    This is the read-side of the LLM wiki (Karpathy pattern). It:

      1. Reads the auto-maintained **index page** (catalog of all wiki pages
         with one-line summaries) if present, so we understand what knowledge
         already exists for this tenant.
      2. Selects the most relevant non-system wiki pages by keyword matching
         the question against each page's title and content.

    The index/log pages themselves are excluded from the results (they are
    meta-pages, not knowledge pages).

    Args:
        user: The authenticated user (per-user isolation).
        company: The user's current company (multi-tenant isolation).
        question: The user's question.
        limit: Maximum number of wiki pages to return.

    Returns:
        A list of wiki page dicts with keys: ``id``, ``title``, ``content``,
        ``page_type``, ``source_type`` (always ``"wiki_page"``). Empty when no
        wiki pages exist or none are relevant.
    """
    keywords = _extract_keywords(question)
    # Exclude the auto-maintained meta-pages (index/log) from knowledge lookup.
    pages_qs = WikiPage.objects.filter(
        user=user,
        company=company,
    ).exclude(title__in=[INDEX_PAGE_TITLE, LOG_PAGE_TITLE])

    if keywords:
        query = Q()
        for kw in keywords:
            query |= Q(title__icontains=kw) | Q(content__icontains=kw)
        pages_qs = pages_qs.filter(query).distinct()
    else:
        # No usable keywords -> nothing to match.
        return []

    pages = list(pages_qs[:limit])

    return [
        {
            "id": page.id,
            "title": page.title,
            "content": page.content,
            "page_type": page.page_type,
            "source_type": "wiki_page",
        }
        for page in pages
    ]


def _build_wiki_prompt(
    wiki_pages: list[dict[str, Any]],
    question: str,
    interaction_context: str | None = None,
    *,
    mask: bool = True,
) -> list[dict[str, str]]:
    """Construct the chat message list for a wiki-grounded LLM completion.

    The wiki pages are inlined as a labelled ``WIKI`` section so the LLM
    synthesises its answer from the persistent compounding wiki rather than
    re-running vector search. Interaction context is included so the answer
    remains personalised.

    When ``mask`` is True (the default), all sensitive data (MST tax IDs, VND
    amounts, phone numbers, emails) inside the wiki content, interaction
    context and question is passed through :func:`data_masker.mask_all`
    **before** the text is sent to the LLM. Callers should pass ``mask=False``
    only when the user's ``UserLLMConfig.disable_masking`` is True (e.g. for a
    local Ollama model where data never leaves the machine).

    Args:
        wiki_pages: Relevant wiki page dicts (from :func:`query_wiki`).
        question: The user's original question.
        interaction_context: Optional summary of recent user activity.
        mask: When True, apply PII masking before constructing the prompt.

    Returns:
        A list of message dicts ready for ``llm_service.get_completion``.
    """
    parts: list[str] = []
    if interaction_context:
        masked_ctx = mask_all(interaction_context) if mask else interaction_context
        parts.append("=== HOAT DONG NGUOI DUNG GAU DAY (Recent user activity) ===")
        parts.append(masked_ctx)

    parts.append("=== WIKI (noi dung wiki da tong hop) ===")
    for i, page in enumerate(wiki_pages, start=1):
        page_title = page["title"]
        page_content = page["content"]
        if mask:
            page_title = mask_all(page_title)
            page_content = mask_all(page_content)
        parts.append(f"[Trang wiki {i}] (Tieu de: {page_title})\n{page_content}")

    context_str = "\n\n".join(parts)
    masked_question = mask_all(question) if mask else question
    user_content = (
        f"NGU CANH (Context):\n{context_str}\n\n"
        f"CAU HOI:\n{masked_question}\n\n"
        "Tra loi dua tren wiki tren. Trich dan ten trang wiki."
    )
    return [
        {"role": "system", "content": WIKI_SYSTEM_MESSAGE},
        {"role": "user", "content": user_content},
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


def _collect_wiki_sources(wiki_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect source references from consulted wiki pages.

    Each source dict has: ``wiki_page_id``, ``document_title`` (the wiki page
    title), ``page_type``, ``content_preview``, ``source_type`` = ``"wiki_page"``.
    """
    sources: list[dict[str, Any]] = []
    for page in wiki_pages:
        content = page.get("content", "") or ""
        sources.append(
            {
                "wiki_page_id": page.get("id"),
                "document_title": page.get("title", ""),
                "page_type": page.get("page_type", ""),
                "content_preview": content[:PREVIEW_LENGTH],
                "source_type": "wiki_page",
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
    *,
    mask: bool = True,
) -> list[dict[str, str]]:
    """Construct the chat message list for the LLM completion call.

    The messages list follows the OpenAI chat format:

        [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": "<context>\\n\\n<question>"},
        ]

    When ``mask`` is True (the default), the chunks, notes, interaction
    context and question are passed through :func:`data_masker.mask_all` so
    that MST tax IDs, VND amounts, phone numbers and emails are obfuscated
    **before** the text reaches an external LLM provider. Callers should pass
    ``mask=False`` only when the user's ``UserLLMConfig.disable_masking`` is
    True (e.g. for a local Ollama model).

    Args:
        context_chunks: List of retrieved chunk dicts (from search_similar +
            enriched with ``document_title``).
        notes: List of retrieved note dicts (from ``_search_notes``).
        question: The user's original question.
        interaction_context: Optional summary of the user's recent activity
            (from ``interaction_service.get_context_summary``). Prepended to
            the RAG context as a 'Recent user activity' section.
        mask: When True, apply PII masking to all user-facing text.

    Returns:
        A list of message dicts ready for ``llm_service.get_completion``.
    """
    if mask:
        context_chunks = [
            {
                **c,
                "content": mask_all(c.get("content", "")),
                "document_title": mask_all(c.get("document_title", "")),
            }
            for c in context_chunks
        ]
        notes = [
            {
                **n,
                "title": mask_all(n.get("title", "")),
                "content_preview": mask_all(n.get("content_preview", "")),
            }
            for n in notes
        ]
        if interaction_context:
            interaction_context = mask_all(interaction_context)
        question = mask_all(question)

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
    """Answer a question using the wiki-grounded Q&A pipeline (Karpathy pattern).

    The wiki is consulted **first** (persistent, compounding artifact). Only
    when the wiki has no relevant pages does the pipeline fall back to the
    existing RAG path (vector search + notes).

    Pipeline:
        1.  Resolve the user's active LLM config.
        2.  **Read the wiki**: query the index and select relevant pages.
        3a. If relevant wiki pages exist: synthesise the answer directly from
            the wiki (no vector search, no embedding call). The wiki is a
            persistent artifact so this is the cheap, fast, preferred path.
        3b. If no relevant wiki pages: fall back to the RAG pipeline
            (embed question -> vector search -> notes -> prompt).
        4.  Collect source references (wiki pages and/or chunks + notes).
        5.  Save Q&A history.
        6.  Append a ``query`` entry to the wiki Log page.
        7.  Suggest filing the answer back into the wiki when it came from the
            RAG fallback (valuable synthesized knowledge worth persisting).

    Args:
        user: The authenticated user (per-user isolation).
        company: The user's current company (multi-tenant isolation).
        question: The question text.
        top_k: Maximum number of document chunks to retrieve (RAG fallback).
        note_limit: Maximum number of notes to retrieve (RAG fallback).

    Returns:
        A dict with keys:
            - ``answer``: The generated answer text.
            - ``sources``: List of source reference dicts.
            - ``context_used``: List of context chunk/note/wiki summaries.
            - ``interaction_context``: Recent activity summary (Vietnamese).
            - ``wiki_consulted``: True if the answer was synthesised from wiki.
            - ``suggest_file_to_wiki``: True if the answer should be filed to
              the wiki (RAG-fallback answers only).

    Raises:
        ValueError: If the question is empty or no active LLM config exists.
        LLMError: If the LLM/embedding API call fails.
    """
    if not question or not question.strip():
        raise ValueError("Cau hoi khong duoc de trong.")

    question = question.strip()

    # Step 1: Resolve LLM config (raises ValueError if none)
    llm_config = _resolve_llm_config(user, company)
    # Masking is on by default; only disabled when the user opted out (e.g.
    # for local Ollama models). VAL-MASK-004.
    mask_enabled = not getattr(llm_config, "disable_masking", False)

    # Step 2: Interaction context summary (used by both paths)
    interaction_context = get_context_summary(user, company)

    # Step 3: Read the wiki FIRST (Karpathy LLM Wiki pattern).
    wiki_pages = query_wiki(user, company, question)
    wiki_consulted = bool(wiki_pages)

    context_used: list[dict[str, Any]]
    sources: list[dict[str, Any]]

    if wiki_consulted:
        # 3a. Wiki has relevant pages: synthesise from the wiki directly.
        #     No embedding/vector-search needed.
        messages = _build_wiki_prompt(wiki_pages, question, interaction_context, mask=mask_enabled)
        response = get_completion(llm_config, messages, stream=False)
        answer = _extract_completion_text(response)

        sources = _collect_wiki_sources(wiki_pages)
        context_used = [
            {
                "type": "wiki_page",
                "wiki_page_id": p.get("id"),
                "title": p.get("title"),
                "page_type": p.get("page_type"),
            }
            for p in wiki_pages
        ]
        # The wiki already persists this knowledge; no need to re-file.
        suggest_file_to_wiki = False
    else:
        # 3b. Wiki had nothing relevant: fall back to the RAG pipeline.
        embed_response = get_embedding(llm_config, [question])
        query_vector = _extract_embedding_vector(embed_response)

        raw_chunks = search_similar(
            user_id=user.id,
            company_id=company.id,
            query_embedding=query_vector,
            top_k=top_k,
            include_system=True,
        )

        has_accounting_keywords = _contains_accounting_keywords(question)
        if has_accounting_keywords and raw_chunks:
            raw_chunks = _boost_regulation_chunks(raw_chunks)

        context_chunks = _enrich_chunks_with_titles(raw_chunks)
        notes = _search_notes(user, company, question, limit=note_limit)

        messages = build_prompt(
            context_chunks, notes, question, interaction_context, mask=mask_enabled
        )
        response = get_completion(llm_config, messages, stream=False)
        answer = _extract_completion_text(response)

        sources = _collect_sources(context_chunks, notes)
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
        # RAG-fallback answers synthesize new knowledge worth persisting to the
        # wiki so future queries hit the wiki first.
        suggest_file_to_wiki = True

    # Step 5: Save Q&A history (includes interaction context summary)
    save_qa_history(
        user,
        company,
        question,
        answer,
        sources,
        context_used,
        interaction_context=interaction_context,
    )

    # Step 6: Append a query entry to the wiki Log page (best-effort).
    try:
        append_log_entry(
            user,
            company,
            operation="query",
            detail=f'Question: "{question}" (wiki_consulted={wiki_consulted})',
        )
    except Exception:  # noqa: BLE001 - log append must never break Q&A.
        logger.warning("answer_question: failed to append wiki log entry", exc_info=True)

    logger.info(
        "answer_question: answered question for user %s (wiki_consulted=%s, %d sources)",
        getattr(user, "username", user),
        wiki_consulted,
        len(sources),
    )

    return {
        "answer": answer,
        "sources": sources,
        "context_used": context_used,
        "interaction_context": interaction_context,
        "wiki_consulted": wiki_consulted,
        "suggest_file_to_wiki": suggest_file_to_wiki,
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
