"""Chart of Accounts models."""
from django.db import models


class AccountType(models.Model):
    """Type of account: asset, liability, equity, revenue, expense, etc."""

    class BalanceType(models.TextChoices):
        DEBIT = 'debit', 'Nợ'
        CREDIT = 'credit', 'Có'

    class Category(models.TextChoices):
        ASSET = 'asset', 'Tài sản'
        LIABILITY = 'liability', 'Nợ phải trả'
        EQUITY = 'equity', 'Vốn chủ sở hữu'
        REVENUE = 'revenue', 'Doanh thu'
        EXPENSE = 'expense', 'Chi phí'
        OTHER_INCOME = 'other_income', 'Thu nhập khác'
        OTHER_EXPENSE = 'other_expense', 'Chi phí khác'
        OFF_BALANCE = 'off_balance', 'Ngoài bảng'

    code = models.SmallIntegerField(unique=True)
    name = models.CharField(max_length=100)
    balance_type = models.CharField(
        max_length=10, choices=BalanceType.choices,
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'account_type'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'
