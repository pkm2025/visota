import pytest
from decimal import Decimal
from datetime import date
from apps.documents.services import PrintService
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company


@pytest.fixture
def voucher(db):
    company = Company.objects.create(
        code='TCO', name='CÔNG TY TEST',
        address='123 Đường A, Hà Nội', tax_code='0101234567',
    )
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), description='Bán hàng test',
        total_vnd=Decimal('1100000'),
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1100000'), description='Tiền mặt')
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000000'), description='Doanh thu')
    VoucherLine.objects.create(voucher=v, line_no=3, account_code='33311', credit_vnd=Decimal('100000'), description='VAT')
    return v


def test_print_generates_pdf(voucher):
    """PrintService.generate_pdf() returns PDF bytes (or HTML fallback)."""
    service = PrintService(company=voucher.company)
    pdf_bytes = service.generate_voucher_pdf(voucher)

    assert pdf_bytes is not None
    assert len(pdf_bytes) > 100  # non-trivial output
    # WeasyPrint is installed in this env, so should produce PDF magic header
    assert pdf_bytes[:4] == b'%PDF'  # PDF magic header


def test_print_creates_document_record(voucher):
    """PrintService saves a VoucherDocument linked to the voucher."""
    from apps.documents.models import VoucherDocument
    service = PrintService(company=voucher.company)
    doc = service.generate_and_save(voucher)

    assert doc.pk is not None
    assert doc.voucher == voucher
    assert doc.document_type == 'print_template'
    assert doc.status == 'printed'
    assert doc.file is not None


def test_print_pdf_contains_voucher_data(voucher):
    """PDF should be non-trivial size with voucher data rendered."""
    service = PrintService(company=voucher.company)
    pdf_bytes = service.generate_voucher_pdf(voucher)
    # Can't easily parse PDF text, but at least verify it generated substantial output
    assert len(pdf_bytes) > 500
