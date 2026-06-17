import pytest
from django.core.management import call_command
from apps.master_data.models import ChartOfAccounts, AccountType
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test Co')


def test_load_tt133_creates_account_types(company):
    call_command('load_tt133', company_code='TCO')
    # TT133 has ~10 account types
    assert AccountType.objects.count() >= 9


def test_load_tt133_creates_accounts(company):
    call_command('load_tt133', company_code='TCO')
    # TT133 has ~100-120 accounts at minimum
    assert ChartOfAccounts.objects.filter(company=company).count() >= 100


def test_load_tt133_includes_key_accounts(company):
    call_command('load_tt133', company_code='TCO')
    codes = set(ChartOfAccounts.objects.filter(company=company)
                .values_list('account_code', flat=True))
    # Must have these critical accounts
    assert '111' in codes  # Tiền mặt
    assert '112' in codes  # TGNH
    assert '131' in codes  # Phải thu khách
    assert '331' in codes  # Phải trả NCC
    assert '511' in codes  # Doanh thu
    assert '632' in codes  # Giá vốn
    assert '911' in codes  # XĐKQ


def test_load_tt133_idempotent(company):
    """Running twice should not duplicate."""
    call_command('load_tt133', company_code='TCO')
    count1 = ChartOfAccounts.objects.filter(company=company).count()
    call_command('load_tt133', company_code='TCO')
    count2 = ChartOfAccounts.objects.filter(company=company).count()
    assert count1 == count2
