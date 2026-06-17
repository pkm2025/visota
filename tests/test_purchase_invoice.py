import pytest
from decimal import Decimal
from datetime import date
from apps.purchasing.models import PurchaseInvoice, PurchaseInvoiceLine
from apps.purchasing.services import PurchaseInvoiceService
from apps.master_data.models import Vendor, Product
from apps.ledger.models import AccountingVoucher
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    vendor = Vendor.objects.create(company=company, code='NCC001', name='XYZ')
    product = Product.objects.create(
        company=company, code='SP001', name='Pin',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    return company, vendor, product


def test_purchase_invoice_generates_voucher(setup):
    company, vendor, product = setup
    service = PurchaseInvoiceService(company=company)

    invoice = service.create({
        'invoice_no': 'PN0001',
        'invoice_date': date(2026, 6, 15),
        'vendor_id': vendor.id,
        'lines': [
            {'product_id': product.id, 'quantity': Decimal('10'),
             'unit_price': Decimal('100000'), 'vat_rate': Decimal('0.10')},
        ],
        'post': True,
    })

    assert invoice.total_amount == Decimal('1100000')

    voucher = AccountingVoucher.objects.get(source_reference_id=invoice.id)
    assert voucher.voucher_type == 'purchase_invoice'
    assert voucher.is_posted

    lines = voucher.lines.all()
    account_codes = {l.account_code for l in lines}
    assert '156' in account_codes  # Inventory debit
    assert '1331' in account_codes  # VAT input debit
    assert '331' in account_codes  # AP credit

    # C331 = 1.1M (full AP)
    ap_line = lines.get(account_code='331', object_type='vendor')
    assert ap_line.credit_vnd == Decimal('1100000')


def test_purchase_invoice_unpost(setup):
    company, vendor, product = setup
    service = PurchaseInvoiceService(company=company)
    invoice = service.create({
        'invoice_no': 'PN0002',
        'invoice_date': date(2026, 6, 15),
        'vendor_id': vendor.id,
        'lines': [
            {'product_id': product.id, 'quantity': Decimal('1'),
             'unit_price': Decimal('100000'), 'vat_rate': Decimal('0.10')},
        ],
        'post': True,
    })
    service.unpost(invoice)
    invoice.refresh_from_db()
    assert invoice.status == 0
