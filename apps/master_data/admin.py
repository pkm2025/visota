"""Django admin for master_data app."""

from django.contrib import admin

from apps.master_data.models import ChartOfAccounts, InvoiceGroup, TaxRateCode


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


@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = (
        "account_code",
        "account_name",
        "currency_code",
        "exchange_rate_method_debit",
        "exchange_rate_method_credit",
        "is_active",
    )
    list_filter = ("currency_code", "exchange_rate_method_debit", "exchange_rate_method_credit")
    search_fields = ("account_code", "account_name")
    ordering = ("account_code",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "company",
                    "account_code",
                    "account_name",
                    "account_name_en",
                    "short_name",
                    "parent_account_code",
                    "currency_code",
                    "account_level",
                    "account_type",
                ),
            },
        ),
        (
            "Phương pháp tính tỷ giá",
            {
                "fields": (
                    "exchange_rate_method_debit",
                    "exchange_rate_method_credit",
                ),
            },
        ),
        (
            "Trạng thái",
            {
                "fields": (
                    "is_posting_account",
                    "is_general_ledger_account",
                    "is_active",
                    "allows_object_code",
                    "allows_cost_center",
                    "allows_project",
                    "allows_production_order",
                    "notes",
                ),
            },
        ),
    )
