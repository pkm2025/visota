import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_user(username='alice', password='Secret123')
    return company, user


@pytest.fixture
def auth_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_trial_balance_requires_login(db):
    c = Client()
    response = c.get('/modern/reports/trial-balance/')
    assert response.status_code == 302


@pytest.mark.django_db
def test_trial_balance_loads_empty(auth_client):
    response = auth_client.get('/modern/reports/trial-balance/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Bảng cân đối tài khoản' in content or 'BCĐ' in content


@pytest.mark.django_db
def test_trial_balance_shows_data(setup, auth_client):
    company, _ = setup
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('1000'), credit_vnd=Decimal('0'),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code='5111',
        debit_vnd=Decimal('0'), credit_vnd=Decimal('1000'),
    )
    VoucherPostingService().post(v)

    response = auth_client.get('/modern/reports/trial-balance/?fiscal_year=2026&period=6')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert '111' in content
    assert '5111' in content
    assert '1.000' in content or '1000' in content


@pytest.mark.django_db
def test_trial_balance_totals_balanced(setup, auth_client):
    """Total debit must equal total credit."""
    company, _ = setup
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code='111',
        debit_vnd=Decimal('5000'), credit_vnd=Decimal('0'),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code='5111',
        debit_vnd=Decimal('0'), credit_vnd=Decimal('5000'),
    )
    VoucherPostingService().post(v)

    response = auth_client.get('/modern/reports/trial-balance/?fiscal_year=2026&period=6')
    assert response.context['total_period_debit'] == Decimal('5000')
    assert response.context['total_period_credit'] == Decimal('5000')
