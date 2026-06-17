"""RecurringTemplate model — automated recurring accounting entries."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class RecurringTemplate(CompanyOwnedModel):
    """Template for automated recurring accounting entries."""

    class ScheduleType(models.TextChoices):
        MONTHLY = "monthly", "Hàng tháng"
        QUARTERLY = "quarterly", "Hàng quý"
        YEARLY = "yearly", "Hàng năm"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="recurring_templates",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    # Dotted path to a callable: ``module.path:func`` or ``module.path.func``
    # The callable must accept (company, **opts) and return a JSON-serializable result.
    service_func = models.CharField(
        max_length=255,
        help_text="Dotted path: apps.recurring.runners.run_depreciation",
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.MONTHLY,
    )
    day_of_month = models.PositiveSmallIntegerField(
        default=1, help_text="Day of month to run on (1-28)"
    )
    is_active = models.BooleanField(default=True)

    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_result = models.JSONField(default=dict, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "recurring_template"
        verbose_name = "Bút toán định kỳ"
        verbose_name_plural = "Bút toán định kỳ"
        ordering = ["schedule_type", "day_of_month", "id"]
        indexes = [
            models.Index(fields=["company", "is_active", "next_run_at"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.schedule_type} d{self.day_of_month}]"
