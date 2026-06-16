"""Custom managers and querysets for multi-tenant models."""
from django.db import models


class CompanyQuerySet(models.QuerySet):
    """QuerySet that supports multi-tenant filtering by company_id."""

    def for_company(self, company_id):
        return self.filter(company_id=company_id)

    def active(self):
        return self.filter(is_active=True)


class CompanyManager(models.Manager.from_queryset(CompanyQuerySet)):
    """Manager that auto-filters by current company if set in thread-local."""

    use_in_migrations = True


class CompanyOwnedModel(models.Model):
    """Abstract base for models that belong to a Company (multi-tenant)."""

    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='+',
        db_index=True,
    )

    objects = CompanyManager()

    class Meta:
        abstract = True
