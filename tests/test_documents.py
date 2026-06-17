import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.documents.models import VoucherDocument
from apps.documents.services import DocumentService
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company
from decimal import Decimal
from datetime import date


@pytest.fixture
def voucher(db):
    company = Company.objects.create(code='TCO', name='Test')
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15), description='Test',
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000'))
    return v


def test_document_upload_scan(voucher):
    """Upload a scanned file linked to a voucher."""
    company = voucher.company
    fake_pdf = SimpleUploadedFile('scan.pdf', b'%PDF fake content', content_type='application/pdf')
    doc = VoucherDocument.objects.create(
        company=company, voucher=voucher,
        document_type='scanned_upload',
        title='Scan phiếu BC0001 đã ký',
        file=fake_pdf,
        status='scanned',
    )
    assert doc.pk is not None
    assert doc.file_size > 0
    assert doc.voucher.voucher_no == 'BC0001'


def test_document_print_generated(voucher):
    """A print-generated document (PDF from system)."""
    doc = VoucherDocument.objects.create(
        company=voucher.company, voucher=voucher,
        document_type='print_template',
        title='Phiếu kế toán BC0001 (in hệ thống)',
        file=SimpleUploadedFile('print.pdf', b'%PDF print', content_type='application/pdf'),
        status='printed',
    )
    assert doc.document_type == 'print_template'
    assert doc.status == 'printed'


def test_document_list_by_voucher(voucher):
    """Can query all documents for a voucher."""
    for i in range(3):
        VoucherDocument.objects.create(
            company=voucher.company, voucher=voucher,
            document_type='scanned_upload', title=f'Scan {i}',
            file=SimpleUploadedFile(f's{i}.pdf', b'x', content_type='application/pdf'),
        )
    docs = VoucherDocument.objects.filter(voucher=voucher)
    assert docs.count() == 3


def test_document_service_upload(voucher):
    """DocumentService.upload() handles file creation."""
    service = DocumentService(company=voucher.company)
    fake_pdf = SimpleUploadedFile('receipt.jpg', b'fake image', content_type='image/jpeg')
    doc = service.upload(
        voucher=voucher,
        title='Hóa đơn scan',
        file=fake_pdf,
        document_type='scanned_upload',
    )
    assert doc.pk is not None
    assert doc.status == 'scanned'
