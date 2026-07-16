import pytest
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company
from decimal import Decimal
from datetime import date


@pytest.fixture
def auth_client_with_voucher(db):
    company = Company.objects.create(code='TCO', name='Test')
    user = User.objects.create_superuser(username='alice', password='Secret123', email='alice@test.local')
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000'))
    client = Client()
    client.force_login(user)
    session = client.session
    session['current_company_id'] = company.id
    session.save()
    return client, v


def test_print_voucher_endpoint(auth_client_with_voucher):
    client, voucher = auth_client_with_voucher
    response = client.get(f'/modern/vouchers/{voucher.id}/print/')
    assert response.status_code == 200
    # Should return PDF or HTML
    assert len(response.content) > 100


def test_upload_scan_endpoint(auth_client_with_voucher):
    client, voucher = auth_client_with_voucher
    fake_pdf = SimpleUploadedFile('scan.pdf', b'%PDF test', content_type='application/pdf')
    response = client.post(f'/modern/vouchers/{voucher.id}/upload/', {
        'title': 'Scan phiếu đã ký',
        'file': fake_pdf,
    })
    assert response.status_code == 302  # redirect back to detail


def test_document_download(auth_client_with_voucher):
    client, voucher = auth_client_with_voucher
    # First upload a document
    from apps.documents.services import DocumentService
    fake = SimpleUploadedFile('test.pdf', b'%PDF', content_type='application/pdf')
    doc = DocumentService(company=voucher.company).upload(
        voucher=voucher, title='Test', file=fake,
    )
    response = client.get(f'/modern/documents/{doc.id}/download/')
    assert response.status_code == 200


def test_document_delete(auth_client_with_voucher):
    client, voucher = auth_client_with_voucher
    from apps.documents.services import DocumentService
    fake = SimpleUploadedFile('del.pdf', b'%PDF', content_type='application/pdf')
    doc = DocumentService(company=voucher.company).upload(
        voucher=voucher, title='Delete me', file=fake,
    )
    doc_id = doc.id
    # Sanity: confirm doc is in the same company as the session.
    assert doc.company_id == voucher.company_id
    response = client.post(f'/modern/documents/{doc_id}/delete/')
    assert response.status_code == 302
    from apps.documents.models import VoucherDocument
    assert not VoucherDocument.objects.filter(id=doc_id).exists()
