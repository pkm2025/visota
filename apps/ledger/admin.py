"""Django admin for ledger app."""

from django.contrib import admin

from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine


class VoucherLineInline(admin.TabularInline):
    model = VoucherLine
    extra = 0
    fields = (
        "line_no",
        "account_code",
        "debit_vnd",
        "credit_vnd",
        "description",
        "invoice_no",
        "invoice_date",
        "invoice_form",
        "invoice_symbol",
        "tax_code",
        "tax_rate",
        "goods_amount_vnd",
        "tax_amount_vnd",
        "offset_account_code",
        "invoice_group_code",
    )
    readonly_fields = ()


@admin.register(AccountingVoucher)
class AccountingVoucherAdmin(admin.ModelAdmin):
    list_display = ("voucher_no", "voucher_date", "voucher_type", "total_vnd", "status")
    list_filter = ("status", "voucher_type", "fiscal_year", "period")
    search_fields = ("voucher_no", "description")
    inlines = [VoucherLineInline]


@admin.register(VoucherLine)
class VoucherLineAdmin(admin.ModelAdmin):
    list_display = (
        "voucher",
        "line_no",
        "account_code",
        "debit_vnd",
        "credit_vnd",
        "invoice_no",
        "tax_code",
        "invoice_group_code",
    )
    list_filter = ("tax_code", "invoice_group_code")
    search_fields = ("account_code", "invoice_no", "description")


admin.site.register(AccountPeriodBalance)
