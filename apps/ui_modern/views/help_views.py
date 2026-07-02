"""In-app Knowledge Base / Help center.

Reuses BlogArticle with a 'help' category tag. Provides a searchable
help index at /modern/help/ and article detail view.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.public.models import BlogArticle


class HelpIndexView(LoginRequiredMixin, View):
    """Knowledge Base index — list help articles grouped by category."""

    template_name = "modern/help/index.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        articles = BlogArticle.objects.filter(
            status=BlogArticle.Status.PUBLISHED, tags__icontains="help"
        ).order_by("title")

        search = request.GET.get("search", "").strip()
        if search:
            articles = articles.filter(title__icontains=search) | articles.filter(
                excerpt__icontains=search
            )

        # Group by first tag (after 'help')
        grouped = {}
        for article in articles:
            category = "Khác"
            for tag in article.tag_list:
                if tag != "help":
                    category = tag
                    break
            grouped.setdefault(category, []).append(article)

        return render(
            request,
            self.template_name,
            {
                "page_title": "Trợ giúp",
                "grouped_articles": grouped,
                "total_articles": articles.count(),
                "search": search,
            },
        )


class HelpDetailView(LoginRequiredMixin, View):
    """Single help article detail."""

    template_name = "modern/help/detail.html"
    login_url = "/auth/login/"

    def get(self, request, slug, *args, **kwargs):
        article = get_object_or_404(
            BlogArticle,
            slug=slug,
            status=BlogArticle.Status.PUBLISHED,
            tags__icontains="help",
        )
        article.view_count += 1
        article.save(update_fields=["view_count"])

        related = (
            BlogArticle.objects.filter(status=BlogArticle.Status.PUBLISHED, tags__icontains="help")
            .exclude(id=article.id)
            .order_by("-view_count")[:5]
        )

        return render(
            request,
            self.template_name,
            {
                "page_title": article.title,
                "article": article,
                "related": related,
            },
        )
