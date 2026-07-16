"""WikiPage model - the LLM-maintained markdown wiki layer (Karpathy pattern).

Layer 2 of the PKM wiki architecture: a persistent, compounding set of
markdown pages that AI ingests, queries, and lints. Each page is scoped
per-user and per-company (multi-tenant) and may cross-reference other
pages (``linked_pages``) and cite the source documents that informed it
(``source_refs``).

Page types follow the wiki schema:
- summary: per-source digest
- concept: a recurring concept (e.g. "VAT")
- entity: a named entity (e.g. a vendor, a regulation)
- overview: an auto-generated index/catalogue
- synthesis: a cross-source synthesis page
"""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class WikiPage(CompanyOwnedModel):
    """An LLM-maintained markdown wiki page (Karpathy LLM Wiki pattern).

    Pages are unique per (user, company, title) so each tenant has their
    own wiki namespace. AI-authored pages set ``is_ai_generated=True``;
    system-seeded shared pages set ``is_system=True``.
    """

    class PageType(models.TextChoices):
        SUMMARY = "summary", "Summary"
        CONCEPT = "concept", "Concept"
        ENTITY = "entity", "Entity"
        OVERVIEW = "overview", "Overview"
        SYNTHESIS = "synthesis", "Synthesis"

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_wiki_pages",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="", help_text="Markdown content")
    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices,
        default=PageType.SUMMARY,
        help_text="Wiki page type (summary/concept/entity/overview/synthesis)",
    )
    source_refs = models.ManyToManyField(
        "pkm.PKMDocument",
        blank=True,
        related_name="wiki_pages",
        help_text="Source documents that informed this page",
    )
    linked_pages = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        help_text="Cross-references to other wiki pages ([[wikilinks]])",
    )
    tags = models.ManyToManyField(
        "pkm.Tag",
        blank=True,
        related_name="wiki_pages",
    )
    is_ai_generated = models.BooleanField(
        default=False,
        help_text="True if authored/synthesised by the LLM ingest pipeline",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="True for shared cross-tenant system pages (e.g. regulation overviews)",
    )
    last_ingest_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the wiki ingest pipeline last updated this page",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_wiki_page"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company", "title"],
                name="unique_wiki_page_user_company_title",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "page_type"]),
            models.Index(fields=["is_system"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title
