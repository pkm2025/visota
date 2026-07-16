"""Django admin for PKM app."""

from django.contrib import admin

from apps.pkm.models import WikiPage


@admin.register(WikiPage)
class WikiPageAdmin(admin.ModelAdmin):
    """Admin registration for the LLM-maintained wiki page model."""

    list_display = (
        "title",
        "user",
        "company",
        "page_type",
        "is_ai_generated",
        "is_system",
        "updated_at",
    )
    list_filter = ("page_type", "is_ai_generated", "is_system")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at", "last_ingest_at")
    filter_horizontal = ("source_refs", "linked_pages", "tags")
