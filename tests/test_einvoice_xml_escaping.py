"""Tests for e-invoice XML escaping (VAL-API-002).

Verifies that the _build_xml method (and BC01 generator) properly escapes
special characters (<, >, &, ", ') when generating XML, preventing
XML injection attacks from buyer/seller name, address, or line description
fields.
"""

from datetime import datetime
from decimal import Decimal
from xml.etree.ElementTree import fromstring, parse

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Company
from apps.einvoice.services import EInvoiceReportService, EInvoiceService
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine

User = get_user_model()


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="XMLTEST",
        name='XML & <Co> "Quote"',
        tax_code="0101234567",
        address='1 <St> & "Sons"',
    )


@pytest.fixture
def customer(db, company):
    return Customer.objects.create(
        company=company,
        code="CUST-XML",
        name='<Customer> & "Friends"',
        tax_code="0109876543",
        address="<123 Addr> & 'Apt'",
    )


@pytest.fixture
def product(db, company):
    return Product.objects.create(
        company=company,
        code="PROD-XML",
        name="XML Product",
        default_unit_price=Decimal("1000000"),
        product_type="goods",
        unit_id="cai",
        default_vat_rate=Decimal("10"),
    )


@pytest.fixture
def sales_invoice(db, company, customer, product):
    si = SalesInvoice.objects.create(
        company=company,
        invoice_no="SI-XML-001",
        invoice_date="2026-06-23",
        customer=customer,
        currency_code="VND",
        exchange_rate=Decimal("1"),
        subtotal=Decimal("1000000"),
        vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"),
        status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si,
        line_no=1,
        product=product,
        description="<Line> & \"desc\" with 'apos'",
        quantity=Decimal("1"),
        unit_id="cai",
        unit_price=Decimal("1000000"),
        amount_before_vat=Decimal("1000000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"),
        amount=Decimal("1100000"),
    )
    return si


@pytest.fixture
def admin(db, company):
    return User.objects.create_superuser(
        username="xmladmin", password="Secret123!", email="xml@test.local"
    )


# ---------- _build_xml direct escaping ----------


@pytest.mark.django_db
def test_build_xml_escapes_special_chars(company, customer, product, sales_invoice, admin):
    """VAL-API-002: _build_xml output properly escapes <, >, &, ", '."""
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)

    # Read the generated XML
    xml_content = ei.xml_file.read().decode("utf-8")

    # Must be parseable as valid XML (would fail if injection broke structure)
    parsed = fromstring(xml_content)
    assert parsed.tag == "Invoice"

    # The raw special characters must NOT appear unescaped in dangerous positions.
    # Specifically, the raw buyer name with < > should not appear verbatim.
    assert '<Customer> & "Friends"' not in xml_content, (
        "Buyer name appears unescaped - XML injection risk"
    )
    # The escaped form should be present
    assert "&lt;Customer&gt;" in xml_content or "&lt;Customer&gt;" in xml_content

    # And the address with 'apos' quote should be escaped
    assert "&lt;123 Addr&gt;" in xml_content


@pytest.mark.django_db
def test_build_xml_is_well_formed(company, customer, product, sales_invoice, admin):
    """XML output must be well-formed even with special characters."""
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    xml_content = ei.xml_file.read().decode("utf-8")

    # parse() raises ParseError if the XML is malformed
    from io import BytesIO

    tree = parse(BytesIO(xml_content.encode("utf-8")))
    root = tree.getroot()
    assert root.tag == "Invoice"

    # Verify the buyer name was preserved (decoded) as the original
    buyer_name_el = root.find(".//Buyer/Name")
    assert buyer_name_el is not None
    assert buyer_name_el.text == '<Customer> & "Friends"'


@pytest.mark.django_db
def test_build_xml_escapes_line_description(company, customer, product, sales_invoice, admin):
    """Line item descriptions with special chars must be escaped."""
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    xml_content = ei.xml_file.read().decode("utf-8")

    from io import BytesIO

    tree = parse(BytesIO(xml_content.encode("utf-8")))
    item_name_el = tree.find(".//Item/ItemName")
    assert item_name_el is not None
    # The text must equal the original description (decoded by parser)
    assert item_name_el.text == "<Line> & \"desc\" with 'apos'"


@pytest.mark.django_db
def test_build_xml_escapes_seller_address(company, customer, product, sales_invoice, admin):
    """Seller address with special chars must be escaped."""
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    xml_content = ei.xml_file.read().decode("utf-8")

    from io import BytesIO

    tree = parse(BytesIO(xml_content.encode("utf-8")))
    seller_addr_el = tree.find(".//Seller/Address")
    assert seller_addr_el is not None
    assert seller_addr_el.text == '1 <St> & "Sons"'


# ---------- BC01 XML escaping ----------


@pytest.mark.django_db
def test_bc01_xml_escapes_special_chars(company, customer, product, sales_invoice, admin):
    """BC01 report XML must also escape special characters."""
    ei = EInvoiceService.issue_from_sales_invoice(sales_invoice, issued_by=admin)
    EInvoiceService.publish(ei)
    # Force the issue date into the BC01 period
    ei.issue_date = timezone.make_aware(datetime(2026, 6, 23))
    ei.save()

    batch = EInvoiceReportService.generate_bc01(company, month=6, year=2026, submitted_by=admin)
    xml_content = batch.xml_file.read().decode("utf-8")

    # Must parse as well-formed XML
    from io import BytesIO

    tree = parse(BytesIO(xml_content.encode("utf-8")))
    assert tree.getroot().tag == "BC01"

    # Company name with special chars must be escaped
    company_name_el = tree.find(".//Company/Name")
    assert company_name_el is not None
    assert company_name_el.text == 'XML & <Co> "Quote"'

    # Buyer name must be escaped
    buyer_name_el = tree.find(".//Invoice/BuyerName")
    assert buyer_name_el is not None
    assert buyer_name_el.text == '<Customer> & "Friends"'
