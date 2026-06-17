import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup_user_company(db):
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_user(username='alice', password='Secret123')
    return company, user


@pytest.fixture
def auth_client(setup_user_company):
    _, user = setup_user_company
    c = Client()
    c.force_login(user)
    return c


def test_voucher_list_requires_login(db):
    c = Client()
    response = c.get('/modern/vouchers/')
    assert response.status_code == 302
    assert '/auth/login/' in response.url


@pytest.mark.django_db
def test_voucher_list_loads_empty(auth_client):
    response = auth_client.get('/modern/vouchers/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Phiếu kế toán' in content
    assert 'Thêm' in content  # Add button


@pytest.mark.django_db
def test_voucher_list_shows_voucher(setup_user_company, auth_client):
    company, _ = setup_user_company
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), description='Test voucher',
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('1000000'), credit_vnd=Decimal('0'),
    )

    response = auth_client.get('/modern/vouchers/')
    content = response.content.decode('utf-8')
    assert 'BC0001' in content
    assert 'Test voucher' in content
