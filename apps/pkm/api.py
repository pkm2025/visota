"""django-ninja Router for PKM (Personal Knowledge Management) API.

Provides CRUD endpoints for knowledge notes, LLM configs, and documents,
scoped by ``request.user`` and ``request.current_company`` for per-user and
multi-tenant isolation.

Endpoints:
    POST   /api/v1/pkm/notes/            # Create note
    GET    /api/v1/pkm/notes/            # List notes (paginated, searchable, tag-filterable)
    GET    /api/v1/pkm/notes/{id}/       # Note detail
    PUT    /api/v1/pkm/notes/{id}/       # Update note
    DELETE /api/v1/pkm/notes/{id}/       # Delete note

    GET    /api/v1/pkm/llm-configs/           # List user's LLM configs
    POST   /api/v1/pkm/llm-configs/           # Create config (api_key encrypted before save)
    PUT    /api/v1/pkm/llm-configs/{id}/      # Update config
    DELETE /api/v1/pkm/llm-configs/{id}/      # Delete config
    POST   /api/v1/pkm/llm-configs/validate/  # Validate API key without saving
    GET    /api/v1/pkm/providers/             # List available providers

    POST   /api/v1/pkm/documents/             # Upload document (multipart)
    GET    /api/v1/pkm/documents/             # List documents
    GET    /api/v1/pkm/documents/{id}/        # Document detail
    DELETE /api/v1/pkm/documents/{id}/        # Delete document (file + chunks + embeddings)
    POST   /api/v1/pkm/documents/{id}/reprocess/  # Re-queue RAG pipeline
    GET    /api/v1/pkm/documents/{id}/status/     # Processing status

    POST   /api/v1/pkm/qa/ask/               # RAG Q&A (returns answer + sources)
    GET    /api/v1/pkm/qa/history/           # Q&A history (paginated)

    GET    /api/v1/pkm/stats/                # Aggregate PKM statistics

All endpoints require ``auth=get_current_user`` (session or API key).
"""

from __future__ import annotations

import hashlib
import os
from contextlib import suppress
from datetime import datetime
from typing import Any

from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpRequest
from ninja import Field, Form, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import paginate

from apps.core.api import get_current_company, get_current_user
from apps.pkm.models import (
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    Tag,
    UserLLMConfig,
)
from apps.pkm.services import encryption_service, llm_service, qa_service, rag_pipeline
from apps.pkm.services.interaction_service import log_interaction
from apps.pkm.services.llm_service import (
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)

router = Router(tags=["PKM"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TagSchema(Schema):
    """Read-only tag representation."""

    id: int
    name: str
    color: str = ""


class NoteCreateSchema(Schema):
    """Request body for creating a note."""

    title: str = Field(..., min_length=1, max_length=255, description="Note title (required)")
    content: str = Field("", description="Markdown content")
    role_context: str = Field("", description="Optional role tag for context filtering")
    is_pinned: bool = False
    tag_ids: list[int] = Field(default_factory=list, description="IDs of tags to attach")


class NoteUpdateSchema(Schema):
    """Request body for updating a note (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    role_context: str | None = None
    is_pinned: bool | None = None
    tag_ids: list[int] | None = None


class NoteSchema(Schema):
    """Full note response."""

    id: int
    title: str
    content: str
    role_context: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    tags: list[TagSchema] = []


class MessageSchema(Schema):
    """Generic message response."""

    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_scoped_queryset(request: HttpRequest, *, pk: int | None = None) -> Any:
    """Return notes scoped to the current user + company.

    If ``pk`` is provided, raises 404 if the note does not belong to the user.
    """
    company = get_current_company(request)
    qs = KnowledgeNote.objects.filter(user=request.user, company=company)
    if pk is not None:
        note = qs.filter(pk=pk).first()
        if note is None:
            raise HttpError(404, "Note not found")
        return note
    return qs


def _serialize_note(note: KnowledgeNote) -> dict[str, Any]:
    """Build a plain dict from a KnowledgeNote for NoteSchema serialization."""
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "role_context": note.role_context,
        "is_pinned": note.is_pinned,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in note.tags.all()],
    }


def _validate_tag_ids(request: HttpRequest, tag_ids: list[int]) -> list[Tag]:
    """Resolve tag IDs to Tag objects, scoped to current user + company.

    Raises 400 if any tag ID does not belong to the user.
    """
    company = get_current_company(request)
    valid_tags = list(Tag.objects.filter(id__in=tag_ids, user=request.user, company=company))
    found_ids = {t.id for t in valid_tags}
    invalid = set(tag_ids) - found_ids
    if invalid:
        raise HttpError(400, f"Invalid tag IDs: {sorted(invalid)}")
    return valid_tags


def _log_search_interaction(request: HttpRequest, query: str) -> None:
    """Log a search interaction with the query in metadata (non-blocking).

    Wrapped in try/except so that interaction capture never breaks the search.
    """
    with suppress(Exception):
        log_interaction(
            user=request.user,
            company=get_current_company(request),
            interaction_type="search",
            module="pkm",
            entity_type="note",
            metadata={"query": query},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/notes/", response=NoteSchema, auth=get_current_user)
def create_note(request: HttpRequest, payload: NoteCreateSchema) -> dict[str, Any]:
    """Create a new knowledge note for the authenticated user."""
    company = get_current_company(request)
    note = KnowledgeNote.objects.create(
        user=request.user,
        company=company,
        title=payload.title,
        content=payload.content,
        role_context=payload.role_context,
        is_pinned=payload.is_pinned,
    )
    if payload.tag_ids:
        tags = _validate_tag_ids(request, payload.tag_ids)
        note.tags.set(tags)
    return _serialize_note(note)


@router.get("/notes/", response=list[NoteSchema], auth=get_current_user)
@paginate
def list_notes(
    request: HttpRequest,
    search: str | None = None,
    tag: str | None = None,
) -> Any:
    """List notes for the authenticated user.

    Query params:
        search: Keyword to filter by title or content (case-insensitive).
        tag:    Tag name to filter by (must match user's tag).
    """
    qs = _get_scoped_queryset(request)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))
        _log_search_interaction(request, search)
    if tag:
        qs = qs.filter(tags__name=tag, tags__user=request.user)
    return qs.distinct()


class NoteSearchSchema(Schema):
    """Request body for the notes search endpoint."""

    query: str = Field(..., min_length=1, description="Search keyword")


@router.post("/notes/search/", response=list[NoteSchema], auth=get_current_user)
def search_notes(request: HttpRequest, payload: NoteSearchSchema) -> list[dict[str, Any]]:
    """Search notes by keyword in title or content (case-insensitive).

    Logs a ``search`` interaction with the query term in metadata.
    """
    qs = _get_scoped_queryset(request).filter(
        Q(title__icontains=payload.query) | Q(content__icontains=payload.query)
    )
    _log_search_interaction(request, payload.query)
    return [_serialize_note(n) for n in qs]


@router.get("/notes/{note_id}/", response=NoteSchema, auth=get_current_user)
def get_note(request: HttpRequest, note_id: int) -> dict[str, Any]:
    """Retrieve a single note by ID."""
    note = _get_scoped_queryset(request, pk=note_id)
    return _serialize_note(note)


@router.put("/notes/{note_id}/", response=NoteSchema, auth=get_current_user)
def update_note(request: HttpRequest, note_id: int, payload: NoteUpdateSchema) -> dict[str, Any]:
    """Update an existing note. Only provided fields are changed."""
    note = _get_scoped_queryset(request, pk=note_id)

    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)

    for field, value in data.items():
        setattr(note, field, value)
    note.save()

    if tag_ids is not None:
        tags = _validate_tag_ids(request, tag_ids)
        note.tags.set(tags)

    note.refresh_from_db()
    return _serialize_note(note)


@router.delete("/notes/{note_id}/", response=MessageSchema, auth=get_current_user)
def delete_note(request: HttpRequest, note_id: int) -> MessageSchema:
    """Delete a note by ID."""
    note = _get_scoped_queryset(request, pk=note_id)
    note.delete()
    return MessageSchema(message="Note deleted")


# ===========================================================================
# LLM Config CRUD
# ===========================================================================


class LLMConfigCreateSchema(Schema):
    """Request body for creating an LLM config."""

    provider: UserLLMConfig.Provider
    api_key: str = Field("", description="Plaintext API key (encrypted before save)")
    api_base: str = Field("", description="Custom API base URL (optional)")
    default_model: str = Field(..., min_length=1, max_length=100)
    default_embedding_model: str = Field("", max_length=100)
    is_active: bool = False


class LLMConfigUpdateSchema(Schema):
    """Request body for updating an LLM config (all fields optional)."""

    api_key: str | None = Field(None, description="New plaintext API key (encrypted before save)")
    api_base: str | None = None
    default_model: str | None = Field(None, min_length=1, max_length=100)
    default_embedding_model: str | None = None
    is_active: bool | None = None


class LLMConfigSchema(Schema):
    """LLM config response.

    NEVER exposes ``api_key_encrypted`` or the plaintext key.
    Only includes ``has_key`` boolean indicating whether a key is stored.
    """

    id: int
    provider: str
    api_base: str = ""
    default_model: str
    default_embedding_model: str = ""
    is_active: bool
    has_key: bool
    created_at: datetime
    updated_at: datetime


class ValidateSchema(Schema):
    """Request body for the validate endpoint."""

    provider: UserLLMConfig.Provider
    api_key: str = Field("", description="Plaintext API key to validate")
    api_base: str = Field("", description="Custom API base URL (optional)")


class ValidateResponseSchema(Schema):
    """Response for the validate endpoint."""

    valid: bool
    message: str = ""


class ProviderSchema(Schema):
    """Provider info for the providers list."""

    value: str
    label: str
    models: list[str]


class ProvidersResponseSchema(Schema):
    """Response for the providers list endpoint."""

    providers: list[ProviderSchema]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_scoped_config(request: HttpRequest, config_id: int) -> UserLLMConfig:
    """Return a config scoped to the current user + company, or 404."""
    company = get_current_company(request)
    config = UserLLMConfig.objects.filter(id=config_id, user=request.user, company=company).first()
    if config is None:
        raise HttpError(404, "LLM config not found")
    return config


def _serialize_config(config: UserLLMConfig) -> dict[str, Any]:
    """Build a plain dict from a UserLLMConfig for LLMConfigSchema serialization.

    Never includes the encrypted or plaintext API key.
    """
    return {
        "id": config.id,
        "provider": config.provider,
        "api_base": config.api_base or "",
        "default_model": config.default_model,
        "default_embedding_model": config.default_embedding_model or "",
        "is_active": config.is_active,
        "has_key": bool(config.api_key_encrypted),
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


# ---------------------------------------------------------------------------
# LLM Config endpoints
# ---------------------------------------------------------------------------


@router.get("/llm-configs/", response=list[LLMConfigSchema], auth=get_current_user)
def list_llm_configs(request: HttpRequest) -> list[dict[str, Any]]:
    """List the authenticated user's LLM configs, scoped by company."""
    company = get_current_company(request)
    qs = UserLLMConfig.objects.filter(user=request.user, company=company)
    return [_serialize_config(c) for c in qs]


@router.post("/llm-configs/", response=LLMConfigSchema, auth=get_current_user)
def create_llm_config(request: HttpRequest, payload: LLMConfigCreateSchema) -> dict[str, Any]:
    """Create a new LLM config. The API key is encrypted before saving."""
    company = get_current_company(request)

    # Encrypt the API key if provided (Ollama may not need one)
    encrypted_key = ""
    if payload.api_key:
        encrypted_key = encryption_service.encrypt(payload.api_key)

    config = UserLLMConfig(
        user=request.user,
        company=company,
        provider=payload.provider,
        api_key_encrypted=encrypted_key,
        api_base=payload.api_base,
        default_model=payload.default_model,
        default_embedding_model=payload.default_embedding_model,
        is_active=payload.is_active,
    )
    try:
        config.save()
    except IntegrityError:
        raise HttpError(
            400, f"A config for provider '{payload.provider}' already exists."
        ) from None

    return _serialize_config(config)


@router.post("/llm-configs/validate/", response=ValidateResponseSchema, auth=get_current_user)
def validate_llm_key(request: HttpRequest, payload: ValidateSchema) -> ValidateResponseSchema:
    """Validate an API key without saving it.

    Calls ``llm_service.validate_api_key`` which makes a minimal test call
    to the provider. The key is never stored.
    """
    # Ollama doesn't need an API key; consider it valid if a base URL is provided
    if payload.provider == "ollama":
        return ValidateResponseSchema(valid=True, message="Ollama does not require an API key.")

    # Non-ollama providers require an API key for validation
    if not payload.api_key:
        raise HttpError(422, "API key is required for this provider.")

    valid = llm_service.validate_api_key(
        provider=payload.provider,
        api_key=payload.api_key,
        api_base=payload.api_base or None,
    )
    message = "API key is valid." if valid else "API key validation failed."
    return ValidateResponseSchema(valid=valid, message=message)


@router.put("/llm-configs/{config_id}/", response=LLMConfigSchema, auth=get_current_user)
def update_llm_config(
    request: HttpRequest, config_id: int, payload: LLMConfigUpdateSchema
) -> dict[str, Any]:
    """Update an existing LLM config. Only provided fields are changed."""
    config = _get_scoped_config(request, config_id)

    data = payload.model_dump(exclude_unset=True)

    # Handle API key re-encryption if a new key is provided
    new_api_key = data.pop("api_key", None)
    if new_api_key is not None:
        config.api_key_encrypted = encryption_service.encrypt(new_api_key)

    for field, value in data.items():
        setattr(config, field, value)

    config.save()
    config.refresh_from_db()
    return _serialize_config(config)


@router.delete("/llm-configs/{config_id}/", response=MessageSchema, auth=get_current_user)
def delete_llm_config(request: HttpRequest, config_id: int) -> MessageSchema:
    """Delete an LLM config by ID."""
    config = _get_scoped_config(request, config_id)
    config.delete()
    return MessageSchema(message="LLM config deleted")


@router.get("/providers/", response=ProvidersResponseSchema, auth=get_current_user)
def list_providers(request: HttpRequest) -> dict[str, Any]:
    """List all supported LLM providers with suggested models."""
    providers = []
    for value, label in UserLLMConfig.Provider.choices:
        models = llm_service.get_provider_models(value)
        providers.append({"value": value, "label": label, "models": models})
    return {"providers": providers}


# ===========================================================================
# Document Management CRUD
# ===========================================================================

#: Maximum file size for uploads: 20 MB.
MAX_FILE_SIZE: int = 20 * 1024 * 1024

#: Allowed file extensions (lowercase, no dot).
ALLOWED_FILE_TYPES: set[str] = {"pdf", "docx", "txt", "md", "xlsx"}


class DocumentSchema(Schema):
    """Document response schema."""

    id: int
    title: str
    file_type: str
    file_size: int
    status: str
    checksum: str = ""
    error_message: str = ""
    created_at: datetime
    updated_at: datetime


class DocumentDetailSchema(DocumentSchema):
    """Document detail schema with additional fields."""

    file_url: str = ""
    has_file: bool = True


class DocumentStatusSchema(Schema):
    """Lightweight status response."""

    id: int
    status: str
    error_message: str = ""


class DocumentCreatedSchema(DocumentSchema):
    """Schema returned after upload (includes duplicate warning)."""

    is_duplicate: bool = False
    duplicate_message: str = ""


class DocumentDeleteSchema(Schema):
    """Delete response."""

    message: str
    id: int


class ReprocessSchema(Schema):
    """Reprocess response."""

    message: str
    id: int
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_scoped_document(request: HttpRequest, doc_id: int) -> PKMDocument:
    """Return a document scoped to the current user + company, or 404."""
    company = get_current_company(request)
    doc = PKMDocument.objects.filter(id=doc_id, user=request.user, company=company).first()
    if doc is None:
        raise HttpError(404, "Document not found")
    return doc


def _validate_file_type(filename: str) -> str:
    """Validate the file extension and return the normalised type.

    Raises 400 if the extension is not in ``ALLOWED_FILE_TYPES``.
    """
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise HttpError(
            400,
            f"File type '.{ext}' is not allowed. "
            f"Supported types: {', '.join(sorted(ALLOWED_FILE_TYPES))}.",
        )
    return ext


def _validate_file_size(file: UploadedFile) -> int:
    """Validate file size and return the size in bytes.

    Raises 400 if the file exceeds ``MAX_FILE_SIZE``.
    """
    file.seek(0, 2)  # seek to end
    size: int = file.tell()
    file.seek(0)  # reset
    if size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise HttpError(
            400,
            f"File size {size} bytes exceeds the {max_mb}MB limit.",
        )
    return size


def _compute_checksum(file: UploadedFile) -> str:
    """Compute SHA-256 checksum of the uploaded file.

    Reads the file in chunks to avoid loading the entire file into memory.
    """
    sha256 = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(8192), b""):
        sha256.update(chunk)
    file.seek(0)
    return sha256.hexdigest()


def _serialize_document(doc: PKMDocument) -> dict[str, Any]:
    """Build a plain dict from a PKMDocument for schema serialization."""
    return {
        "id": doc.id,
        "title": doc.title,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "checksum": doc.checksum,
        "error_message": doc.error_message,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


# ---------------------------------------------------------------------------
# Document endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/documents/",
    response={201: DocumentCreatedSchema},
    auth=get_current_user,
)
def upload_document(
    request: HttpRequest,
    file: UploadedFile,
    title: str = Form(""),
) -> dict[str, Any]:
    """Upload a document for RAG processing.

    Accepts a multipart file upload. Validates the file type (pdf, docx, txt,
    md, xlsx) and size (max 20MB). Computes a SHA-256 checksum for dedup
    detection. Creates a ``PKMDocument`` record (status=pending) and enqueues
    an async task for RAG processing.

    A duplicate warning is returned (200) if a document with the same checksum
    already exists for the user, but the upload still succeeds (201).
    """
    # Validate file type
    filename = file.name or "unknown"
    file_type = _validate_file_type(filename)

    # Validate file size
    file_size = _validate_file_size(file)

    # Compute checksum
    checksum = _compute_checksum(file)

    # Check for duplicate (same checksum for this user)
    company = get_current_company(request)
    existing_dup = PKMDocument.objects.filter(
        user=request.user,
        company=company,
        checksum=checksum,
    ).first()

    is_duplicate = existing_dup is not None

    # Use provided title or derive from filename
    doc_title = title.strip() if title.strip() else os.path.splitext(filename)[0]

    # Create the document record
    document = PKMDocument.objects.create(
        user=request.user,
        company=company,
        title=doc_title,
        file=file,
        file_type=file_type,
        file_size=file_size,
        checksum=checksum,
        status=PKMDocument.Status.PENDING,
    )

    # Enqueue async processing task
    rag_pipeline.schedule_document_processing(document.id)

    # Build response
    result = _serialize_document(document)
    result["is_duplicate"] = is_duplicate
    if is_duplicate and existing_dup is not None:
        result["duplicate_message"] = (
            f"A document with the same content (checksum) already exists: "
            f"'{existing_dup.title}' (ID: {existing_dup.id})."
        )
    return result


@router.get("/documents/", response=list[DocumentSchema], auth=get_current_user)
@paginate
def list_documents(
    request: HttpRequest,
    status: str | None = None,
) -> Any:
    """List the authenticated user's documents, scoped by company.

    Query params:
        status: Filter by processing status (pending, processing, processed, failed).
    """
    company = get_current_company(request)
    qs = PKMDocument.objects.filter(user=request.user, company=company)
    if status:
        qs = qs.filter(status=status)
    return qs


@router.get("/documents/{doc_id}/", response=DocumentDetailSchema, auth=get_current_user)
def get_document(request: HttpRequest, doc_id: int) -> dict[str, Any]:
    """Retrieve a single document by ID."""
    doc = _get_scoped_document(request, doc_id)
    result = _serialize_document(doc)
    result["file_url"] = doc.file.url if doc.file else ""
    result["has_file"] = bool(doc.file)
    return result


@router.delete("/documents/{doc_id}/", response=DocumentDeleteSchema, auth=get_current_user)
def delete_document(request: HttpRequest, doc_id: int) -> dict[str, Any]:
    """Delete a document and all related data (file, chunks, embeddings).

    Cascade order:
        1. Delete chunks + embeddings via ``delete_document_data`` (raw SQL)
        2. Delete the physical file from storage
        3. Delete the ``PKMDocument`` record from the database
    """
    doc = _get_scoped_document(request, doc_id)

    # Delete chunks and embeddings (raw SQL for VECTOR table)
    rag_pipeline.delete_document_data(doc.id)

    # Delete the physical file
    if doc.file:
        with suppress(Exception):
            doc.file.delete(save=False)

    # Delete the document record
    doc.delete()

    return {"message": "Document deleted", "id": doc_id}


@router.post(
    "/documents/{doc_id}/reprocess/",
    response=ReprocessSchema,
    auth=get_current_user,
)
def reprocess_document(request: HttpRequest, doc_id: int) -> dict[str, Any]:
    """Re-queue a document for RAG pipeline processing.

    Resets the document status to ``pending`` and enqueues a new async task.
    The pipeline will delete old chunks/embeddings and re-process from scratch.
    """
    doc = _get_scoped_document(request, doc_id)

    # Reset status and error
    doc.status = PKMDocument.Status.PENDING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "updated_at"])

    # Enqueue reprocessing (reprocess_document clears old data + re-runs)
    rag_pipeline.schedule_reprocessing(doc.id)

    return {
        "message": "Document re-queued for processing",
        "id": doc_id,
        "status": doc.status,
    }


@router.get(
    "/documents/{doc_id}/status/",
    response=DocumentStatusSchema,
    auth=get_current_user,
)
def get_document_status(request: HttpRequest, doc_id: int) -> dict[str, Any]:
    """Return the current processing status of a document."""
    doc = _get_scoped_document(request, doc_id)
    return {
        "id": doc.id,
        "status": doc.status,
        "error_message": doc.error_message,
    }


# ===========================================================================
# Q&A (RAG-powered Question Answering)
# ===========================================================================


class AskQuestionSchema(Schema):
    """Request body for the Q&A ask endpoint."""

    question: str = Field(..., min_length=1, description="The question to ask")


class SourceSchema(Schema):
    """A source reference cited in the Q&A answer."""

    chunk_id: int | None = None
    embedding_id: int | None = None
    note_id: int | None = None
    document_title: str = ""
    content_preview: str = ""
    distance: float | None = None
    source_type: str


class ContextUsedSchema(Schema):
    """A context item used to build the Q&A prompt."""

    type: str
    chunk_id: int | None = None
    note_id: int | None = None
    document_title: str | None = None
    title: str | None = None
    distance: float | None = None


class AskResponseSchema(Schema):
    """Response for the Q&A ask endpoint."""

    answer: str
    sources: list[SourceSchema] = []
    context_used: list[ContextUsedSchema] = []
    interaction_context: str = ""
    context_used_indicator: bool = False


class QAHistorySchema(Schema):
    """A Q&A history record."""

    id: int
    question: str
    answer: str
    sources: list[dict[str, Any]] = []
    context_used: list[dict[str, Any]] = []
    interaction_context: str = ""
    created_at: datetime


# ---------------------------------------------------------------------------
# Q&A endpoints
# ---------------------------------------------------------------------------


@router.post("/qa/ask/", response=AskResponseSchema, auth=get_current_user)
def ask_question(request: HttpRequest, payload: AskQuestionSchema) -> dict[str, Any]:
    """Answer a question using RAG (Retrieval-Augmented Generation).

    Accepts a question, embeds it, searches for relevant document chunks and
    notes, builds a context prompt, and calls the LLM for an answer.

    Requires an active LLM configuration. If the user has no active config,
    returns 400 with a message directing them to configure a provider first.

    Returns:
        The generated answer, source references, and context used.
    """
    company = get_current_company(request)

    # Check for active LLM config before delegating to the service.
    # This provides a clear 400 (not a 500) when the user hasn't configured
    # a provider yet.
    active_config = UserLLMConfig.objects.filter(
        user=request.user,
        company=company,
        is_active=True,
    ).exists()
    if not active_config:
        raise HttpError(
            400,
            "Chua co cau hinh LLM nao hoat dong. "
            "Vui long cau hinh provider (OpenAI, Anthropic, v.v.) truoc khi "
            "su dung Q&A. Truy cap /api/v1/pkm/llm-configs/ de cau hinh.",
        )

    # Delegate to the service (LLM calls are mocked in tests)
    try:
        result = qa_service.answer_question(
            user=request.user,
            company=company,
            question=payload.question,
        )
    except ValueError as exc:
        # The service raises ValueError for empty/whitespace questions.
        # Return a clean 400 instead of letting it bubble up as a 500.
        raise HttpError(400, str(exc)) from exc
    except LLMAuthError as exc:
        # Invalid API key -> 401-like response
        raise HttpError(401, f"LLM authentication failed: {exc}") from exc
    except LLMRateLimitError as exc:
        # Provider rate-limited the request -> 429
        raise HttpError(429, f"LLM rate limit exceeded: {exc}") from exc
    except LLMTimeoutError as exc:
        # Timeout or connection error -> 504 Gateway Timeout
        raise HttpError(504, f"LLM request timed out: {exc}") from exc
    except LLMError as exc:
        # Catch-all for unexpected LLM failures (e.g. bad request, internal
        # server error from the provider) -> 502 Bad Gateway
        raise HttpError(502, f"LLM provider error: {exc}") from exc

    # Add 'context used' indicator: True when any context (chunks, notes,
    # or interaction summary) was included in the prompt.
    result["context_used_indicator"] = bool(
        result.get("context_used") or result.get("interaction_context")
    )
    return result


@router.get("/qa/history/", response=list[QAHistorySchema], auth=get_current_user)
@paginate
def list_qa_history(request: HttpRequest) -> Any:
    """List the authenticated user's Q&A history, scoped by company.

    Results are ordered by most recent first and paginated.
    """
    company = get_current_company(request)
    return QAHistory.objects.filter(user=request.user, company=company)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class StatsResponseSchema(Schema):
    """Aggregate PKM statistics for the authenticated user."""

    note_count: int
    doc_count: int
    doc_status_counts: dict[str, int]
    qa_count: int
    tag_count: int
    llm_config_count: int
    has_active_config: bool
    pinned_note_count: int
    role_suggestions_count: int
    user_role_codes: list[str]


@router.get("/stats/", response=StatsResponseSchema, auth=get_current_user)
def get_pkm_stats(request: HttpRequest) -> dict[str, Any]:
    """Return aggregate PKM statistics for the authenticated user.

    All counts are scoped by ``request.user`` and ``request.current_company``
    for per-user and multi-tenant isolation. Includes:

      - ``note_count``: total notes
      - ``doc_count``: total documents
      - ``doc_status_counts``: documents broken down by status
        (pending/processing/processed/failed)
      - ``qa_count``: total Q&A interactions
      - ``tag_count``: total tags
      - ``llm_config_count``: total LLM configs
      - ``has_active_config``: True if user has at least one active config
      - ``pinned_note_count``: number of pinned notes
      - ``role_suggestions_count``: number of notes whose ``role_context``
        matches one of the user's role codes
      - ``user_role_codes``: the user's role codes in the current company
    """
    company = get_current_company(request)

    notes_qs = KnowledgeNote.objects.filter(user=request.user, company=company)
    docs_qs = PKMDocument.objects.filter(user=request.user, company=company)
    qa_qs = QAHistory.objects.filter(user=request.user, company=company)
    tags_qs = Tag.objects.filter(user=request.user, company=company)
    configs_qs = UserLLMConfig.objects.filter(user=request.user, company=company)

    # User's role codes in the current company (for role-based filtering)
    from apps.identity.models import UserCompanyRole

    user_role_codes = list(
        UserCompanyRole.objects.filter(
            user=request.user,
            company=company,
        ).values_list("role__code", flat=True)
    )

    role_suggestions_qs = (
        notes_qs.filter(role_context__in=user_role_codes)
        if user_role_codes
        else notes_qs.none()
    )

    return {
        "note_count": notes_qs.count(),
        "doc_count": docs_qs.count(),
        "doc_status_counts": {
            "pending": docs_qs.filter(status=PKMDocument.Status.PENDING).count(),
            "processing": docs_qs.filter(status=PKMDocument.Status.PROCESSING).count(),
            "processed": docs_qs.filter(status=PKMDocument.Status.PROCESSED).count(),
            "failed": docs_qs.filter(status=PKMDocument.Status.FAILED).count(),
        },
        "qa_count": qa_qs.count(),
        "tag_count": tags_qs.count(),
        "llm_config_count": configs_qs.count(),
        "has_active_config": configs_qs.filter(is_active=True).exists(),
        "pinned_note_count": notes_qs.filter(is_pinned=True).count(),
        "role_suggestions_count": role_suggestions_qs.count(),
        "user_role_codes": user_role_codes,
    }
