"""Bank reconciliation models.

BankAccount: per-company bank accounts.
BankStatementImport: import session (CSV/Excel/XML).
BankTransaction: line from statement.
ReconciliationMatch: link between BankTransaction and voucher/cash receipt/payment.
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class BankAccount(CompanyOwnedModel):
    """Bank account of the company."""

    code = models.CharField(max_length=30)
    bank_name = models.CharField(max_length=100)
    bank_branch = models.CharField(max_length=100, blank=True, default="")
    account_number = models.CharField(max_length=50)
    account_holder = models.CharField(max_length=255)
    currency_code = models.CharField(max_length=3, default="VND")
    gl_account = models.CharField(max_length=20, default="1121")  # 1121, 1122
    opening_balance = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_account"
        unique_together = [("company", "account_number")]
        ordering = ["bank_name", "account_number"]

    def __str__(self):
        return f"{self.account_number} — {self.bank_name}"


class BankStatementImport(CompanyOwnedModel):
    """A single upload of a bank statement (CSV/Excel/XML)."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Đã tải lên"
        PARSED = "parsed", "Đã parse"
        RECONCILED = "reconciled", "Đã đối soát"
        ARCHIVED = "archived", "Lưu trữ"

    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="imports"
    )
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="banking/imports/", null=True, blank=True)
    period_from = models.DateField()
    period_to = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADED
    )
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bank_imports",
    )
    note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bank_statement_import"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.bank_account.account_number} {self.period_from} → {self.period_to}"


class BankTransaction(models.Model):
    """A single transaction from a bank statement."""

    class Direction(models.TextChoices):
        DEBIT = "debit", "Bank debit (chi)"  # money out
        CREDIT = "credit", "Bank credit (thu)"  # money in

    import_session = models.ForeignKey(
        BankStatementImport, on_delete=models.CASCADE, related_name="transactions"
    )
    company = models.ForeignKey(
        "core.Company", on_delete=models.CASCADE, related_name="bank_transactions"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    txn_date = models.DateField(db_index=True)
    value_date = models.DateField(null=True, blank=True)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="VND")
    counterparty_name = models.CharField(max_length=255, blank=True, default="")
    counterparty_account = models.CharField(max_length=50, blank=True, default="")
    counterparty_bank = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    reference = models.CharField(max_length=100, blank=True, default="", db_index=True)
    is_reconciled = models.BooleanField(default=False, db_index=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bank_transaction"
        ordering = ["-txn_date", "-id"]
        indexes = [
            models.Index(fields=["company", "is_reconciled", "-txn_date"]),
            models.Index(fields=["bank_account", "-txn_date"]),
        ]

    def __str__(self):
        return f"{self.txn_date} {self.direction} {self.amount:,.0f} — {self.description[:50]}"


class ReconciliationMatch(models.Model):
    """A match between a bank transaction and a system record (voucher/cash receipt/payment)."""

    class MatchMethod(models.TextChoices):
        AUTO = "auto", "Tự động"
        MANUAL = "manual", "Thủ công"

    transaction = models.ForeignKey(
        BankTransaction, on_delete=models.CASCADE, related_name="matches"
    )
    content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField()
    object_label = models.CharField(max_length=255)
    object_amount = models.DecimalField(max_digits=20, decimal_places=4)
    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    match_method = models.CharField(
        max_length=10, choices=MatchMethod.choices, default=MatchMethod.AUTO
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bank_reconciliation_match"
        unique_together = [("transaction", "content_type", "object_id")]

    def __str__(self):
        return f"Txn#{self.transaction_id} ↔ {self.object_label}"
