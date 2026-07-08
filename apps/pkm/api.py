"""django-ninja Router for PKM (Personal Knowledge Management) API.

Provides CRUD endpoints for knowledge notes, scoped by ``request.user`` and
``request.current_company`` for per-user and multi-tenant isolation.

Endpoints:
    POST   /api/v1/pkm/notes/            # Create note
    GET    /api/v1/pkm/notes/            # List notes (paginated, searchable, tag-filterable)
    GET    /api/v1/pkm/notes/{id}/       # Note detail
    PUT    /api/v1/pkm/notes/{id}/       # Update note
    DELETE /api/v1/pkm/notes/{id}/       # Delete note

All endpoints require ``auth=get_current_user`` (session or API key).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import Q
from django.http import HttpRequest
from ninja import Field, Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate

from apps.core.api import get_current_company, get_current_user
from apps.pkm.models import KnowledgeNote, Tag

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
