"""Tag model for user-specific tag classification."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Tag(CompanyOwnedModel):
    """User-specific tag for classifying knowledge notes and documents.

    Unique per (user, company, name) so each user has their own tag namespace
    within a company.
    """

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_tags",
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_tag"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company", "name"],
                name="unique_tag_user_company_name",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "company"]),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.username})"
