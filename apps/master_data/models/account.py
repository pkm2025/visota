"""Chart of accounts models."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class AccountType(models.Model):
    """Type of account: asset, liability, equity, revenue, expense, etc."""

    class BalanceType(models.TextChoices):
        DEBIT = "debit", "Nợ"
        CREDIT = "credit", "Có"

    class Category(models.TextChoices):
        ASSET = "asset", "Tài sản"
        LIABILITY = "liability", "Nợ phải trả"
        EQUITY = "equity", "Vốn chủ sở hữu"
        REVENUE = "revenue", "Doanh thu"
        EXPENSE = "expense", "Chi phí"
        OTHER_INCOME = "other_income", "Thu nhập khác"
        OTHER_EXPENSE = "other_expense", "Chi phí khác"
        OFF_BALANCE = "off_balance", "Ngoài bảng"

    code = models.SmallIntegerField(unique=True)
    name = models.CharField(max_length=100)
    balance_type = models.CharField(
        max_length=10,
        choices=BalanceType.choices,
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "account_type"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ChartOfAccounts(CompanyOwnedModel):
    """Chart of accounts entry. Tree via parent_account_code (string FK)."""

    class ExchangeRateMethod(models.TextChoices):
        NONE = "NONE", "Không áp dụng"
        AVG = "AVG", "Bình quân"
        ENDING = "ENDING", "Cuối kỳ"
        SPOT = "SPOT", "Giao dịch"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="accounts",
        db_index=True,
    )
    account_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    account_name_en = models.CharField(max_length=255, blank=True)
    short_name = models.CharField(max_length=100, blank=True)

    parent_account_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
    )
    currency_code = models.CharField(max_length=3, default="VND")

    exchange_rate_method_debit = models.CharField(
        max_length=10,
        choices=ExchangeRateMethod.choices,
        default=ExchangeRateMethod.NONE,
        help_text="Phương pháp tính tỷ giá cho bên Nợ",
    )
    exchange_rate_method_credit = models.CharField(
        max_length=10,
        choices=ExchangeRateMethod.choices,
        default=ExchangeRateMethod.NONE,
        help_text="Phương pháp tính tỷ giá cho bên Có",
    )

    account_level = models.PositiveSmallIntegerField(default=1)
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        related_name="accounts",
    )

    is_posting_account = models.BooleanField(
        default=False, help_text="Có cho phép hạch toán trực tiếp?"
    )
    is_general_ledger_account = models.BooleanField(default=False, help_text="Là tài khoản sổ cái?")
    is_active = models.BooleanField(default=True)

    allows_object_code = models.BooleanField(default=False)
    allows_cost_center = models.BooleanField(default=False)
    allows_project = models.BooleanField(default=False)
    allows_production_order = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "chart_of_accounts"
        unique_together = [("company", "account_code")]
        ordering = ["account_code"]
        indexes = [
            models.Index(fields=["company", "parent_account_code"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"
