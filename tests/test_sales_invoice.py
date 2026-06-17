import pytest
from decimal import Decimal
from datetime import date
from apps.sales.models import SalesInvoice, SalesInvoiceLine
from apps.sales.services import SalesInvoiceService
from apps.master_data.models import Customer, Product
from apps.ledger.models import AccountingVoucher
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    customer = Customer.objects.create(company=company, code='KH001', name='ABC')
    product = Product.objects.create(
        company=company, code='SP001', name='Pin',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    return company, customer, product


def test_invoice_creation_generates_voucher(setup):
    """Creating a posted invoice generates an accounting voucher."""
    company, customer, product = setup
    service = SalesInvoiceService(company=company)

    invoice = service.create({
        'invoice_no': 'BC0001',
        'invoice_date': date(2026, 6, 15),
        'customer_id': customer.id,
        'lines': [
            {
                'product_id': product.id,
                'quantity': Decimal('10'),
                'unit_price': Decimal('100000'),
                'vat_rate': Decimal('0.10'),
            },
        ],
        'post': True,
    })

    assert invoice.pk is not None
    assert invoice.total_amount == Decimal('1100000')  # 10 * 100k + 10% VAT

    # Voucher created
    voucher = AccountingVoucher.objects.get(source_reference_id=invoice.id)
    assert voucher.voucher_type == 'sales_invoice'
    assert voucher.is_posted

    # Voucher lines: N131 (1100k), C5111 (1000k), C33311 (100k)
    lines = voucher.lines.all()
    account_codes = {l.account_code for l in lines}
    assert '131' in account_codes  # AR
    assert '5111' in account_codes  # Revenue
    assert '33311' in account_codes  # VAT output

    # Check N131 = 1.1M
    ar_line = lines.get(account_code='131')
    assert ar_line.debit_vnd == Decimal('1100000')


def test_invoice_with_multiple_lines(setup):
    company, customer, product = setup
    service = SalesInvoiceService(company=company)

    invoice = service.create({
        'invoice_no': 'BC0002',
        'invoice_date': date(2026, 6, 15),
        'customer_id': customer.id,
        'lines': [
            {'product_id': product.id, 'quantity': Decimal('5'),
             'unit_price': Decimal('100000'), 'vat_rate': Decimal('0.10')},
            {'product_id': product.id, 'quantity': Decimal('2'),
             'unit_price': Decimal('200000'), 'vat_rate': Decimal('0.10')},
        ],
        'post': True,
    })

    # 5*100k + 2*200k = 500k + 400k = 900k revenue, 90k VAT, total 990k
    assert invoice.subtotal == Decimal('900000')
    assert invoice.vat_amount == Decimal('90000')
    assert invoice.total_amount == Decimal('990000')


def test_invoice_unpost_reverts_voucher(setup):
    company, customer, product = setup
    service = SalesInvoiceService(company=company)

    invoice = service.create({
        'invoice_no': 'BC0003',
        'invoice_date': date(2026, 6, 15),
        'customer_id': customer.id,
        'lines': [
            {'product_id': product.id, 'quantity': Decimal('1'),
             'unit_price': Decimal('100000'), 'vat_rate': Decimal('0.10')},
        ],
        'post': True,
    })
    voucher = AccountingVoucher.objects.get(source_reference_id=invoice.id)
    assert voucher.is_posted

    service.unpost(invoice)
    voucher.refresh_from_db()
    assert not voucher.is_posted
