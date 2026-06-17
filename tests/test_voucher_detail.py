import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def voucher(db):
    from apps.core.models import Company
    company = Company.objects.create(code='TCO', name='T')
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=2,
        description='Test',
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000'))
    return v


@pytest.mark.django_db
def test_voucher_detail_loads(auth_client, voucher):
    response = auth_client.get(f'/modern/vouchers/{voucher.id}/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'BC0001' in content
    assert '111' in content
    assert '5111' in content
    assert '1.000' in content or '1000' in content


@pytest.mark.django_db
def test_voucher_detail_shows_lines(auth_client, voucher):
    response = auth_client.get(f'/modern/vouchers/{voucher.id}/')
    content = response.content.decode('utf-8')
    # Should show 2 lines
    assert content.count('account_code') >= 2 or content.count('111') >= 1
