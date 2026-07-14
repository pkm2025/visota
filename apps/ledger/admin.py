"""Django admin for ledger app."""

from django.contrib import admin

from apps.ledger.models import (
    AccountingVoucher,
    AccountPeriodBalance,
    DnsnLedgerBalance,
    DnsnLedgerEntry,
    DnsnVoucher,
    VoucherLine,
)


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


# ── TT58 DNSN models ──────────────────────────────────────────────────────


class DnsnLedgerEntryInline(admin.TabularInline):
    model = DnsnLedgerEntry
    extra = 0
    fields = (
        "line_no",
        "ledger_type",
        "entry_date",
        "description",
        "revenue_amount",
        "cost_amount",
        "vat_amount",
        "cash_in",
        "cash_out",
        "running_balance",
    )
    readonly_fields = ("running_balance",)


@admin.register(DnsnVoucher)
class DnsnVoucherAdmin(admin.ModelAdmin):
    list_display = (
        "voucher_no",
        "voucher_date",
        "voucher_type",
        "total_amount",
        "status",
    )
    list_filter = ("status", "voucher_type", "fiscal_year", "period")
    search_fields = ("voucher_no", "description", "partner_name")
    inlines = [DnsnLedgerEntryInline]


@admin.register(DnsnLedgerEntry)
class DnsnLedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "voucher",
        "line_no",
        "ledger_type",
        "entry_date",
        "revenue_amount",
        "cost_amount",
        "running_balance",
    )
    list_filter = ("ledger_type", "fiscal_year", "period")
    search_fields = ("description", "partner_name", "item_name")


@admin.register(DnsnLedgerBalance)
class DnsnLedgerBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "ledger_type",
        "fiscal_year",
        "period",
        "opening_revenue",
        "period_revenue",
        "closing_revenue",
        "closing_cash",
    )
    list_filter = ("ledger_type", "fiscal_year", "period")
    search_fields = ()
