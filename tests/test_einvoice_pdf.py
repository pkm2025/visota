"""Tests for EInvoice PDF generation."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.einvoice.models import EInvoice
from apps.einvoice.services.einvoice_pdf_service import EInvoicePDFService, EInvoicePDFError
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine

User = get_user_model()


# ponytail: fixtures copied verbatim from tests/test_einvoice.py — pytest only
# shares fixtures via conftest.py, and these were file-local. Move to conftest
# if a third einvoice test file appears.


@pytest.fixture
def customer(db, company):
    return Customer.objects.create(
        company=company, code="CUST001",
        name="Test Customer", tax_code="0109876543",
        address="123 Test St",
    )


@pytest.fixture
def product(db, company):
    return Product.objects.create(
        company=company, code="PROD001", name="Test Product",
        default_unit_price=Decimal("1000000"),
        product_type="goods", unit_id="cai",
        default_vat_rate=Decimal("10"),
    )


@pytest.fixture
def sales_invoice(db, company, customer, product):
    si = SalesInvoice.objects.create(
        company=company, invoice_no="SI-001", invoice_date="2026-06-23",
        customer=customer, currency_code="VND", exchange_rate=Decimal("1"),
        subtotal=Decimal("1000000"), vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"), status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si, line_no=1, product=product, description="Test",
        quantity=Decimal("1"), unit_id="cai", unit_price=Decimal("1000000"),
        amount_before_vat=Decimal("1000000"), vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"), amount=Decimal("1100000"),
    )
    return si


@pytest.fixture
def einvoice_for_pdf(db, company, sales_invoice):
    """Build a fully-populated published EInvoice for PDF tests."""
    # EInvoiceConfig omitted — model has no FK to it; smoke test doesn't need it.
    ei = EInvoice.objects.create(
        company=company,
        sales_invoice=sales_invoice,
        pattern="1C26T",
        serial="AA/26E",
        invoice_no="AA/26E-0000001",
        status="issued",
        buyer_name=sales_invoice.customer.name,
        buyer_tax_code=sales_invoice.customer.tax_code,
        buyer_address=sales_invoice.customer.address,
        subtotal=Decimal("1000000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"),
        total_in_words="Một triệu một trăm ngàn đồng",
        issue_date="2026-06-29T10:00:00Z",
    )
    return ei


def test_generate_pdf_returns_bytes_starting_with_pdf_magic(einvoice_for_pdf):
    """generate_pdf returns bytes starting with %PDF."""
    pdf_bytes = EInvoicePDFService().generate_pdf(einvoice_for_pdf)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_get_or_generate_caches_to_pdf_file(einvoice_for_pdf):
    """First call generates + saves to pdf_file."""
    service = EInvoicePDFService()
    assert not einvoice_for_pdf.pdf_file  # empty initially

    pdf_bytes = service.get_or_generate(einvoice_for_pdf)

    assert isinstance(pdf_bytes, bytes)
    einvoice_for_pdf.refresh_from_db()
    assert einvoice_for_pdf.pdf_file.name  # saved
    assert einvoice_for_pdf.pdf_file.size > 1000


def test_get_or_generate_returns_cache_when_exists(einvoice_for_pdf):
    """If pdf_file already populated, return cached bytes without regenerating."""
    from django.core.files.base import ContentFile
    einvoice_for_pdf.pdf_file.save(
        "cached.pdf", ContentFile(b"%PDF-1.4 cached content"), save=True
    )
    einvoice_for_pdf.refresh_from_db()

    pdf_bytes = EInvoicePDFService().get_or_generate(einvoice_for_pdf)

    assert pdf_bytes == b"%PDF-1.4 cached content"


def test_get_or_generate_force_regenerates(einvoice_for_pdf):
    """force=True regenerates even if cache exists."""
    from django.core.files.base import ContentFile
    einvoice_for_pdf.pdf_file.save(
        "cached.pdf", ContentFile(b"%PDF-1.4 old"), save=True
    )

    pdf_bytes = EInvoicePDFService().get_or_generate(einvoice_for_pdf, force=True)

    assert pdf_bytes != b"%PDF-1.4 old"
    assert pdf_bytes.startswith(b"%PDF")


# --- View tests (Task 4) ---
# ponytail: brief said `request.user.company` but User model has no company FK;
# codebase uses session-driven `request.current_company`. Test sets
# session["current_company_id"] to drive scoping; view mirrors EInvoiceListView.

from django.test import Client
from django.urls import reverse


@pytest.fixture
def admin_user(db, company):
    """Superuser whose default company matches the einvoice's company."""
    User = get_user_model()
    u = User.objects.create_superuser(
        username="pdf_admin", password="Secret123!", email="p@test.local"
    )
    return u


@pytest.fixture
def auth_client(admin_user, company):
    c = Client()
    c.force_login(admin_user)
    # Bind the session's current company to the einvoice's company
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


def test_pdf_view_returns_pdf_content_type(auth_client, einvoice_for_pdf):
    """GET /pdf/ returns 200 + application/pdf."""
    url = reverse("ui_modern:einvoice_download_pdf", kwargs={"pk": einvoice_for_pdf.pk})
    response = auth_client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_pdf_view_requires_login(einvoice_for_pdf):
    """Anonymous user → redirect to login."""
    url = reverse("ui_modern:einvoice_download_pdf", kwargs={"pk": einvoice_for_pdf.pk})
    response = Client().get(url)
    assert response.status_code in (302, 403)


def test_pdf_view_force_query_regenerates(auth_client, einvoice_for_pdf):
    """?force=1 regenerates."""
    url = reverse("ui_modern:einvoice_download_pdf", kwargs={"pk": einvoice_for_pdf.pk})
    auth_client.get(url)  # populate cache
    response = auth_client.get(url + "?force=1")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_pdf_view_404_other_company(admin_user, einvoice_for_pdf, db):
    """current_company pointing elsewhere → 404 (company scoping)."""
    from apps.core.models import Company

    other_company = Company.objects.create(
        code="OTHER",
        name="Other Co",
        tax_code="9999999999",
        accounting_regime="tt133",
    )

    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = other_company.id
    session.save()

    url = reverse("ui_modern:einvoice_download_pdf", kwargs={"pk": einvoice_for_pdf.pk})
    response = c.get(url)
    assert response.status_code == 404


def test_publish_auto_generates_pdf(company, customer, product, sales_invoice):
    """After EInvoiceService.publish, pdf_file should be populated (best-effort)."""
    from apps.einvoice.services import EInvoiceService

    ei = EInvoice.objects.create(
        company=company, sales_invoice=sales_invoice,
        pattern="1C26T", serial="AA/26E",
        status=EInvoice.Status.DRAFT,
        subtotal=Decimal("1000000"), vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"), total_amount=Decimal("1100000"),
    )
    assert not ei.pdf_file

    EInvoiceService.publish(ei, invoice_no="AA/26E-0000002")
    ei.refresh_from_db()

    assert ei.status == EInvoice.Status.ISSUED
    assert ei.invoice_no == "AA/26E-0000002"
    assert ei.pdf_file.name  # auto-gen populated
    assert ei.pdf_file.size > 1000
