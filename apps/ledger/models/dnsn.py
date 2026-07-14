"""TT58/2026/TT-BTC simplified ledger models for Doanh nghiệp siêu nhỏ (DNSN).

These models implement the DNSN accounting regime that bypasses the
double-entry (No/Có) chart-of-accounts system. Instead of debit/credit
pairs tied to account codes, entries store direct transaction amounts
(revenue, cost, tax, cash) classified by ledger type (S1-S4).
"""

from decimal import Decimal

from django.db import models

from apps.core.managers import CompanyOwnedModel


class DnsnVoucher(CompanyOwnedModel):
    """Simplified voucher for DNSN (phiếu thu/chi/nhập/xuất etc.).

    Unlike AccountingVoucher, this model has no account_code, debit, or
    credit fields. It records simplified transactions for micro/small
    enterprises following TT58/2026/TT-BTC.
    """

    class VoucherType(models.TextChoices):
        PHIEU_THU = "phieu_thu", "Phiếu thu"
        PHIEU_CHI = "phieu_chi", "Phiếu chi"
        PHIEU_NHAP = "phieu_nhap", "Phiếu nhập"
        PHIEU_XUAT = "phieu_xuat", "Phiếu xuất"
        HOA_DON_BAN_HANG = "hoa_don_ban_hang", "Hóa đơn bán hàng"
        HOA_DON_MUA_HANG = "hoa_don_mua_hang", "Hóa đơn mua hàng"
        CHUNG_TU_KHAC = "chung_tu_khac", "Chứng từ khác"

    class Status(models.TextChoices):
        DRAFT = "draft", "Lưu tạm"
        POSTED = "posted", "Đã ghi sổ"
        LOCKED = "locked", "Đã khóa"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="dnsn_vouchers",
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    voucher_no = models.CharField(max_length=50)
    voucher_type = models.CharField(max_length=30, choices=VoucherType.choices)
    voucher_date = models.DateField()
    posting_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    # Partner info (simplified, no object code linkage)
    partner_name = models.CharField(max_length=255, blank=True, default="")
    partner_tax_code = models.CharField(max_length=20, blank=True, default="")
    partner_address = models.CharField(max_length=500, blank=True, default="")

    # Invoice info
    invoice_no = models.CharField(max_length=50, blank=True, default="")
    invoice_date = models.DateField(null=True, blank=True)
    invoice_form = models.CharField(max_length=20, blank=True, default="")
    invoice_serial = models.CharField(max_length=50, blank=True, default="")

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # Total amounts for display
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "dnsn_voucher"
        unique_together = [
            ("company", "fiscal_year", "voucher_type", "voucher_no"),
        ]
        indexes = [
            models.Index(fields=["company", "voucher_date"]),
            models.Index(fields=["company", "fiscal_year", "period", "status"]),
            models.Index(fields=["company", "voucher_type", "voucher_date"]),
        ]
        ordering = ["-voucher_date", "-id"]

    def __str__(self):
        return f"{self.voucher_no} ({self.voucher_date})"

    @property
    def is_posted(self):
        return self.status in (self.Status.POSTED, self.Status.LOCKED)

    @property
    def is_locked(self):
        return self.status == self.Status.LOCKED


class DnsnLedgerEntry(CompanyOwnedModel):
    """Direct ledger entry for DNSN (no double-entry No/Có).

    Instead of account_code + debit/credit, entries store transaction
    amounts directly: revenue_amount, cost_amount, vat_amount, tndn_amount,
    cash_in, cash_out, bank_in, bank_out, etc.

    Classified by ledger_type (S1-S4) per TT58/2026/TT-BTC.
    """

    class LedgerType(models.TextChoices):
        S1 = "s1", "S1-DNSN (Sổ doanh thu — Nhóm 1)"
        S2A = "s2a", "S2a-DNSN (Sổ doanh thu — Nhóm 2)"
        S2B = "s2b", "S2b-DNSN (Sổ chi tiết doanh thu, chi phí)"
        S2C = "s2c", "S2c-DNSN (Sổ vật liệu, hàng hóa)"
        S2D = "s2d", "S2d-DNSN (Sổ chi tiết tiền)"
        S3A = "s3a", "S3a-DNSN (Sổ doanh thu — Nhóm 3)"
        S3B = "s3b", "S3b-DNSN (Sổ nghĩa vụ thuế GTGT)"
        S4A = "s4a", "S4a-DNSN (Sổ công nợ — tùy chọn)"
        S4B = "s4b", "S4b-DNSN (Sổ TSCĐ — tùy chọn)"
        S4C = "s4c", "S4c-DNSN (Sổ thuế khác — tùy chọn)"
        S4D = "s4d", "S4d-DNSN (Sổ vốn CSH — tùy chọn)"

    voucher = models.ForeignKey(
        DnsnVoucher,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="dnsn_ledger_entries",
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    line_no = models.PositiveSmallIntegerField()
    entry_date = models.DateField()
    ledger_type = models.CharField(max_length=10, choices=LedgerType.choices)
    description = models.TextField(blank=True, default="")
    partner_name = models.CharField(max_length=255, blank=True, default="")

    # Revenue / cost fields (S1, S2a, S2b, S3a)
    revenue_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    cost_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Tax fields
    vat_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    tndn_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Cash fields (S2d)
    cash_in = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    cash_out = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bank_in = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bank_out = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # VAT tracking (S3b)
    vat_input = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_output = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_payable = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Inventory fields (S2c)
    item_code = models.CharField(max_length=50, blank=True, default="")
    item_name = models.CharField(max_length=255, blank=True, default="")
    quantity = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    unit_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Running balance — cumulative amount for this ledger_type
    # up to and including this entry, ordered by (entry_date, id).
    running_balance = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "dnsn_ledger_entry"
        unique_together = [("voucher", "line_no")]
        indexes = [
            models.Index(fields=["company", "fiscal_year", "period", "ledger_type"]),
            models.Index(fields=["company", "ledger_type", "entry_date"]),
        ]
        ordering = ["entry_date", "id", "line_no"]

    def __str__(self):
        return f"{self.ledger_type} — {self.entry_date} (line {self.line_no})"


class DnsnLedgerBalance(CompanyOwnedModel):
    """Period balance per ledger type for DNSN.

    Tracks opening and closing balances for each ledger_type (S1-S4)
    per company, fiscal year, and period. Updated by DnsnPostingService
    on post/unpost. Rebuildable from DnsnLedgerEntry.
    """

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="dnsn_ledger_balances",
        db_index=True,
    )
    fiscal_year = models.SmallIntegerField()
    period = models.PositiveSmallIntegerField()
    ledger_type = models.CharField(max_length=10, choices=DnsnLedgerEntry.LedgerType.choices)

    # Revenue balances (S1, S2a, S2b, S3a)
    opening_revenue = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_revenue = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_revenue = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Cost balances (S2b)
    opening_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Tax balances (S3b)
    opening_vat = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_vat = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_vat = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Cash balances (S2d)
    opening_cash = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    period_cash = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    closing_cash = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    last_transaction_date = models.DateField(null=True, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "dnsn_ledger_balance"
        unique_together = [
            ("company", "fiscal_year", "period", "ledger_type"),
        ]
        indexes = [
            models.Index(fields=["company", "fiscal_year", "period"]),
            models.Index(fields=["ledger_type"]),
        ]

    def __str__(self):
        return f"{self.ledger_type} P{self.period}/{self.fiscal_year}"

    def recalculate_closing(self):
        """Compute closing from opening + period for all amount categories."""
        self.closing_revenue = self.opening_revenue + self.period_revenue
        self.closing_cost = self.opening_cost + self.period_cost
        self.closing_vat = self.opening_vat + self.period_vat
        self.closing_cash = self.opening_cash + self.period_cash

    def reset_period(self):
        """Reset period accumulators to zero (used on unpost when entries removed)."""
        self.period_revenue = Decimal("0")
        self.period_cost = Decimal("0")
        self.period_vat = Decimal("0")
        self.period_cash = Decimal("0")
        self.recalculate_closing()
