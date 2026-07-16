import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.core.models import Company


@pytest.fixture
def company_with_pnl_data(db):
    company = Company.objects.create(code='TCO', name='Test')
    # Revenue: C5111 5000, C33311 500 (VAT)
    # Expense: N632 3000 (COGS), N642 1000 (Admin)
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC01', voucher_type='sales_invoice',
        voucher_date=date(2026, 6, 15), status=0,
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='131', debit_vnd=Decimal('5500'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('5000'))
    VoucherLine.objects.create(voucher=v, line_no=3, account_code='33311', credit_vnd=Decimal('500'))
    VoucherPostingService().post(v)

    v2 = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC02', voucher_type='journal',
        voucher_date=date(2026, 6, 16), status=0,
    )
    VoucherLine.objects.create(voucher=v2, line_no=1, account_code='632', debit_vnd=Decimal('3000'))
    VoucherLine.objects.create(voucher=v2, line_no=2, account_code='642', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v2, line_no=3, account_code='111', credit_vnd=Decimal('4000'))
    VoucherPostingService().post(v2)
    return company


def test_pnl_revenue(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['revenue'] == Decimal('5000')


def test_pnl_cogs(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['cogs'] == Decimal('3000')


def test_pnl_gross_profit(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    # Revenue 5000 - COGS 3000 = 2000
    assert result['gross_profit'] == Decimal('2000')


def test_pnl_admin_expense(company_with_pnl_data):
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['admin_expense'] == Decimal('1000')


def test_pnl_operating_profit(company_with_pnl_data):
    """Gross 2000 - Admin 1000 = 1000 operating profit."""
    from apps.reporting.services import PnLService
    svc = PnLService(company=company_with_pnl_data)
    result = svc.generate(fiscal_year=2026, period=6)
    assert result['operating_profit'] == Decimal('1000')


def test_pnl_view_loads(db):
    from django.test import Client
    from apps.identity.models import User
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_superuser(username='alice', password='Secret123', email='alice@test.local')
    c = Client()
    c.force_login(user)
    session = c.session
    session['current_company_id'] = company.id
    session.save()
    response = c.get('/modern/reports/pnl/')
    assert response.status_code == 200
    assert 'Kết quả' in response.content.decode('utf-8')
