"""django-ninja Router for PKM (Personal Knowledge Management) API.

Provides CRUD endpoints for knowledge notes and LLM configs, scoped by
``request.user`` and ``request.current_company`` for per-user and
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

All endpoints require ``auth=get_current_user`` (session or API key).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpRequest
from ninja import Field, Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate

from apps.core.api import get_current_company, get_current_user
from apps.pkm.models import KnowledgeNote, Tag, UserLLMConfig
from apps.pkm.services import encryption_service, llm_service

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
    if tag:
        qs = qs.filter(tags__name=tag, tags__user=request.user)
    return qs.distinct()


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
