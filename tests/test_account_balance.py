import pytest
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_balance_creation(company):
    b = AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='111',
        opening_debit=Decimal('1000'),
        period_debit=Decimal('500'),
        period_credit=Decimal('200'),
        closing_debit=Decimal('1300'),
        closing_credit=Decimal('0'),
    )
    assert b.pk is not None
    assert b.closing_debit == Decimal('1300')


def test_balance_unique_per_company_period_account(company):
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='111',
    )
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        AccountPeriodBalance.objects.create(
            company=company, fiscal_year=2026, period=6,
            account_code='111',
        )


def test_balance_with_object_code(company):
    """Same account can have multiple balances per object_code."""
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='131', object_type='customer', object_code='KH001',
    )
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=6,
        account_code='131', object_type='customer', object_code='KH002',
    )
    assert AccountPeriodBalance.objects.filter(account_code='131').count() == 2
