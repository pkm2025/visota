import pytest
from apps.master_data.models import AccountType


@pytest.mark.django_db
def test_account_type_creation():
    at = AccountType.objects.create(
        code=1, name='Tài sản ngắn hạn',
        balance_type='debit', category='asset',
    )
    assert at.pk is not None
    assert str(at) == '1 - Tài sản ngắn hạn'


@pytest.mark.django_db
def test_account_type_str_includes_code():
    at = AccountType(code=2, name='Nợ phải trả')
    assert '2' in str(at)
    assert 'Nợ phải trả' in str(at)
