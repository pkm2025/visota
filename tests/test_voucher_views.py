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
    user = User.objects.create_superuser(username='alice', password='Secret123', email='alice@test.local')
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


@pytest.mark.django_db
def test_voucher_create_form_loads(auth_client):
    response = auth_client.get('/modern/vouchers/new/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'name="voucher_no"' in content or 'voucher_no' in content
    assert 'Bút toán' in content or 'lines' in content


@pytest.mark.django_db
def test_voucher_create_post_valid(setup_user_company, auth_client):
    company, _ = setup_user_company
    response = auth_client.post('/modern/vouchers/new/', {
        'voucher_no': 'BC0001',
        'voucher_date': '2026-06-15',
        'voucher_type': 'journal',
        'description': 'Test',
        'lines-TOTAL_FORMS': '2',
        'lines-INITIAL_FORMS': '0',
        'lines-MIN_NUM_FORMS': '2',
        'lines-MAX_NUM_FORMS': '1000',
        'lines-0-account_code': '111',
        'lines-0-debit_vnd': '1000',
        'lines-0-credit_vnd': '0',
        'lines-1-account_code': '5111',
        'lines-1-debit_vnd': '0',
        'lines-1-credit_vnd': '1000',
    })
    assert response.status_code == 302
    assert '/modern/vouchers/' in response.url
    v = AccountingVoucher.objects.get(voucher_no='BC0001')
    assert v.lines.count() == 2
    assert v.total_vnd == 1000
    # Default status is LEDGER (auto-posted)
    assert v.status == AccountingVoucher.Status.LEDGER


@pytest.mark.django_db
def test_voucher_create_unbalanced_fails(setup_user_company, auth_client):
    response = auth_client.post('/modern/vouchers/new/', {
        'voucher_no': 'BC0001',
        'voucher_date': '2026-06-15',
        'voucher_type': 'journal',
        'description': 'Test',
        'lines-TOTAL_FORMS': '2',
        'lines-INITIAL_FORMS': '0',
        'lines-0-account_code': '111',
        'lines-0-debit_vnd': '1000',
        'lines-0-credit_vnd': '0',
        'lines-1-account_code': '5111',
        'lines-1-debit_vnd': '0',
        'lines-1-credit_vnd': '500',  # imbalance
    })
    # Should re-render form with error, not crash
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'không cân đối' in content.lower() or 'not balanced' in content.lower() or 'alert' in content
