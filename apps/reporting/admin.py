"""Django admin for reporting app."""

from django.contrib import admin

from apps.reporting.models import FinancialReportLine


@admin.register(FinancialReportLine)
class FinancialReportLineAdmin(admin.ModelAdmin):
    list_display = (
        "report_type",
        "stt",
        "ma_so",
        "chi_tieu",
        "is_header",
        "display_order",
    )
    list_filter = ("report_type", "is_header")
    list_editable = ("is_header", "display_order")
    search_fields = ("ma_so", "chi_tieu", "stt")
    ordering = ("report_type", "display_order")
