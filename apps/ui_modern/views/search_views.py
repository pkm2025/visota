"""Global "super search" views: instant suggestions + click tracking."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from apps.ui_modern.search import is_valid_type, record_click, search


class GlobalSearchView(LoginRequiredMixin, View):
    """Return grouped search suggestions as an HTML partial (HTMX)."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        company = getattr(request, "current_company", None)
        groups = search(request.user, company, query) if query and company else []
        return render(
            request,
            "modern/search/_results.html",
            {"groups": groups, "query": query},
        )


class SearchClickView(LoginRequiredMixin, View):
    """Record a result click to personalize future group ordering."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        object_type = request.POST.get("type", "")
        company = getattr(request, "current_company", None)
        if company and is_valid_type(object_type):
            record_click(request.user, company, object_type)
        return HttpResponse(status=204)
