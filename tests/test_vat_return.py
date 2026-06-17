import pytest
from decimal import Decimal
from datetime import date
from apps.sales.services import SalesInvoiceService
from apps.purchasing.services import PurchaseInvoiceService
from apps.master_data.models import Customer, Vendor, Product
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cust = Customer.objects.create(company=company, code='KH01', name='C')
    vend = Vendor.objects.create(company=company, code='NCC01', name='V')
    prod = Product.objects.create(
        company=company, code='SP01', name='P',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    return company, cust, vend, prod


def test_vat_return_output(setup):
    """Output VAT from sales invoices."""
    company, cust, vend, prod = setup
    SalesInvoiceService(company=company).create({
        'invoice_no': 'BC01', 'invoice_date': date(2026, 6, 10),
        'customer_id': cust.id,
        'lines': [{'product_id': prod.id, 'quantity': 10,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # Output: 1M revenue * 10% = 100k VAT
    assert result['vat_output'] == Decimal('100000')


def test_vat_return_input(setup):
    """Input VAT from purchase invoices."""
    company, cust, vend, prod = setup
    PurchaseInvoiceService(company=company).create({
        'invoice_no': 'PN01', 'invoice_date': date(2026, 6, 5),
        'vendor_id': vend.id,
        'lines': [{'product_id': prod.id, 'quantity': 5,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # Input: 500k * 10% = 50k VAT
    assert result['vat_input_credit'] == Decimal('50000')


def test_vat_return_payable(setup):
    """VAT payable = output - input."""
    company, cust, vend, prod = setup
    SalesInvoiceService(company=company).create({
        'invoice_no': 'BC01', 'invoice_date': date(2026, 6, 10),
        'customer_id': cust.id,
        'lines': [{'product_id': prod.id, 'quantity': 10,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })
    PurchaseInvoiceService(company=company).create({
        'invoice_no': 'PN01', 'invoice_date': date(2026, 6, 5),
        'vendor_id': vend.id,
        'lines': [{'product_id': prod.id, 'quantity': 5,
                   'unit_price': 100000, 'vat_rate': 0.10}],
        'post': True,
    })

    from apps.reporting.services import VATReturnService
    svc = VATReturnService(company=company)
    result = svc.generate(fiscal_year=2026, period=6)
    # 100k output - 50k input = 50k payable
    assert result['vat_payable'] == Decimal('50000')


def test_vat_return_view_loads(db):
    from django.test import Client
    from apps.identity.models import User
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    response = c.get('/modern/reports/vat-return/')
    assert response.status_code == 200
    assert 'GTGT' in response.content.decode('utf-8')
