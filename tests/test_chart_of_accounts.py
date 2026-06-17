import pytest
from apps.master_data.models import ChartOfAccounts, AccountType


@pytest.fixture
def asset_type(db):
    return AccountType.objects.create(
        code=1, name='Tài sản', balance_type='debit', category='asset',
    )


@pytest.fixture
def company(db):
    from apps.core.models import Company
    return Company.objects.create(code='TCO', name='Test Co')


def test_account_creation(asset_type, company):
    acc = ChartOfAccounts.objects.create(
        company=company,
        account_code='111',
        account_name='Tiền mặt',
        parent_account_code=None,
        account_level=1,
        account_type=asset_type,
        is_posting_account=False,
        is_general_ledger_account=True,
    )
    assert acc.pk is not None
    assert str(acc) == '111 - Tiền mặt'


def test_account_tree(asset_type, company):
    """Parent-child relationship via account_code."""
    parent = ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='Tiền mặt',
        account_level=1, account_type=asset_type,
    )
    child = ChartOfAccounts.objects.create(
        company=company, account_code='1111', account_name='Tiền Việt Nam',
        parent_account_code='111',
        account_level=2, account_type=asset_type,
    )
    assert child.parent_account_code == '111'


def test_account_unique_per_company(asset_type, company):
    """Same account_code can exist in different companies."""
    from apps.core.models import Company
    other = Company.objects.create(code='OCO', name='Other Co')
    ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='A',
        account_level=1, account_type=asset_type,
    )
    ChartOfAccounts.objects.create(
        company=other, account_code='111', account_name='B',
        account_level=1, account_type=asset_type,
    )
    # No error — different companies
    assert ChartOfAccounts.objects.filter(company=company).count() == 1
    assert ChartOfAccounts.objects.filter(company=other).count() == 1


def test_account_duplicate_in_same_company_fails(asset_type, company):
    from django.db import IntegrityError
    ChartOfAccounts.objects.create(
        company=company, account_code='111', account_name='A',
        account_level=1, account_type=asset_type,
    )
    with pytest.raises(IntegrityError):
        ChartOfAccounts.objects.create(
            company=company, account_code='111', account_name='B',
            account_level=1, account_type=asset_type,
        )


def test_account_defaults(asset_type, company):
    """New account defaults to active, currency VND, regime-independent."""
    acc = ChartOfAccounts(
        company=company, account_code='X', account_name='Test',
        account_level=1, account_type=asset_type,
    )
    assert acc.is_active is True
    assert acc.currency_code == 'VND'
    assert acc.is_posting_account is False
