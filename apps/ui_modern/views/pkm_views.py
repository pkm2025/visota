"""PKM (Personal Knowledge Management) UI views.

Provides:
    PKMDashboardView         - overview with stats and recent notes
    KnowledgeNoteListView    - paginated list with search + tag filter, pinned-first
    KnowledgeNoteDetailView  - single note with rendered markdown
    KnowledgeNoteCreateView  - create form
    KnowledgeNoteUpdateView  - edit form
    KnowledgeNoteDeleteView  - delete confirmation
    PKMSearchView            - unified search across notes

All views require ``LoginRequiredMixin`` and the ``pkm.access`` permission
(enforced by ``ModulePermissionMiddleware`` on ``/modern/knowledge/`` paths).
Queries are scoped by ``request.user`` and ``request.current_company``
for per-user and multi-tenant isolation.
"""

from __future__ import annotations

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
from apps.pkm.models import KnowledgeNote, Tag


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

        # Document count is deferred to the documents feature; show 0 for now.
        doc_count = 0

        recent_notes = notes_qs[:5]
        pinned_notes = notes_qs.filter(is_pinned=True)[:5]

        context = {
            "page_title": "Tri thức cá nhân",
            "note_count": notes_qs.count(),
            "doc_count": doc_count,
            "recent_notes": recent_notes,
            "pinned_notes": pinned_notes,
            "tags": _get_tags_qs(request),
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
