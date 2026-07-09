"""PKM (Personal Knowledge Management) UI views.

Provides:
    PKMDashboardView         - overview with stats and recent notes
    KnowledgeNoteListView    - paginated list with search + tag filter, pinned-first
    KnowledgeNoteDetailView  - single note with rendered markdown
    KnowledgeNoteCreateView  - create form
    KnowledgeNoteUpdateView  - edit form
    KnowledgeNoteDeleteView  - delete confirmation
    PKMSearchView            - unified search across notes
    DocumentListView         - list of uploaded RAG documents with status badges
    DocumentUploadView       - drag-drop upload form
    DocumentDetailView       - single document with status, chunks, reprocess
    DocumentDeleteView       - delete confirmation
    DocumentStatusBadgeView  - HTMX partial returning a status badge (polled)

All views require ``LoginRequiredMixin`` and the ``pkm.access`` permission
(enforced by ``ModulePermissionMiddleware`` on ``/modern/knowledge/`` paths).
Queries are scoped by ``request.user`` and ``request.current_company``
for per-user and multi-tenant isolation.
"""

from __future__ import annotations

from contextlib import suppress

import markdown as md_lib
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from apps.core.models import Company
from apps.pkm.models import (
    DocumentChunk,
    KnowledgeNote,
    PKMDocument,
    QAHistory,
    Tag,
    UserLLMConfig,
)
from apps.pkm.services import encryption_service, llm_service, qa_service, rag_pipeline
from apps.pkm.services.interaction_service import log_interaction


def _get_company(request: HttpRequest) -> Company:
    """Return the current company from the request, falling back to the first."""
    company = getattr(request, "current_company", None)
    if company is None:
        company = Company.objects.first()
    return company


def _get_notes_qs(request: HttpRequest):
    """Return notes scoped to the current user + company."""
    company = _get_company(request)
    return KnowledgeNote.objects.filter(user=request.user, company=company)


def _get_tags_qs(request: HttpRequest):
    """Return tags scoped to the current user + company."""
    company = _get_company(request)
    return Tag.objects.filter(user=request.user, company=company)


def _get_llm_configs_qs(request: HttpRequest):
    """Return LLM configs scoped to the current user + company."""
    company = _get_company(request)
    return UserLLMConfig.objects.filter(user=request.user, company=company)


def _get_documents_qs(request: HttpRequest):
    """Return PKM documents scoped to the current user + company."""
    company = _get_company(request)
    return PKMDocument.objects.filter(user=request.user, company=company)


def _has_active_llm_config(request: HttpRequest) -> bool:
    """Return True if the user has at least one active LLM config."""
    return _get_llm_configs_qs(request).filter(is_active=True).exists()


def _log_search(request: HttpRequest, query: str) -> None:
    """Log a search interaction (non-blocking).

    Wrapped in try/except so that interaction capture never breaks the search
    operation. The query term is stored in the interaction metadata.
    """
    company = _get_company(request)
    with suppress(Exception):
        log_interaction(
            user=request.user,
            company=company,
            interaction_type="search",
            module="pkm",
            entity_type="note",
            metadata={"query": query},
        )


def render_markdown(text: str) -> str:
    """Convert markdown text to safe HTML.

    Uses the ``markdown`` library with a sensible set of extensions.
    """
    extensions = ["extra", "codehilite", "toc"]
    return md_lib.markdown(text, extensions=extensions, output_format="html")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class PKMDashboardView(LoginRequiredMixin, View):
    """PKM dashboard showing stats and recent notes."""

    template_name = "modern/pkm/dashboard.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        notes_qs = _get_notes_qs(request)
        docs_qs = _get_documents_qs(request)

        doc_count = docs_qs.count()

        recent_notes = notes_qs[:5]
        pinned_notes = notes_qs.filter(is_pinned=True)[:5]

        context = {
            "page_title": "Tri thức cá nhân",
            "note_count": notes_qs.count(),
            "doc_count": doc_count,
            "recent_notes": recent_notes,
            "pinned_notes": pinned_notes,
            "tags": _get_tags_qs(request),
            "has_active_config": _has_active_llm_config(request),
            "llm_config_count": _get_llm_configs_qs(request).count(),
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Note List
# ---------------------------------------------------------------------------


class KnowledgeNoteListView(LoginRequiredMixin, ListView):
    """Paginated list of the user's notes with search and tag filtering.

    Pinned notes always appear before unpinned ones.
    """

    template_name = "modern/pkm/note_list.html"
    context_object_name = "notes"
    paginate_by = 10
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = _get_notes_qs(self.request).select_related("user", "company")
        # Pin first, then by most recently updated
        qs = qs.order_by("-is_pinned", "-updated_at")

        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        tag = self.request.GET.get("tag")
        if tag:
            qs = qs.filter(tags__name=tag, tags__user=self.request.user).distinct()

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ghi chú"
        ctx["search_query"] = self.request.GET.get("search", "")
        ctx["selected_tag"] = self.request.GET.get("tag", "")
        ctx["tags"] = _get_tags_qs(self.request)
        return ctx


# ---------------------------------------------------------------------------
# Note Detail
# ---------------------------------------------------------------------------


class KnowledgeNoteDetailView(LoginRequiredMixin, DetailView):
    """Display a single note with rendered markdown content."""

    template_name = "modern/pkm/note_detail.html"
    context_object_name = "note"
    login_url = "/auth/login/"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return _get_notes_qs(self.request).select_related("user", "company")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.object.title
        ctx["rendered_content"] = render_markdown(self.object.content)
        return ctx


# ---------------------------------------------------------------------------
# Note Create
# ---------------------------------------------------------------------------


class KnowledgeNoteCreateView(LoginRequiredMixin, View):
    """Create a new knowledge note via a simple form.

    Uses a plain ``View`` (not ``CreateView``) so we can handle tags
    without a Django ``ModelForm`` — tags are selected by name from the
    user's existing tag set.
    """

    template_name = "modern/pkm/note_form.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        context = {
            "page_title": "Tạo ghi chú",
            "is_new": True,
            "note": None,
            "title": "",
            "content": "",
            "role_context": "",
            "is_pinned": False,
            "selected_tag_ids": [],
            "tags": _get_tags_qs(request),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "")
        role_context = request.POST.get("role_context", "").strip()
        is_pinned = request.POST.get("is_pinned") == "on"
        tag_ids = request.POST.getlist("tags")

        if not title:
            messages.error(request, "Tiêu đề không được để trống.")
            context = {
                "page_title": "Tạo ghi chú",
                "is_new": True,
                "note": None,
                "title": title,
                "content": content,
                "role_context": role_context,
                "is_pinned": is_pinned,
                "selected_tag_ids": [int(t) for t in tag_ids if t.isdigit()],
                "tags": _get_tags_qs(request),
            }
            return render(request, self.template_name, context)

        company = _get_company(request)
        note = KnowledgeNote.objects.create(
            user=request.user,
            company=company,
            title=title,
            content=content,
            role_context=role_context,
            is_pinned=is_pinned,
        )

        # Attach tags (validated against user's own tags)
        if tag_ids:
            valid_tags = _get_tags_qs(request).filter(id__in=tag_ids)
            note.tags.set(valid_tags)

        messages.success(request, "Đã tạo ghi chú.")
        return redirect("ui_modern:pkm_note_detail", pk=note.pk)


# ---------------------------------------------------------------------------
# Note Update
# ---------------------------------------------------------------------------


class KnowledgeNoteUpdateView(LoginRequiredMixin, View):
    """Edit an existing knowledge note."""

    template_name = "modern/pkm/note_form.html"
    login_url = "/auth/login/"

    def get_note(self, request: HttpRequest, pk: int) -> KnowledgeNote:
        return get_object_or_404(_get_notes_qs(request), pk=pk)

    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        note = self.get_note(request, pk)
        context = {
            "page_title": f"Sửa: {note.title}",
            "is_new": False,
            "note": note,
            "title": note.title,
            "content": note.content,
            "role_context": note.role_context,
            "is_pinned": note.is_pinned,
            "selected_tag_ids": list(note.tags.values_list("id", flat=True)),
            "tags": _get_tags_qs(request),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        note = self.get_note(request, pk)
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "")
        role_context = request.POST.get("role_context", "").strip()
        is_pinned = request.POST.get("is_pinned") == "on"
        tag_ids = request.POST.getlist("tags")

        if not title:
            messages.error(request, "Tiêu đề không được để trống.")
            note.title = title
            note.content = content
            note.role_context = role_context
            note.is_pinned = is_pinned
            context = {
                "page_title": f"Sửa: {note.title}",
                "is_new": False,
                "note": note,
                "title": title,
                "content": content,
                "role_context": role_context,
                "is_pinned": is_pinned,
                "selected_tag_ids": [int(t) for t in tag_ids if t.isdigit()],
                "tags": _get_tags_qs(request),
            }
            return render(request, self.template_name, context)

        note.title = title
        note.content = content
        note.role_context = role_context
        note.is_pinned = is_pinned
        note.save()

        if tag_ids:
            valid_tags = _get_tags_qs(request).filter(id__in=tag_ids)
            note.tags.set(valid_tags)
        else:
            note.tags.clear()

        messages.success(request, "Đã cập nhật ghi chú.")
        return redirect("ui_modern:pkm_note_detail", pk=note.pk)


# ---------------------------------------------------------------------------
# Note Delete
# ---------------------------------------------------------------------------


class KnowledgeNoteDeleteView(LoginRequiredMixin, DeleteView):
    """Delete confirmation page for a knowledge note."""

    template_name = "modern/pkm/note_confirm_delete.html"
    context_object_name = "note"
    success_url = reverse_lazy("ui_modern:pkm_note_list")
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return _get_notes_qs(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Xóa: {self.object.title}"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Đã xóa ghi chú.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class PKMSearchView(LoginRequiredMixin, View):
    """Unified search across the user's notes."""

    template_name = "modern/pkm/note_list.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        query = request.GET.get("q", "").strip()
        notes_qs = _get_notes_qs(request)

        if query:
            notes_qs = notes_qs.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            ).order_by("-is_pinned", "-updated_at")

            # Log the search interaction (non-blocking)
            _log_search(request, query)
        else:
            notes_qs = notes_qs.none()

        context = {
            "page_title": "Tìm kiếm ghi chú",
            "notes": notes_qs,
            "search_query": query,
            "selected_tag": "",
            "tags": _get_tags_qs(request),
            "is_search_page": True,
        }
        return render(request, self.template_name, context)


# ===========================================================================
# LLM Config Views
# ===========================================================================


# Providers that support a custom API base URL (shown in the form).
_PROVIDERS_WITH_BASE_URL = {"ollama", "openrouter"}

# Provider choices for the dropdown (Vietnamese labels).
_PROVIDER_CHOICES = UserLLMConfig.Provider.choices


def _get_provider_models_map() -> dict[str, list[str]]:
    """Return a mapping of provider -> suggested models from the llm_service."""
    result: dict[str, list[str]] = {}
    for value, _label in _PROVIDER_CHOICES:
        result[value] = llm_service.get_provider_models(value)
    return result


class LLMConfigListView(LoginRequiredMixin, View):
    """List all LLM configs for the current user + company."""

    template_name = "modern/pkm/llm_config_list.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        configs = _get_llm_configs_qs(request)
        context = {
            "page_title": "Cấu hình nhà cung cấp AI",
            "configs": configs,
            "has_active_config": _has_active_llm_config(request),
        }
        return render(request, self.template_name, context)


class LLMConfigCreateView(LoginRequiredMixin, View):
    """Create a new LLM config (provider, API key, base URL, model).

    The API key is encrypted via ``encryption_service`` before saving.
    The plaintext key is never stored in the database.
    """

    template_name = "modern/pkm/llm_config_form.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        context = self._build_context(
            request,
            is_new=True,
            provider="",
            api_base="",
            default_model="",
            default_embedding_model="",
            is_active=False,
        )
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        provider = request.POST.get("provider", "").strip()
        api_key = request.POST.get("api_key", "").strip()
        api_base = request.POST.get("api_base", "").strip()
        default_model = request.POST.get("default_model", "").strip()
        default_embedding_model = request.POST.get(
            "default_embedding_model", ""
        ).strip()
        is_active = request.POST.get("is_active") == "on"

        errors = self._validate(
            provider=provider,
            api_key=api_key,
            default_model=default_model,
        )
        if errors:
            for err in errors:
                messages.error(request, err)
            context = self._build_context(
                request,
                is_new=True,
                provider=provider,
                api_base=api_base,
                default_model=default_model,
                default_embedding_model=default_embedding_model,
                is_active=is_active,
            )
            return render(request, self.template_name, context)

        company = _get_company(request)

        if _get_llm_configs_qs(request).filter(provider=provider).exists():
            messages.error(
                request,
                "Đã có cấu hình cho nhà cung cấp này."
                " Vui lòng chỉnh sửa cấu hình hiện có.",
            )
            context = self._build_context(
                request,
                is_new=True,
                provider=provider,
                api_base=api_base,
                default_model=default_model,
                default_embedding_model=default_embedding_model,
                is_active=is_active,
            )
            return render(request, self.template_name, context)

        encrypted_key = ""
        if api_key:
            encrypted_key = encryption_service.encrypt(api_key)

        config = UserLLMConfig(
            user=request.user,
            company=company,
            provider=provider,
            api_key_encrypted=encrypted_key,
            api_base=api_base,
            default_model=default_model,
            default_embedding_model=default_embedding_model,
            is_active=is_active,
        )
        config.save()

        messages.success(request, f"Đã thêm cấu hình {config.get_provider_display()}.")
        return redirect("ui_modern:pkm_llm_config_list")

    @staticmethod
    def _validate(provider: str, api_key: str, default_model: str) -> list[str]:
        """Validate form fields. Returns a list of error messages."""
        errors: list[str] = []
        if not provider:
            errors.append("Vui lòng chọn nhà cung cấp.")
        elif provider not in dict(_PROVIDER_CHOICES):
            errors.append("Nhà cung cấp không hợp lệ.")

        if provider != "ollama" and not api_key:
            errors.append("API key là bắt buộc cho nhà cung cấp này.")

        if not default_model:
            errors.append("Model mặc định là bắt buộc.")
        return errors

    @staticmethod
    def _build_context(
        request: HttpRequest,
        *,
        is_new: bool,
        provider: str,
        api_base: str,
        default_model: str,
        default_embedding_model: str,
        is_active: bool,
    ) -> dict:
        return {
            "page_title": "Thêm cấu hình AI",
            "is_new": is_new,
            "provider_choices": _PROVIDER_CHOICES,
            "provider_models_map": _get_provider_models_map(),
            "providers_with_base_url": _PROVIDERS_WITH_BASE_URL,
            "provider": provider,
            "api_base": api_base,
            "default_model": default_model,
            "default_embedding_model": default_embedding_model,
            "is_active": is_active,
            "config": None,
        }


class LLMConfigUpdateView(LoginRequiredMixin, View):
    """Edit an existing LLM config.

    The API key field is shown empty (never pre-fills the decrypted key).
    If left blank during edit, the existing key is preserved.
    """

    template_name = "modern/pkm/llm_config_form.html"
    login_url = "/auth/login/"

    def get_config(self, request: HttpRequest, pk: int) -> UserLLMConfig:
        return get_object_or_404(_get_llm_configs_qs(request), pk=pk)

    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        config = self.get_config(request, pk)
        context = self._build_context(request, config=config)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        config = self.get_config(request, pk)
        api_key = request.POST.get("api_key", "").strip()
        api_base = request.POST.get("api_base", "").strip()
        default_model = request.POST.get("default_model", "").strip()
        default_embedding_model = request.POST.get(
            "default_embedding_model", ""
        ).strip()
        is_active = request.POST.get("is_active") == "on"

        if not default_model:
            messages.error(request, "Model mặc định là bắt buộc.")
            context = self._build_context(request, config=config)
            return render(request, self.template_name, context)

        if api_key:
            config.api_key_encrypted = encryption_service.encrypt(api_key)
        config.api_base = api_base
        config.default_model = default_model
        config.default_embedding_model = default_embedding_model
        config.is_active = is_active
        config.save()

        messages.success(request, f"Đã cập nhật cấu hình {config.get_provider_display()}.")
        return redirect("ui_modern:pkm_llm_config_list")

    @staticmethod
    def _build_context(request: HttpRequest, *, config: UserLLMConfig) -> dict:
        return {
            "page_title": f"Sửa cấu hình: {config.get_provider_display()}",
            "is_new": False,
            "provider_choices": _PROVIDER_CHOICES,
            "provider_models_map": _get_provider_models_map(),
            "providers_with_base_url": _PROVIDERS_WITH_BASE_URL,
            "provider": config.provider,
            "api_base": config.api_base,
            "default_model": config.default_model,
            "default_embedding_model": config.default_embedding_model,
            "is_active": config.is_active,
            "config": config,
        }


class LLMConfigDeleteView(LoginRequiredMixin, DeleteView):
    """Delete confirmation page for an LLM config."""

    template_name = "modern/pkm/llm_config_confirm_delete.html"
    context_object_name = "config"
    success_url = reverse_lazy("ui_modern:pkm_llm_config_list")
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return _get_llm_configs_qs(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Xóa cấu hình: {self.object.get_provider_display()}"
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Đã xóa cấu hình {self.object.get_provider_display()}.",
        )
        return super().form_valid(form)


# ===========================================================================
# Document Views
# ===========================================================================


#: Allowed file extensions for upload (must match the API layer).
_ALLOWED_DOC_TYPES: set[str] = {"pdf", "docx", "txt", "md", "xlsx"}

#: Maximum file size for uploads (20 MB), matching the API layer.
_MAX_DOC_FILE_SIZE: int = 20 * 1024 * 1024

#: HTMX polling interval (milliseconds) for pending/processing documents.
_DOC_POLL_INTERVAL_MS: int = 3000


def _status_badge_class(status: str) -> str:
    """Return a Bootstrap badge CSS class for a document status."""
    mapping = {
        PKMDocument.Status.PENDING: "bg-secondary",
        PKMDocument.Status.PROCESSING: "bg-info",
        PKMDocument.Status.PROCESSED: "bg-success",
        PKMDocument.Status.FAILED: "bg-danger",
    }
    return mapping.get(status, "bg-secondary")


def _status_label(status: str) -> str:
    """Return a Vietnamese label for a document status."""
    mapping = {
        PKMDocument.Status.PENDING: "Chờ xử lý",
        PKMDocument.Status.PROCESSING: "Đang xử lý",
        PKMDocument.Status.PROCESSED: "Đã xử lý",
        PKMDocument.Status.FAILED: "Lỗi",
    }
    return mapping.get(status, status)


def _doc_file_ext(filename: str) -> str:
    """Return the lowercase extension (without dot) of a filename."""
    import os

    return os.path.splitext(filename)[1].lstrip(".").lower()


def _strip_extension(filename: str) -> str:
    """Return the filename without its extension."""
    import os

    return os.path.splitext(filename)[0]


class DocumentListView(LoginRequiredMixin, ListView):
    """Paginated list of the user's documents with status badges.

    Documents that are pending or processing are annotated for client-side
    HTMX polling so their status badge refreshes every 3 seconds.
    """

    template_name = "modern/pkm/document_list.html"
    context_object_name = "documents"
    paginate_by = 10
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = _get_documents_qs(self.request).select_related("user", "company")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tài liệu"
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["poll_interval"] = _DOC_POLL_INTERVAL_MS
        ctx["status_choices"] = [
            (PKMDocument.Status.PENDING, _status_label(PKMDocument.Status.PENDING)),
            (PKMDocument.Status.PROCESSING, _status_label(PKMDocument.Status.PROCESSING)),
            (PKMDocument.Status.PROCESSED, _status_label(PKMDocument.Status.PROCESSED)),
            (PKMDocument.Status.FAILED, _status_label(PKMDocument.Status.FAILED)),
        ]
        return ctx


class DocumentUploadView(LoginRequiredMixin, View):
    """Drag-and-drop upload form for RAG documents.

    Validates the file type and size server-side, creates the PKMDocument,
    and enqueues the async processing pipeline.
    """

    template_name = "modern/pkm/document_upload.html"
    login_url = "/auth/login/"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        context = {
            "page_title": "Tải tài liệu lên",
            "allowed_types": sorted(_ALLOWED_DOC_TYPES),
            "max_size_mb": _MAX_DOC_FILE_SIZE // (1024 * 1024),
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        uploaded = request.FILES.get("file")
        title = request.POST.get("title", "").strip()

        errors = self._validate(uploaded, title)
        if errors:
            for err in errors:
                messages.error(request, err)
            context = {
                "page_title": "Tải tài liệu lên",
                "allowed_types": sorted(_ALLOWED_DOC_TYPES),
                "max_size_mb": _MAX_DOC_FILE_SIZE // (1024 * 1024),
                "title": title,
            }
            return render(request, self.template_name, context)

        assert uploaded is not None  # validated above
        file_type = _doc_file_ext(uploaded.name)
        doc_title = title or _strip_extension(uploaded.name)

        company = _get_company(request)
        document = PKMDocument.objects.create(
            user=request.user,
            company=company,
            title=doc_title,
            file=uploaded,
            file_type=file_type,
            file_size=uploaded.size,
            status=PKMDocument.Status.PENDING,
        )

        # Enqueue async processing (never block upload on queue issues)
        with suppress(Exception):
            rag_pipeline.schedule_document_processing(document.id)

        messages.success(request, f"Đã tải lên '{document.title}'. Đang xử lý...")
        return redirect("ui_modern:pkm_document_detail", pk=document.pk)

    @staticmethod
    def _validate(uploaded, title: str) -> list[str]:
        """Validate the upload. Returns a list of error messages."""
        errors: list[str] = []
        if uploaded is None:
            errors.append("Vui lòng chọn một tệp để tải lên.")
            return errors

        ext = _doc_file_ext(uploaded.name)
        if ext not in _ALLOWED_DOC_TYPES:
            errors.append(
                f"Loại tệp '.{ext}' không được hỗ trợ. "
                f"Chấp nhận: {', '.join(sorted(_ALLOWED_DOC_TYPES))}."
            )

        if uploaded.size > _MAX_DOC_FILE_SIZE:
            max_mb = _MAX_DOC_FILE_SIZE // (1024 * 1024)
            errors.append(f"Tệp vượt quá giới hạn {max_mb}MB.")

        if title and len(title) > 255:
            errors.append("Tiêu đề không được dài quá 255 ký tự.")
        return errors


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Display a single document with status, chunk count, and actions.

    For failed documents, shows the error message and a reprocess button.
    """

    template_name = "modern/pkm/document_detail.html"
    context_object_name = "document"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return _get_documents_qs(self.request).select_related("user", "company")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc: PKMDocument = self.object
        ctx["page_title"] = doc.title
        ctx["chunks_count"] = DocumentChunk.objects.filter(document=doc).count()
        ctx["status_badge_class"] = _status_badge_class(doc.status)
        ctx["status_label"] = _status_label(doc.status)
        ctx["poll_interval"] = _DOC_POLL_INTERVAL_MS
        ctx["is_polling"] = doc.status in (
            PKMDocument.Status.PENDING,
            PKMDocument.Status.PROCESSING,
        )
        return ctx


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete confirmation page for a document.

    On POST, removes the file, chunks, embeddings, and the document record.
    """

    template_name = "modern/pkm/document_confirm_delete.html"
    context_object_name = "document"
    success_url = reverse_lazy("ui_modern:pkm_document_list")
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return _get_documents_qs(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Xóa: {self.object.title}"
        return ctx

    def form_valid(self, form):
        doc = self.object
        # Remove chunks + embeddings via the pipeline helper (raw SQL)
        with suppress(Exception):
            rag_pipeline.delete_document_data(doc.id)
        messages.success(self.request, f"Đã xóa tài liệu '{doc.title}'.")
        return super().form_valid(form)


class DocumentStatusBadgeView(LoginRequiredMixin, View):
    """HTMX partial returning a status badge for a single document.

    Polled by the client every ``_DOC_POLL_INTERVAL_MS`` while the document
    is pending or processing. When the status becomes terminal (processed /
    failed), the response triggers an ``HX-Trigger`` event so the client can
    stop polling and refresh actions.
    """

    login_url = "/auth/login/"

    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        doc = get_object_or_404(_get_documents_qs(request), pk=pk)
        is_polling = doc.status in (
            PKMDocument.Status.PENDING,
            PKMDocument.Status.PROCESSING,
        )
        context = {
            "document": doc,
            "status_badge_class": _status_badge_class(doc.status),
            "status_label": _status_label(doc.status),
            "poll_interval": _DOC_POLL_INTERVAL_MS,
            "is_polling": is_polling,
        }
        response = render(request, "modern/pkm/_document_status_badge.html", context)
        if not is_polling:
            response.headers["HX-Trigger"] = "status-updated"
        return response


class DocumentReprocessView(LoginRequiredMixin, View):
    """Re-queue a failed (or any) document for processing via POST."""

    login_url = "/auth/login/"

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        doc = get_object_or_404(_get_documents_qs(request), pk=pk)
        doc.status = PKMDocument.Status.PENDING
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "updated_at"])
        with suppress(Exception):
            rag_pipeline.schedule_reprocessing(doc.id)
        messages.success(request, f"Đã đưa '{doc.title}' vào hàng đợi xử lý lại.")
        return redirect("ui_modern:pkm_document_detail", pk=doc.pk)


# ===========================================================================
# Q&A Chat View
# ===========================================================================


def _get_qa_history_qs(request: HttpRequest):
    """Return Q&A history scoped to the current user + company."""
    company = _get_company(request)
    return QAHistory.objects.filter(user=request.user, company=company)


class QAChatView(LoginRequiredMixin, View):
    """Q&A chat interface with message history and a question input.

    On GET:
        - Renders the chat page with recent Q&A history (sidebar/panel).
        - If the user has no active LLM config, displays a "configure provider
          first" prompt and disables the input.

    On POST:
        - Validates the question (non-empty).
        - Calls ``qa_service.answer_question`` (LLM mocked in tests) via the
          API service layer.
        - Renders the answer with source citations.
        - If the user has no active config, shows the configure-first prompt.

    The page also exposes a JSON endpoint for HTMX/fetch submissions via the
    API at ``/api/v1/pkm/qa/ask/``. The server-side POST handler here renders
    the answer HTML fragment for progressive enhancement (no-JS fallback).
    """

    template_name = "modern/pkm/qa_chat.html"
    login_url = "/auth/login/"

    #: Number of recent Q&A entries shown in the history panel.
    _HISTORY_LIMIT: int = 20

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        context = self._build_context(request)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        question = request.POST.get("question", "").strip()

        # Validate: empty question is an error
        if not question:
            messages.error(request, "Câu hỏi không được để trống.")
            context = self._build_context(request, question=question)
            return render(request, self.template_name, context)

        # Check for active LLM config before calling the service
        if not _has_active_llm_config(request):
            messages.error(
                request,
                "Chưa có cấu hình AI hoạt động. Vui lòng cấu hình nhà cung cấp trước.",
            )
            context = self._build_context(request, question=question)
            return render(request, self.template_name, context)

        # Delegate to the service (LLM calls are mocked in tests)
        company = _get_company(request)
        try:
            result = qa_service.answer_question(
                user=request.user,
                company=company,
                question=question,
            )
        except ValueError:
            messages.error(
                request,
                "Chưa có cấu hình AI hoạt động. Vui lòng cấu hình nhà cung cấp trước.",
            )
            context = self._build_context(request, question=question)
            return render(request, self.template_name, context)
        except Exception:
            messages.error(
                request,
                "Có lỗi xảy ra khi xử lý câu hỏi. Vui lòng thử lại.",
            )
            context = self._build_context(request, question=question)
            return render(request, self.template_name, context)

        # Refresh history (the new Q&A is now saved by the service)
        context = self._build_context(
            request,
            question=question,
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
        )
        return render(request, self.template_name, context)

    def _build_context(
        self,
        request: HttpRequest,
        *,
        question: str = "",
        answer: str = "",
        sources: list | None = None,
    ) -> dict:
        """Build the template context for the Q&A chat page."""
        return {
            "page_title": "Hỏi đáp AI",
            "has_active_config": _has_active_llm_config(request),
            "history": _get_qa_history_qs(request)[: self._HISTORY_LIMIT],
            "question": question,
            "answer": answer,
            "sources": sources or [],
            "config_url": "ui_modern:pkm_llm_config_list",
        }
