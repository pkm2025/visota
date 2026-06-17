"""Tests for InputInvoice model + InvoiceExtractionService."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.input_docs.models import InputInvoice
from apps.input_docs.services import InvoiceExtractionService
from apps.ledger.models import AccountingVoucher
from apps.master_data.models import Product, Vendor
from apps.purchasing.models import PurchaseInvoice


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test Co")
    product = Product.objects.create(
        company=company,
        code="SP001",
        name="Pin",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )
    return company, product


def test_input_invoice_create(setup):
    company, _ = setup
    inv = InputInvoice.objects.create(
        company=company,
        invoice_no="HD001",
        seller_tax_code="0101234567",
        seller_name="Công ty ABC",
        amount_before_vat=Decimal("100000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("10000"),
        total_amount=Decimal("110000"),
        extraction_status=InputInvoice.ExtractionStatus.PENDING,
    )
    inv.refresh_from_db()
    assert inv.id is not None
    assert inv.extraction_status == "pending"
    assert inv.total_amount == Decimal("110000")


def test_extract_from_text_parses_vietnamese_invoice(setup):
    company, _ = setup
    text = """
    HÓA ĐƠN GTGT
    Ký hiệu: 1C22TAA  Số: 0001234
    Ngày: 15/06/2026
    Đơn vị bán: Công ty XYZ
    Mã số thuế: 0109876543
    Địa chỉ: Số 2 Đường B, Hà Nội
    Thành tiền: 100000
    Tiền thuế GTGT: 10000 (10%)
    TỔNG CỘNG THANH TOÁN: 110000
    """
    svc = InvoiceExtractionService(company=company)
    data = svc.extract_from_text(text)
    assert data["seller_tax_code"] == "0109876543"
    assert data["invoice_no"] == "0001234"
    assert data["invoice_date"] == date(2026, 6, 15)
    assert data["amount_before_vat"] == Decimal("100000")
    assert data["vat_amount"] == Decimal("10000")
    assert data["total_amount"] == Decimal("110000")
    assert data["vat_rate"] == Decimal("0.10")


def test_extract_from_xml_parses_einvoice(setup):
    company, _ = setup
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <HoaDon>
      <TTChung>
        <KHDon>1C22TAA</KHDon>
        <SHDon>0005678</SHDon>
        <NLap>2026-06-15</NLap>
        <MST>0105554444</MST>
      </TTChung>
      <NDHDon>
        <TTKhach>
          <Ten>Công ty Mua</Ten>
        </TTKhach>
      </NDHDon>
      <TToan>
        <TgTThue>200000</TgTThue>
        <TgTGTGT>20000</TgTGTGT>
        <TgTTTBSo>220000</TgTTTBSo>
        <TSuat>10</TSuat>
      </TToan>
    </HoaDon>
    """
    svc = InvoiceExtractionService(company=company)
    data = svc.extract_from_xml(xml)
    assert data["invoice_no"] == "0005678"
    assert data["invoice_date"] == date(2026, 6, 15)
    assert data["seller_tax_code"] == "0105554444"
    assert data["amount_before_vat"] == Decimal("200000")
    assert data["vat_amount"] == Decimal("20000")
    assert data["total_amount"] == Decimal("220000")
    assert data["vat_rate"] == Decimal("0.10")


def test_auto_create_purchase_invoice(setup):
    company, product = setup
    inv = InputInvoice.objects.create(
        company=company,
        invoice_no="HD002",
        invoice_date=date(2026, 6, 15),
        seller_tax_code="0105554444",
        seller_name="Công ty XYZ",
        amount_before_vat=Decimal("100000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("10000"),
        total_amount=Decimal("110000"),
        extraction_status=InputInvoice.ExtractionStatus.EXTRACTED,
    )
    svc = InvoiceExtractionService(company=company)
    pi = svc.auto_create_purchase_invoice(inv, product_id=product.id)

    # PI created with correct totals
    assert isinstance(pi, PurchaseInvoice)
    assert pi.invoice_no == "HD002"
    assert pi.vendor.tax_code == "0105554444"
    assert pi.vendor.name == "Công ty XYZ"
    assert pi.total_amount == Decimal("110000")

    # Voucher posted
    assert pi.gl_voucher is not None
    assert pi.gl_voucher.is_posted

    # InputInvoice updated to matched
    inv.refresh_from_db()
    assert inv.extraction_status == InputInvoice.ExtractionStatus.MATCHED
    assert inv.purchase_invoice_id == pi.id
    assert inv.processed_at is not None
