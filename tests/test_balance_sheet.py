import pytest
from decimal import Decimal
from datetime import date
from django.test import Client
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def company_with_data(db):
    """Company with posted vouchers so balances exist."""
    company = Company.objects.create(code='TCO', name='Test')
    # Post a simple voucher: N111 1000 / C411 1000
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), status=0,
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='411', credit_vnd=Decimal('1000'))
    VoucherPostingService().post(v)
    return company


def test_balance_sheet_returns_dict(company_with_data):
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert 'assets' in result
    assert 'liabilities_equity' in result
    assert isinstance(result['assets'], dict)


def test_balance_sheet_assets_include_111(company_with_data):
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    # TK 111 (Tiền mặt) is asset type 1 → should be in assets
    assert result['assets']['total'] > 0
    # The amount should include 1000 from N111
    assert Decimal('1000') in [r['amount'] for r in result['assets']['rows']]


def test_balance_sheet_balanced(company_with_data):
    """Total assets must equal total liabilities + equity."""
    from apps.reporting.services import BalanceSheetService
    svc = BalanceSheetService(company=company_with_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['assets']['total'] == result['liabilities_equity']['total']


def test_balance_sheet_view_loads(db):
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.get('/modern/reports/balance-sheet/')
    assert response.status_code == 200
    assert 'Báo cáo tình hình tài chính' in response.content.decode('utf-8')
