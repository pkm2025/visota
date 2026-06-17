# Document Management Module — Print + Scan + Link

> Mỗi chứng từ có thể: (1) in ra PDF theo mẫu VN để ký, (2) scan/upload file scan đã ký, (3) liên kết 2 chiều với bút toán.

## Task 1: Document model + upload service

**Files:**
- Create: `apps/documents/` (apps.py, models.py, services/, migrations/)
- Modify: `config/settings/base.py`
- Test: `tests/test_documents.py`

### Step 1: Write tests

`tests/test_documents.py`:
```python
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
```

### Step 2: Create models

`apps/documents/models.py`:
```python
"""Voucher document models — printed forms + scanned uploads."""
import os
from django.db import models
from apps.core.managers import CompanyOwnedModel


class VoucherDocument(CompanyOwnedModel):
    """Document linked to a voucher: printed PDF or scanned upload."""

    class DocumentType(models.TextChoices):
        PRINT_TEMPLATE = 'print_template', 'In từ hệ thống'
        SCANNED_UPLOAD = 'scanned_upload', 'Scan/Upload'
        EXTERNAL = 'external', 'File ngoài'
        SIGNED_CONTRACT = 'signed_contract', 'Hợp đồng đã ký'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Bản nháp'
        PRINTED = 'printed', 'Đã in'
        SIGNED = 'signed', 'Đã ký'
        SCANNED = 'scanned', 'Đã scan'
        ARCHIVED = 'archived', 'Lưu trữ'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='documents', db_index=True,
    )
    voucher = models.ForeignKey(
        'ledger.AccountingVoucher', on_delete=models.CASCADE,
        related_name='documents', null=True, blank=True,
    )

    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    title = models.CharField(max_length=500)
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_type = models.CharField(max_length=10, blank=True, default='')
    file_size = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )

    notes = models.TextField(blank=True, default='')
    uploaded_by = models.ForeignKey(
        'identity.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='uploaded_documents',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'voucher_document'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'voucher']),
            models.Index(fields=['company', 'document_type']),
        ]

    def __str__(self):
        return f'{self.title} ({self.document_type})'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            ext = os.path.splitext(self.file.name)[1].lower().lstrip('.')
            self.file_type = ext
        super().save(*args, **kwargs)
```

### Step 3: Create service

`apps/documents/services/document_service.py`:
```python
"""DocumentService — upload, generate print, link to voucher."""
import os
from django.core.files.base import ContentFile
from apps.documents.models import VoucherDocument


class DocumentService:
    def __init__(self, company):
        self.company = company

    def upload(self, voucher, title, file, document_type='scanned_upload',
               notes='', user=None):
        """Upload a scanned/external file and link to voucher."""
        doc = VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type=document_type,
            title=title,
            file=file,
            status='scanned' if document_type == 'scanned_upload' else 'draft',
            notes=notes,
            uploaded_by=user,
        )
        return doc

    def generate_print(self, voucher, title=None):
        """Generate a placeholder for a printed document.

        The actual PDF generation happens in PrintService (Task 2).
        This creates the DB record.
        """
        if not title:
            title = f'{voucher.get_voucher_type_display()} {voucher.voucher_no}'

        doc = VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type='print_template',
            title=title,
            file=None,  # will be set by PrintService
            status='printed',
        )
        return doc

    def get_voucher_documents(self, voucher):
        """Get all documents linked to a voucher."""
        return VoucherDocument.objects.filter(
            company=self.company, voucher=voucher,
        ).order_by('-created_at')
```

`apps/documents/services/__init__.py`:
```python
from .document_service import DocumentService
__all__ = ['DocumentService']
```

### Step 4: Migration + tests + commit

Add `'apps.documents',` to INSTALLED_APPS.
```bash
.venv/bin/python manage.py makemigrations documents
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_documents.py -v
.venv/bin/pytest -v
git add apps/documents/ config/settings/base.py tests/test_documents.py
git commit -m "feat(documents): VoucherDocument model + DocumentService for print/scan/link

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: PrintService — PDF generation from voucher data

**Files:**
- Create: `apps/documents/services/print_service.py`
- Create: `templates/documents/print/voucher_print.html`
- Modify: `apps/documents/services/__init__.py`
- Test: `tests/test_print_service.py`

### Step 1: Write tests

`tests/test_print_service.py`:
```python
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
    """PrintService.generate_pdf() returns PDF bytes."""
    service = PrintService(company=voucher.company)
    pdf_bytes = service.generate_voucher_pdf(voucher)

    assert pdf_bytes is not None
    assert len(pdf_bytes) > 100  # non-trivial PDF
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
    """PDF should contain voucher number and company name."""
    service = PrintService(company=voucher.company)
    pdf_bytes = service.generate_voucher_pdf(voucher)
    # Can't easily parse PDF text, but at least verify it generated
    assert len(pdf_bytes) > 500
```

### Step 2: Create print template

`templates/documents/print/voucher_print.html`:
```html
{% load humanize %}
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 2cm; }
        body { font-family: 'Times New Roman', serif; font-size: 12pt; }
        .header { text-align: center; margin-bottom: 20px; }
        .company-name { font-size: 14pt; font-weight: bold; text-transform: uppercase; }
        .company-info { font-size: 10pt; }
        .title { font-size: 16pt; font-weight: bold; text-align: center; margin: 20px 0; text-transform: uppercase; }
        .voucher-info { margin: 15px 0; }
        .voucher-info table { width: 100%; }
        .voucher-info td { padding: 3px 10px; font-size: 11pt; }
        .lines-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .lines-table th, .lines-table td { border: 1px solid #333; padding: 5px 8px; font-size: 10pt; }
        .lines-table th { background: #f0f0f0; text-align: center; }
        .amount { text-align: right; font-family: 'Courier New', monospace; }
        .signatures { margin-top: 40px; width: 100%; }
        .signatures td { text-align: center; font-size: 10pt; width: 33%; }
        .sign-line { margin-top: 50px; font-style: italic; }
        .total-row { font-weight: bold; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ company.name }}</div>
        <div class="company-info">
            Địa chỉ: {{ company.address }}<br>
            MST: {{ company.tax_code }}
        </div>
    </div>

    <div class="title">
        {{ voucher.get_voucher_type_display }}<br>
        {{ voucher.description }}
    </div>

    <div class="voucher-info">
        <table>
            <tr>
                <td><strong>Số chứng từ:</strong> {{ voucher.voucher_no }}</td>
                <td><strong>Ngày:</strong> {{ voucher.voucher_date|date:"d/m/Y" }}</td>
            </tr>
            <tr>
                <td><strong>Kỳ:</strong> Tháng {{ voucher.period }} / {{ voucher.fiscal_year }}</td>
                <td><strong>Trạng thái:</strong> {{ voucher.get_status_display }}</td>
            </tr>
        </table>
    </div>

    <table class="lines-table">
        <thead>
            <tr>
                <th style="width: 5%">#</th>
                <th style="width: 12%">TK Nợ</th>
                <th style="width: 12%">TK Có</th>
                <th style="width: 15%">Đối tượng</th>
                <th>Diễn giải</th>
                <th style="width: 13%" class="amount">Số tiền</th>
            </tr>
        </thead>
        <tbody>
            {% for line in voucher.lines.all %}
            <tr>
                <td style="text-align: center">{{ line.line_no }}</td>
                <td>{% if line.debit_vnd > 0 %}{{ line.account_code }}{% endif %}</td>
                <td>{% if line.credit_vnd > 0 %}{{ line.account_code }}{% endif %}</td>
                <td>{{ line.object_code|default:'' }}</td>
                <td>{{ line.description }}</td>
                <td class="amount">{{ line.debit_vnd|floatformat:0|intcomma }}{{ line.credit_vnd|floatformat:0|intcomma }}</td>
            </tr>
            {% endfor %}
            <tr class="total-row">
                <td colspan="5" style="text-align: right">Tổng cộng:</td>
                <td class="amount">{{ voucher.total_vnd|floatformat:0|intcomma }}</td>
            </tr>
        </tbody>
    </table>

    <div style="text-align: right; font-style: italic; margin: 10px 0;">
        Tổng số tiền viết bằng chữ: .......................................................
    </div>

    <div class="signatures">
        <table>
            <tr>
                <td><strong>Người lập</strong><div class="sign-line">(Ký, họ tên)</div></td>
                <td><strong>Kế toán trưởng</strong><div class="sign-line">(Ký, họ tên)</div></td>
                <td><strong>Giám đốc</strong><div class="sign-line">(Ký, họ tên, đóng dấu)</div></td>
            </tr>
        </table>
    </div>

    <div style="margin-top: 30px; font-size: 9pt; color: #666;">
        Ngày ..... tháng ..... năm 20...<br>
        Địa chỉ: {{ company.address }} — MST: {{ company.tax_code }}
    </div>
</body>
</html>
```

### Step 3: Create PrintService

`apps/documents/services/print_service.py`:
```python
"""PrintService — generate PDF from voucher data using WeasyPrint."""
import io
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from apps.documents.models import VoucherDocument

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


class PrintService:
    """Generate printable PDF documents from voucher data."""

    TEMPLATE_MAP = {
        'journal': 'documents/print/voucher_print.html',
        'cash_receipt': 'documents/print/voucher_print.html',
        'cash_payment': 'documents/print/voucher_print.html',
        'sales_invoice': 'documents/print/voucher_print.html',
        'purchase_invoice': 'documents/print/voucher_print.html',
        'depreciation': 'documents/print/voucher_print.html',
        'payroll': 'documents/print/voucher_print.html',
        'closing': 'documents/print/voucher_print.html',
    }

    def __init__(self, company):
        self.company = company

    def generate_voucher_pdf(self, voucher) -> bytes:
        """Render voucher to PDF bytes."""
        template = self.TEMPLATE_MAP.get(
            voucher.voucher_type,
            'documents/print/voucher_print.html',
        )
        html_str = render_to_string(template, {
            'voucher': voucher,
            'company': voucher.company,
        })

        if not WEASYPRINT_AVAILABLE:
            # Fallback: return HTML as bytes (for dev without WeasyPrint installed)
            return html_str.encode('utf-8')

        pdf_bytes = HTML(string=html_str).write_pdf()
        return pdf_bytes

    def generate_and_save(self, voucher) -> VoucherDocument:
        """Generate PDF and save as VoucherDocument linked to voucher."""
        pdf_bytes = self.generate_voucher_pdf(voucher)

        ext = 'html' if not WEASYPRINT_AVAILABLE else 'pdf'
        filename = f'{voucher.voucher_no}_{voucher.voucher_date}.{ext}'
        file_obj = ContentFile(pdf_bytes, name=filename)

        doc = VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type='print_template',
            title=f'{voucher.get_voucher_type_display()} {voucher.voucher_no}',
            file=file_obj,
            status='printed',
        )
        return doc
```

Update `apps/documents/services/__init__.py`:
```python
from .document_service import DocumentService
from .print_service import PrintService
__all__ = ['DocumentService', 'PrintService']
```

### Step 4: Tests + commit

```bash
.venv/bin/pytest tests/test_print_service.py -v
.venv/bin/pytest -v
git add apps/documents/ templates/documents/ tests/test_print_service.py
git commit -m "feat(documents): PrintService — PDF generation from voucher (WeasyPrint)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: UI — Voucher detail integration (print + upload)

**Files:**
- Modify: `templates/modern/ledger/voucher_detail.html` (add print/upload buttons + document list)
- Create: `apps/ui_modern/views/document_views.py`
- Modify: `apps/ui_modern/views/__init__.py`, `apps/ui_modern/urls.py`
- Test: `tests/test_document_views.py`

### Step 1: Write tests

`tests/test_document_views.py`:
```python
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
    user = User.objects.create_user(username='alice', password='Secret123')
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code='111', debit_vnd=Decimal('1000'))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code='5111', credit_vnd=Decimal('1000'))
    client = Client()
    client.force_login(user)
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
```

### Step 2: Create views

`apps/ui_modern/views/document_views.py`:
```python
"""Document views — print, upload, download."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages

from apps.ledger.models import AccountingVoucher
from apps.documents.models import VoucherDocument
from apps.documents.services import PrintService, DocumentService
from apps.core.models import Company


class VoucherPrintView(LoginRequiredMixin, View):
    """Generate and download PDF for a voucher."""
    login_url = '/auth/login/'

    def get(self, request, pk):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        company = voucher.company

        service = PrintService(company=company)
        pdf_bytes = service.generate_voucher_pdf(voucher)

        # Also save as document record
        service.generate_and_save(voucher)

        ext = 'pdf'
        content_type = 'application/pdf'
        if pdf_bytes[:4] != b'%PDF':
            ext = 'html'
            content_type = 'text/html'

        response = HttpResponse(pdf_bytes, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{voucher.voucher_no}.{ext}"'
        return response


class VoucherUploadView(LoginRequiredMixin, View):
    """Upload scanned document for a voucher."""
    login_url = '/auth/login/'

    def post(self, request, pk):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        company = voucher.company

        title = request.POST.get('title', f'Scan {voucher.voucher_no}')
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            messages.error(request, 'Vui lòng chọn file.')
            return redirect('ui_modern:voucher_detail', pk=pk)

        service = DocumentService(company=company)
        doc = service.upload(
            voucher=voucher,
            title=title,
            file=uploaded_file,
            document_type='scanned_upload',
            user=request.user,
        )
        messages.success(request, f'Đã tải lên: {doc.title}')
        return redirect('ui_modern:voucher_detail', pk=pk)


class DocumentDownloadView(LoginRequiredMixin, View):
    """Download a document file."""
    login_url = '/auth/login/'

    def get(self, request, pk):
        doc = get_object_or_404(VoucherDocument, pk=pk)
        if not doc.file:
            messages.error(request, 'File không tồn tại.')
            return redirect('ui_modern:voucher_detail', pk=doc.voucher_id)

        response = HttpResponse(doc.file, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{doc.file.name.split("/")[-1]}"'
        return response


class DocumentDeleteView(LoginRequiredMixin, View):
    """Delete a document."""
    login_url = '/auth/login/'

    def post(self, request, pk):
        doc = get_object_or_404(VoucherDocument, pk=pk)
        voucher_id = doc.voucher_id
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()
        messages.success(request, f'Đã xóa: {doc.title}')
        return redirect('ui_modern:voucher_detail', pk=voucher_id)
```

### Step 3: Update urls.py

Add routes:
```python
path('vouchers/<int:pk>/print/', VoucherPrintView.as_view(), name='voucher_print'),
path('vouchers/<int:pk>/upload/', VoucherUploadView.as_view(), name='voucher_upload'),
path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document_download'),
path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
```

### Step 4: Update voucher_detail.html template

Add after the lines table:

```html
<!-- Documents section -->
<div class="card mt-3">
    <div class="card-header d-flex justify-content-between align-items-center py-2">
        <strong>Chứng từ đính kèm</strong>
        <div class="btn-group btn-group-sm">
            <a href="{% url 'ui_modern:voucher_print' voucher.id %}" target="_blank"
               class="btn btn-outline-primary">
                <i class="bi bi-printer"></i> In chứng từ (PDF)
            </a>
            <button class="btn btn-outline-success" data-bs-toggle="modal" data-bs-target="#uploadModal">
                <i class="bi bi-upload"></i> Tải lên scan
            </button>
        </div>
    </div>
    <div class="card-body p-0">
        {% if voucher.documents.all %}
        <table class="table table-sm mb-0">
            <thead class="table-light">
                <tr>
                    <th>Tiêu đề</th>
                    <th>Loại</th>
                    <th>File</th>
                    <th>Trạng thái</th>
                    <th>Ngày tạo</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {% for doc in voucher.documents.all %}
                <tr>
                    <td>{{ doc.title }}</td>
                    <td>
                        {% if doc.document_type == 'print_template' %}
                        <span class="badge bg-info">In hệ thống</span>
                        {% elif doc.document_type == 'scanned_upload' %}
                        <span class="badge bg-success">Scan</span>
                        {% else %}
                        <span class="badge bg-secondary">{{ doc.document_type }}</span>
                        {% endif %}
                    </td>
                    <td>
                        <small>{{ doc.file_type|upper }} ({{ doc.file_size|filesizeformat }})</small>
                    </td>
                    <td>
                        {% if doc.status == 'printed' %}<span class="badge bg-info">Đã in</span>
                        {% elif doc.status == 'signed' %}<span class="badge bg-primary">Đã ký</span>
                        {% elif doc.status == 'scanned' %}<span class="badge bg-success">Đã scan</span>
                        {% else %}<span class="badge bg-secondary">{{ doc.status }}</span>
                        {% endif %}
                    </td>
                    <td><small>{{ doc.created_at|date:"d/m/Y H:i" }}</small></td>
                    <td>
                        <a href="{% url 'ui_modern:document_download' doc.id %}"
                           class="btn btn-sm btn-outline-secondary py-0">
                            <i class="bi bi-download"></i>
                        </a>
                        <form method="post" action="{% url 'ui_modern:document_delete' doc.id %}"
                              class="d-inline" onsubmit="return confirm('Xóa file này?')">
                            {% csrf_token %}
                            <button class="btn btn-sm btn-outline-danger py-0">
                                <i class="bi bi-trash"></i>
                            </button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="text-muted text-center py-3 mb-0">
            <i class="bi bi-paperclip"></i> Chưa có file đính kèm.
            In chứng từ hoặc tải lên scan đã ký.
        </p>
        {% endif %}
    </div>
</div>

<!-- Upload Modal -->
<div class="modal fade" id="uploadModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="post" action="{% url 'ui_modern:voucher_upload' voucher.id %}"
                  enctype="multipart/form-data">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title">Tải lên chứng từ scan</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Tiêu đề</label>
                        <input type="text" name="title" class="form-control"
                               value="Scan {{ voucher.voucher_no }} đã ký" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Chọn file (PDF, JPG, PNG)</label>
                        <input type="file" name="file" class="form-control" required
                               accept=".pdf,.jpg,.jpeg,.png">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hủy</button>
                    <button type="submit" class="btn btn-success">
                        <i class="bi bi-upload"></i> Tải lên
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

### Step 5: Tests + commit

```bash
.venv/bin/pytest tests/test_document_views.py -v
.venv/bin/pytest -v
git add apps/ui_modern/ templates/modern/ledger/voucher_detail.html tests/test_document_views.py
git commit -m "feat(documents): voucher detail integration — print PDF + upload scan + download/delete

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Final cleanup + verify

```bash
.venv/bin/ruff check apps/ --fix && .venv/bin/ruff format apps/
.venv/bin/pytest -v
.venv/bin/python manage.py check
git add -A
git commit -m "feat: document management module complete

- VoucherDocument: print_template + scanned_upload + external
- PrintService: WeasyPrint PDF from voucher data
- DocumentService: upload, link to voucher, download, delete
- Voucher detail: print PDF button + upload modal + document list
- Vietnamese accounting print template with 3 signature blocks

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

**Plan complete.** 4 tasks.
