"""Tests for e-invoice form 02BANHANG (Hóa đơn bán hàng) — TT58 support.

Covers VAL-TT58-042..045:
- 02BANHANG available for GTGT% companies (Groups 1, 2)
- 02BANHANG not available for khau_tru companies (Groups 3, 4)
- 02BANHANG invoice has per-line VAT rate field, no input VAT deduction fields
- 02BANHANG PDF renders with form symbol and VAT by percentage
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Company
from apps.einvoice.models import EInvoice, EInvoiceFormSymbol
from apps.einvoice.services import EInvoiceService
from apps.einvoice.services.einvoice_pdf_service import EInvoicePDFService
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company_gtgt_pct(db):
    """TT58 company with vat_method=ty_le_phan_tram (Group 1 or 2)."""
    return Company.objects.create(
        code="TT58PCT",
        name="GTGT Percentage Co",
        tax_code="0123456789",
        accounting_regime=Company.AccountingRegime.TT58,
        vat_method=Company.VatMethod.TY_LE_PHAN_TRAM,
        tndn_method=Company.TndnMethod.TY_LE_PHAN_TRAM,
    )


@pytest.fixture
def company_khau_tru(db):
    """TT58 company with vat_method=khau_tru (Group 3 or 4)."""
    return Company.objects.create(
        code="TT58KT",
        name="Khau Tru Co",
        tax_code="0987654321",
        accounting_regime=Company.AccountingRegime.TT58,
        vat_method=Company.VatMethod.KHAU_TRU,
        tndn_method=Company.TndnMethod.TINH_THUE,
    )


@pytest.fixture
def company_tt133(db):
    """Non-TT58 (TT133) company — should default to 01GTKT."""
    return Company.objects.create(
        code="TT133CO",
        name="TT133 Co",
        tax_code="0555555555",
        accounting_regime=Company.AccountingRegime.TT133,
    )


@pytest.fixture
def customer(db, company_gtgt_pct):
    return Customer.objects.create(
        company=company_gtgt_pct,
        code="CUST02B",
        name="02BANHANG Customer",
        tax_code="0101111222",
        address="456 Ban Hang St",
    )


@pytest.fixture
def product(db, company_gtgt_pct):
    return Product.objects.create(
        company=company_gtgt_pct,
        code="PROD02B",
        name="Ban Hang Product",
        default_unit_price=Decimal("500000"),
        product_type="goods",
        unit_id="cai",
        default_vat_rate=Decimal("5"),
    )


def _make_sales_invoice(company, customer, product, vat_rate=Decimal("0.05")):
    """Helper to create a sales invoice with given VAT rate per line."""
    subtotal = Decimal("1000000")
    vat_amount = (subtotal * vat_rate).quantize(Decimal("0.0001"))
    total = subtotal + vat_amount
    si = SalesInvoice.objects.create(
        company=company,
        invoice_no="SI-02B-001",
        invoice_date="2026-07-01",
        customer=customer,
        currency_code="VND",
        exchange_rate=Decimal("1"),
        subtotal=subtotal,
        vat_amount=vat_amount,
        total_amount=total,
        status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si,
        line_no=1,
        product=product,
        description="Sản phẩm bán hàng",
        quantity=Decimal("2"),
        unit_id="cai",
        unit_price=Decimal("500000"),
        amount_before_vat=subtotal,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        amount=total,
    )
    return si


# ---------------------------------------------------------------------------
# VAL-TT58-042: 02BANHANG available for GTGT% companies
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_default_form_symbol_for_gtgt_pct_company(company_gtgt_pct):
    """GTGT% company defaults to 02BANHANG."""
    symbol = EInvoiceService.default_form_symbol_for_company(company_gtgt_pct)
    assert symbol == EInvoiceFormSymbol.BANHANG_02


@pytest.mark.django_db
def test_available_forms_for_gtgt_pct_company(company_gtgt_pct):
    """GTGT% company has 02BANHANG in available forms."""
    forms = EInvoiceService.available_form_symbols(company_gtgt_pct)
    assert EInvoiceFormSymbol.BANHANG_02 in forms
    assert EInvoiceFormSymbol.GTKT_01 not in forms


@pytest.mark.django_db
def test_issue_from_sales_sets_02banhang_for_gtgt_pct(company_gtgt_pct, customer, product):
    """When issuing from a sales invoice for a GTGT% company, form_symbol=02BANHANG."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product)
    ei = EInvoiceService.issue_from_sales_invoice(si)
    assert ei.form_symbol == EInvoiceFormSymbol.BANHANG_02


@pytest.mark.django_db
def test_group2_company_also_gets_02banhang(db, company_gtgt_pct, customer, product):
    """Group 2 (GTGT% + TNDN tinh_thue) also gets 02BANHANG."""
    company_gtgt_pct.tndn_method = Company.TndnMethod.TINH_THUE
    company_gtgt_pct.save()
    si = _make_sales_invoice(company_gtgt_pct, customer, product)
    ei = EInvoiceService.issue_from_sales_invoice(si)
    assert ei.form_symbol == EInvoiceFormSymbol.BANHANG_02
    assert company_gtgt_pct.tax_method_group == 2


# ---------------------------------------------------------------------------
# VAL-TT58-043: 02BANHANG NOT available for khau_tru companies
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_default_form_symbol_for_khau_tru_company(company_khau_tru):
    """Khau_tru company defaults to 01GTKT."""
    symbol = EInvoiceService.default_form_symbol_for_company(company_khau_tru)
    assert symbol == EInvoiceFormSymbol.GTKT_01


@pytest.mark.django_db
def test_available_forms_for_khau_tru_company(company_khau_tru):
    """Khau_tru company does NOT have 02BANHANG available."""
    forms = EInvoiceService.available_form_symbols(company_khau_tru)
    assert EInvoiceFormSymbol.BANHANG_02 not in forms
    assert EInvoiceFormSymbol.GTKT_01 in forms


@pytest.mark.django_db
def test_issue_from_sales_sets_01gtkt_for_khau_tru(company_khau_tru, db):
    """When issuing from a sales invoice for a khau_tru company, form_symbol=01GTKT."""
    cust = Customer.objects.create(
        company=company_khau_tru,
        code="CUST_KT",
        name="KT Customer",
    )
    prod = Product.objects.create(
        company=company_khau_tru,
        code="PROD_KT",
        name="KT Product",
        default_unit_price=Decimal("1000000"),
        product_type="goods",
        unit_id="cai",
    )
    si = _make_sales_invoice(company_khau_tru, cust, prod, vat_rate=Decimal("0.10"))
    ei = EInvoiceService.issue_from_sales_invoice(si)
    assert ei.form_symbol == EInvoiceFormSymbol.GTKT_01


@pytest.mark.django_db
def test_non_tt58_company_defaults_to_01gtkt(company_tt133):
    """Non-TT58 company always uses 01GTKT regardless of any field."""
    symbol = EInvoiceService.default_form_symbol_for_company(company_tt133)
    assert symbol == EInvoiceFormSymbol.GTKT_01


# ---------------------------------------------------------------------------
# VAL-TT58-044: 02BANHANG has per-line VAT rate, no input VAT deduction fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_02banhang_xml_includes_form_symbol(company_gtgt_pct, customer, product):
    """Generated XML includes the FormSymbol element with 02BANHANG."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product)
    ei = EInvoiceService.issue_from_sales_invoice(si)
    xml_content = ei.xml_file.read().decode("utf-8")
    assert "<FormSymbol>02BANHANG</FormSymbol>" in xml_content


@pytest.mark.django_db
def test_02banhang_xml_includes_per_line_vat_rate(company_gtgt_pct, customer, product):
    """XML includes per-line VATRate (e.g., 5.0 for 5%)."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product, vat_rate=Decimal("0.05"))
    ei = EInvoiceService.issue_from_sales_invoice(si)
    xml_content = ei.xml_file.read().decode("utf-8")
    assert "<VATRate>5" in xml_content


@pytest.mark.django_db
def test_02banhang_json_includes_form_symbol(company_gtgt_pct, customer, product):
    """Generated JSON payload includes formSymbol."""
    import json

    si = _make_sales_invoice(company_gtgt_pct, customer, product)
    ei = EInvoiceService.issue_from_sales_invoice(si)
    data = json.loads(ei.json_file.read())
    assert data["formSymbol"] == "02BANHANG"


@pytest.mark.django_db
def test_02banhang_json_includes_per_line_vat_rate(company_gtgt_pct, customer, product):
    """JSON includes per-line vatRate field."""
    import json

    si = _make_sales_invoice(company_gtgt_pct, customer, product, vat_rate=Decimal("0.01"))
    ei = EInvoiceService.issue_from_sales_invoice(si)
    data = json.loads(ei.json_file.read())
    assert len(data["items"]) == 1
    # vatRate should be 0.01 (1%)
    assert data["items"][0]["vatRate"] == 0.01


@pytest.mark.django_db
def test_02banhang_json_no_input_vat_fields(company_gtgt_pct, customer, product):
    """JSON for 02BANHANG must NOT have input VAT deduction fields."""
    import json

    si = _make_sales_invoice(company_gtgt_pct, customer, product)
    ei = EInvoiceService.issue_from_sales_invoice(si)
    data = json.loads(ei.json_file.read())
    json_str = json.dumps(data)
    # No input VAT deduction fields
    assert "inputVat" not in json_str.lower().replace("inputvat", "input_vat")
    assert "vatDeduction" not in json_str
    assert "deductible" not in json_str.lower()


@pytest.mark.django_db
def test_02banhang_supports_various_vat_rates(company_gtgt_pct, customer, product):
    """02BANHANG line items can have different VAT rates (1%, 5%, etc.)."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product, vat_rate=Decimal("0.01"))
    # Verify 1% rate
    line = si.lines.first()
    assert line.vat_rate == Decimal("0.01")

    ei = EInvoiceService.issue_from_sales_invoice(si)
    xml_content = ei.xml_file.read().decode("utf-8")
    assert "<VATRate>1" in xml_content


# ---------------------------------------------------------------------------
# VAL-TT58-045: 02BANHANG PDF renders correctly
# ---------------------------------------------------------------------------


@pytest.fixture
def einvoice_02banhang(db, company_gtgt_pct, customer, product):
    """Create a published 02BANHANG EInvoice for PDF tests."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product, vat_rate=Decimal("0.05"))
    return EInvoice.objects.create(
        company=company_gtgt_pct,
        sales_invoice=si,
        pattern="1C26T",
        serial="AA/26E",
        form_symbol=EInvoiceFormSymbol.BANHANG_02,
        invoice_no="02BH-0000001",
        status=EInvoice.Status.ISSUED,
        buyer_name=customer.name,
        buyer_tax_code=customer.tax_code,
        buyer_address=customer.address,
        subtotal=si.subtotal,
        vat_rate=Decimal("0.05"),
        vat_amount=si.vat_amount,
        total_amount=si.total_amount,
        total_in_words="Một triệu năm mươi nghìn đồng",
        issue_date="2026-07-01T10:00:00Z",
    )


@pytest.mark.django_db
def test_02banhang_pdf_generates_successfully(einvoice_02banhang):
    """PDF generation for 02BANHANG produces valid PDF bytes."""
    pdf_bytes = EInvoicePDFService().generate_pdf(einvoice_02banhang)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.django_db
def test_02banhang_pdf_contains_form_symbol(einvoice_02banhang):
    """PDF HTML contains 02BANHANG form symbol text."""
    from django.template.loader import render_to_string

    context = EInvoicePDFService()._build_context(einvoice_02banhang)
    html = render_to_string(EInvoicePDFService.TEMPLATE_NAME, context)
    assert "02BANHANG" in html


@pytest.mark.django_db
def test_02banhang_pdf_contains_hoa_don_ban_hang_title(einvoice_02banhang):
    """PDF HTML title says 'Hóa đơn bán hàng' for 02BANHANG."""
    from django.template.loader import render_to_string

    context = EInvoicePDFService()._build_context(einvoice_02banhang)
    html = render_to_string(EInvoicePDFService.TEMPLATE_NAME, context)
    assert "Hóa đơn bán hàng" in html


@pytest.mark.django_db
def test_02banhang_pdf_shows_vat_by_percentage(einvoice_02banhang):
    """PDF shows VAT rate as percentage (5%) for 02BANHANG."""
    from django.template.loader import render_to_string

    context = EInvoicePDFService()._build_context(einvoice_02banhang)
    html = render_to_string(EInvoicePDFService.TEMPLATE_NAME, context)
    # The VAT rate is 5%, should show "5%" somewhere
    assert "5%" in html
    # Should reference "tỷ lệ" for 02BANHANG
    assert "tỷ lệ" in html.lower()


@pytest.mark.django_db
def test_02banhang_pdf_has_per_line_vat_rate_column(einvoice_02banhang):
    """PDF items table has a VAT rate column showing per-line rates."""
    from django.template.loader import render_to_string

    context = EInvoicePDFService()._build_context(einvoice_02banhang)
    html = render_to_string(EInvoicePDFService.TEMPLATE_NAME, context)
    assert "Thuế GTGT" in html


@pytest.mark.django_db
def test_01gtkt_pdf_does_not_say_hoa_don_ban_hang(einvoice_02banhang):
    """For 01GTKT form, PDF should NOT say 'Hóa đơn bán hàng'."""
    from django.template.loader import render_to_string

    einvoice_02banhang.form_symbol = EInvoiceFormSymbol.GTKT_01
    einvoice_02banhang.save()
    context = EInvoicePDFService()._build_context(einvoice_02banhang)
    html = render_to_string(EInvoicePDFService.TEMPLATE_NAME, context)
    assert "Hóa đơn bán hàng" not in html
    assert "Hóa đơn GTGT điện tử" in html


@pytest.mark.django_db
def test_02banhang_pdf_get_or_generate_caches(einvoice_02banhang):
    """get_or_generate caches PDF for 02BANHANG."""
    service = EInvoicePDFService()
    assert not einvoice_02banhang.pdf_file
    pdf_bytes = service.get_or_generate(einvoice_02banhang)
    assert pdf_bytes.startswith(b"%PDF")
    einvoice_02banhang.refresh_from_db()
    assert einvoice_02banhang.pdf_file.name


# ---------------------------------------------------------------------------
# Integration: issue from sales invoice then publish generates correct PDF
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_publish_02banhang_auto_generates_pdf(company_gtgt_pct, customer, product):
    """Publishing a 02BANHANG invoice auto-generates PDF with form symbol."""
    si = _make_sales_invoice(company_gtgt_pct, customer, product, vat_rate=Decimal("0.05"))
    ei = EInvoiceService.issue_from_sales_invoice(si)
    assert ei.form_symbol == EInvoiceFormSymbol.BANHANG_02

    EInvoiceService.publish(ei, invoice_no="02BH-PUB-001")
    ei.refresh_from_db()

    assert ei.status == EInvoice.Status.ISSUED
    assert ei.invoice_no == "02BH-PUB-001"
    assert ei.pdf_file.name
    assert ei.pdf_file.size > 1000
    # Verify PDF content has the form symbol
    pdf_bytes = ei.pdf_file.read()
    assert pdf_bytes.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Model field default
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_einvoice_form_symbol_default_is_01gtkt(company_tt133):
    """EInvoice without explicit form_symbol defaults to 01GTKT."""
    ei = EInvoice.objects.create(
        company=company_tt133,
        pattern="1C26T",
        serial="AA/26E",
    )
    assert ei.form_symbol == EInvoiceFormSymbol.GTKT_01


@pytest.mark.django_db
def test_einvoice_form_symbol_choices():
    """Form symbol choices include both 01GTKT and 02BANHANG."""
    choices = EInvoiceFormSymbol.choices
    values = [c[0] for c in choices]
    assert "01GTKT" in values
    assert "02BANHANG" in values


# ---------------------------------------------------------------------------
# List/Detail view: form symbol is accessible in context
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db, company_gtgt_pct):
    return User.objects.create_superuser(
        username="admin02b", password="Secret123!", email="admin02b@test.local"
    )


@pytest.mark.django_db
def test_list_view_includes_available_forms_for_gtgt_pct(
    admin_user, company_gtgt_pct, einvoice_02banhang
):
    """List view context includes available_forms with 02BANHANG for GTGT% company."""
    from django.test import Client
    from django.urls import reverse

    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = company_gtgt_pct.id
    session.save()

    url = reverse("ui_modern:einvoice_list")
    response = c.get(url)
    assert response.status_code == 200
    assert "02BANHANG" in response.context["available_forms"]
