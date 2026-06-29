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
        status="published",
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
