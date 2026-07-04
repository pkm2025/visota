"""Django admin for master_data app."""

from django.contrib import admin

from apps.master_data.models import InvoiceGroup, TaxRateCode


@admin.register(TaxRateCode)
class TaxRateCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "rate", "display_name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "display_name")
    ordering = ("sort_order", "code")


@admin.register(InvoiceGroup)
class InvoiceGroupAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name_vi",
        "name_en",
        "default_tax_account_debit",
        "default_tax_account_credit",
        "sort_order",
    )
    search_fields = ("code", "name_vi", "name_en")
    ordering = ("sort_order", "code")
