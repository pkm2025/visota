"""Bank loan models.

BankLoan: a single loan agreement with bank.
LoanDisbursement: each drawdown (N112 / C343).
LoanRepayment: principal repayment (N343 / C112).
LoanInterestAccrual: monthly interest (N635 / C343 or N112).
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class BankLoan(CompanyOwnedModel):
    class LoanType(models.TextChoices):
        SHORT_TERM = "short_term", "Ngắn hạn (< 1 năm)"
        LONG_TERM = "long_term", "Dài hạn (≥ 1 năm)"
        OVERDRAFT = "overdraft", "Thấu chi"

    class Status(models.TextChoices):
        DRAFT = "draft", "Dự thảo"
        ACTIVE = "active", "Đang vay"
        CLOSED = "closed", "Đã tất toán"
        DEFAULTED = "defaulted", "Quá hạn"

    loan_no = models.CharField(max_length=50)
    loan_type = models.CharField(
        max_length=20, choices=LoanType.choices, default=LoanType.SHORT_TERM
    )
    bank_name = models.CharField(max_length=100)
    bank_account = models.CharField(max_length=50, blank=True, default="")
    contract_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="VND")
    interest_rate_pa = models.DecimalField(
        max_digits=8, decimal_places=4, default=0.10
    )  # percent per year
    disbursement_date = models.DateField()
    maturity_date = models.DateField()
    payment_schedule = models.TextField(blank=True, default="")
    purpose = models.TextField(blank=True, default="")
    gl_account = models.CharField(max_length=20, default="343")  # 3431, 3432
    interest_account = models.CharField(max_length=20, default="635")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loans",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_loan"
        unique_together = [("company", "loan_no")]
        ordering = ["-contract_date", "-id"]

    def __str__(self):
        return f"{self.loan_no} — {self.bank_name} ({self.principal_amount:,.0f})"

    @property
    def outstanding_principal(self):
        disbursed = sum((d.amount for d in self.disbursements.all()), 0)
        repaid = sum((r.principal for r in self.repayments.all()), 0)
        return disbursed - repaid


class LoanDisbursement(models.Model):
    loan = models.ForeignKey(BankLoan, on_delete=models.CASCADE, related_name="disbursements")
    disbursement_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    description = models.CharField(max_length=500, blank=True, default="")
    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loan_disbursement"


class LoanRepayment(models.Model):
    loan = models.ForeignKey(BankLoan, on_delete=models.CASCADE, related_name="repayments")
    payment_date = models.DateField()
    principal = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    interest = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    description = models.CharField(max_length=500, blank=True, default="")
    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loan_repayment"


class LoanInterestAccrual(models.Model):
    loan = models.ForeignKey(BankLoan, on_delete=models.CASCADE, related_name="interest_accruals")
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    days = models.PositiveSmallIntegerField()  # days in period
    principal_base = models.DecimalField(max_digits=20, decimal_places=4)
    interest_amount = models.DecimalField(max_digits=20, decimal_places=4)
    description = models.CharField(max_length=500, blank=True, default="")
    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loan_interest_accrual"
        unique_together = [("loan", "period_year", "period_month")]
