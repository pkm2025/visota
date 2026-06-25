"""Tests for e-invoice module: issue from sales, publish, cancel, BC01."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Company
from apps.einvoice.models import (
    EInvoice,
    EInvoiceConfig,
    EInvoiceProvider,
    EInvoiceReportBatch,
)
from apps.einvoice.services import (
    EInvoiceIssueError,
    EInvoiceReportService,
    EInvoiceService,
    amount_in_words,
)
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine
from apps.notifications.models import Notification

User = get_user_model()


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TESTEINV", name="Test EInvoice Co", tax_code="0101234567",
    )


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
def admin(db, company):
    return User.objects.create_superuser(
        username="admin", password="Secret123!", email="admin@test.local"
    )


# ---------- amount_in_words ----------

def test_amount_in_words_zero():
    assert "Không" in amount_in_words(Decimal("0"))


def test_amount_in_words_simple():
    s = amount_in_words(Decimal("1000"))
    assert "một nghìn" in s.lower()


def test_amount_in_words_million():
    s = amount_in_words(Decimal("1000000"))
    assert "triệu" in s.lower()


# ---------- Config ----------

@pytest.mark.django_db
def test_get_config_auto_creates(company):
    config = EInvoiceService.get_config(company)
    assert config.pk is not None
    assert config.provider == EInvoiceProvider.MANUAL


@pytest.mark.django_db
def test_get_config_returns_existing(company):
    EInvoiceConfig.objects.create(company=company, provider=EInvoiceProvider.MISA)
    config = EInvoiceService.get_config(company)
    assert config.provider == EInvoiceProvider.MISA


# ---------- Issue from sales ----------

@pytest.mark.django_db
def test_issue_from_sales_creates_draft(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    assert ei.status == EInvoice.Status.DRAFT
    assert ei.sales_invoice == sales_invoice
    assert ei.buyer_name == customer.name
    assert ei.buyer_tax_code == customer.tax_code
    assert ei.seller_name == company.name
    assert ei.seller_tax_code == company.tax_code
    assert ei.subtotal == Decimal("1000000")
    assert ei.vat_amount == Decimal("100000")
    assert ei.total_amount == Decimal("1100000")
    assert ei.issued_by == admin


@pytest.mark.django_db
def test_issue_from_sales_generates_xml_file(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    assert ei.xml_file.name.endswith(".xml")
    assert ei.xml_file.size > 500  # has content
    content = ei.xml_file.read().decode("utf-8")
    assert "<Invoice>" in content
    assert customer.name in content
    assert company.name in content


@pytest.mark.django_db
def test_issue_from_sales_generates_json_file(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    assert ei.json_file.name.endswith(".json")
    import json
    data = json.loads(ei.json_file.read())
    assert data["seller"]["name"] == company.name
    assert data["buyer"]["name"] == customer.name
    assert data["summary"]["totalAmount"] == 1100000.0


@pytest.mark.django_db
def test_issue_from_sales_includes_line_items(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    import json
    data = json.loads(ei.json_file.read())
    assert len(data["items"]) == 1
    assert data["items"][0]["itemName"] == "Test"


# ---------- Publish ----------

@pytest.mark.django_db
def test_publish_manual_mode_assigns_number(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei)
    ei.refresh_from_db()
    assert ei.status == EInvoice.Status.ISSUED
    assert ei.invoice_no != ""
    assert ei.issue_date is not None
    assert ei.provider_response["mode"] == "manual"


@pytest.mark.django_db
def test_publish_with_explicit_number(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei, invoice_no="AA-001")
    ei.refresh_from_db()
    assert ei.invoice_no == "AA-001"


@pytest.mark.django_db
def test_publish_fires_notification(company, db):
    """publish() should notify superusers."""
    from apps.sales.services.invoice_service import SalesInvoiceService

    company = Company.objects.create(code="TESTPUB", name="Pub Co", tax_code="0109999999")
    User.objects.create_superuser(
        username="admintest", password="Secret123!", email="admin3@test.local"
    )
    cust = Customer.objects.create(company=company, code="C1", name="C1")
    prod = Product.objects.create(
        company=company, code="P1", name="P1",
        default_unit_price=Decimal("100"), product_type="goods",
    )
    si = SalesInvoice.objects.create(
        company=company, invoice_no="SI-X", invoice_date="2026-06-23",
        customer=cust, currency_code="VND", exchange_rate=Decimal("1"),
        subtotal=Decimal("100"), vat_amount=Decimal("0"),
        total_amount=Decimal("100"), status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si, line_no=1, product=prod, description="x",
        quantity=Decimal("1"), unit_id="cai", unit_price=Decimal("100"),
        amount_before_vat=Decimal("100"), vat_rate=Decimal("0"),
        vat_amount=Decimal("0"), amount=Decimal("100"),
    )
    ei = EInvoiceService.issue_from_sales_invoice(si)
    EInvoiceService.publish(ei)
    assert Notification.objects.filter(type="success").count() >= 1


# ---------- Cancel ----------

@pytest.mark.django_db
def test_cancel_marks_cancelled(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei)
    EInvoiceService.cancel(ei, reason="Sai tên KH")
    ei.refresh_from_db()
    assert ei.status == EInvoice.Status.CANCELLED
    assert "Sai tên KH" in ei.error_message


# ---------- Adjust ----------

@pytest.mark.django_db
def test_adjust_creates_negative_invoice(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei)
    adjusted = EInvoiceService.adjust(ei, reason="Sai số lượng")
    assert adjusted.replaces_invoice == ei
    assert adjusted.adjustment_type == "adjust"
    assert adjusted.subtotal == -ei.subtotal
    assert adjusted.total_amount == -ei.total_amount
    assert "Điều chỉnh" in adjusted.note


# ---------- BC01 Report ----------

@pytest.mark.django_db
def test_generate_bc01_returns_batch(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei)
    batch = EInvoiceReportService.generate_bc01(
        company, month=6, year=2026, submitted_by=admin
    )
    assert batch.report_type == "bc01"
    assert batch.invoice_count == 1
    assert batch.total_amount == ei.total_amount
    assert batch.xml_file.name.endswith(".xml")
    content = batch.xml_file.read().decode("utf-8")
    assert "<BC01>" in content
    assert ei.invoice_no in content


@pytest.mark.django_db
def test_generate_bc01_includes_only_issued(company, customer, product, sales_invoice, admin):
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    # Don't publish — should not be in BC01
    batch = EInvoiceReportService.generate_bc01(company, 6, 2026)
    assert batch.invoice_count == 0
