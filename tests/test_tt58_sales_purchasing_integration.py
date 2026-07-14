"""Tests for TT58 Sales/Purchasing VAT Integration.

Covers VAL-TT58-046 through VAL-TT58-050:
- VAL-TT58-046: Sales invoice VAT posting uses vat_method for ty_le_phan_tram
- VAL-TT58-047: Sales invoice VAT posting for khau_tru method
- VAL-TT58-048: Purchasing invoice VAT handling differs by vat_method
- VAL-TT58-049: TNDN calculation uses tndn_method
- VAL-TT58-050: Full TT58 period cycle for Group 1
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.ledger.models import (
    DnsnLedgerBalance,
    DnsnLedgerEntry,
    DnsnVoucher,
)
from apps.master_data.models import Customer, Product, Vendor
from apps.purchasing.services import PurchaseInvoiceService
from apps.sales.services import SalesInvoiceService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_group1_company(db):
    """Group 1: GTGT% + TNDN%."""
    return Company.objects.create(
        code="T58G1",
        name="TT58 Group 1 Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt58_group2_company(db):
    """Group 2: GTGT% + TNDN tinh_thue."""
    return Company.objects.create(
        code="T58G2",
        name="TT58 Group 2 Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="tinh_thue",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt58_group3_company(db):
    """Group 3: GTGT khau_tru + TNDN%."""
    return Company.objects.create(
        code="T58G3",
        name="TT58 Group 3 Co",
        accounting_regime="tt58",
        vat_method="khau_tru",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt58_group4_company(db):
    """Group 4: GTGT khau_tru + TNDN tinh_thue."""
    return Company.objects.create(
        code="T58G4",
        name="TT58 Group 4 Co",
        accounting_regime="tt58",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt133_company(db):
    """Standard TT133 company for regression testing."""
    return Company.objects.create(
        code="TT133C",
        name="TT133 Company",
        accounting_regime="tt133",
    )


def _make_customer(company, code="KH001", name="ABC Customer"):
    return Customer.objects.create(
        company=company,
        code=code,
        name=name,
    )


def _make_vendor(company, code="NCC001", name="XYZ Vendor"):
    return Vendor.objects.create(
        company=company,
        code=code,
        name=name,
    )


def _make_product(company, code="SP001", name="Test Product"):
    return Product.objects.create(
        company=company,
        code=code,
        name=name,
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )


# ---------------------------------------------------------------------------
# VAL-TT58-046: Sales invoice VAT posting uses vat_method for ty_le_phan_tram
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sales_tt58_vat_percentage_creates_dnsn_voucher(tt58_group1_company):
    """VAL-TT58-046: TT58 company with vat_method=ty_le_phan_tram creates
    a DnsnVoucher instead of AccountingVoucher when posting a sales invoice."""
    customer = _make_customer(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = SalesInvoiceService(company=tt58_group1_company)

    invoice = service.create(
        {
            "invoice_no": "HD0001",
            "invoice_date": date(2026, 7, 10),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.05"),
                },
            ],
            "post": True,
        }
    )

    # Should have a DNSN voucher, NOT a standard accounting voucher
    assert invoice.dnsn_voucher_id is not None
    assert invoice.gl_voucher_id is None

    voucher = invoice.dnsn_voucher
    assert voucher.voucher_type == DnsnVoucher.VoucherType.HOA_DON_BAN_HANG
    assert voucher.status == DnsnVoucher.Status.POSTED


@pytest.mark.django_db
def test_sales_tt58_vat_percentage_no_separate_vat_account(tt58_group1_company):
    """VAL-TT58-046: For ty_le_phan_tram, revenue is posted WITH VAT embedded
    and there is no separate VAT output entry (no TK 33311 equivalent)."""
    customer = _make_customer(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = SalesInvoiceService(company=tt58_group1_company)

    invoice = service.create(
        {
            "invoice_no": "HD0002",
            "invoice_date": date(2026, 7, 10),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.05"),
                },
            ],
            "post": True,
        }
    )

    # 10 * 100000 = 1,000,000 subtotal; 5% VAT = 50,000; total = 1,050,000
    assert invoice.subtotal == Decimal("1000000")
    assert invoice.vat_amount == Decimal("50000")
    assert invoice.total_amount == Decimal("1050000")

    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))

    # Group 1 uses S1 revenue ledger
    ledger_types = [e.ledger_type for e in entries]
    assert "s1" in ledger_types

    # The revenue entry should have total_amount (including VAT) as revenue_amount
    s1_entry = next(e for e in entries if e.ledger_type == "s1")
    assert s1_entry.revenue_amount == Decimal("1050000")

    # There should be NO S3b entry (no separate VAT output ledger)
    assert "s3b" not in ledger_types, "ty_le_phan_tram should not have separate VAT output"


@pytest.mark.django_db
def test_sales_tt58_vat_percentage_revenue_includes_vat(tt58_group2_company):
    """VAL-TT58-046: For Group 2 (GTGT%), revenue is posted with VAT embedded."""
    customer = _make_customer(tt58_group2_company)
    product = _make_product(tt58_group2_company)
    service = SalesInvoiceService(company=tt58_group2_company)

    invoice = service.create(
        {
            "invoice_no": "HD0003",
            "invoice_date": date(2026, 7, 15),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("5"),
                    "unit_price": Decimal("200000"),
                    "vat_rate": Decimal("0.03"),
                },
            ],
            "post": True,
        }
    )

    # 5 * 200000 = 1,000,000 subtotal; 3% VAT = 30,000; total = 1,030,000
    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))

    # Group 2 uses S2a revenue ledger
    s2a_entry = next(e for e in entries if e.ledger_type == "s2a")
    assert s2a_entry.revenue_amount == Decimal("1030000")  # includes VAT

    # No S3b VAT entry for ty_le_phan_tram
    assert "s3b" not in [e.ledger_type for e in entries]


# ---------------------------------------------------------------------------
# VAL-TT58-047: Sales invoice VAT posting for khau_tru method
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sales_tt58_khau_tru_posts_vat_to_s3b(tt58_group3_company):
    """VAL-TT58-047: For vat_method=khau_tru, revenue is posted without VAT
    and output VAT is posted to S3b ledger."""
    customer = _make_customer(tt58_group3_company)
    product = _make_product(tt58_group3_company)
    service = SalesInvoiceService(company=tt58_group3_company)

    invoice = service.create(
        {
            "invoice_no": "HD0004",
            "invoice_date": date(2026, 7, 10),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.10"),
                },
            ],
            "post": True,
        }
    )

    # 10 * 100000 = 1,000,000 subtotal; 10% VAT = 100,000; total = 1,100,000
    assert invoice.subtotal == Decimal("1000000")
    assert invoice.vat_amount == Decimal("100000")

    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))
    ledger_types = [e.ledger_type for e in entries]

    # Group 3 uses S3a revenue ledger
    assert "s3a" in ledger_types
    s3a_entry = next(e for e in entries if e.ledger_type == "s3a")
    # Revenue should be subtotal (WITHOUT VAT for khau_tru)
    assert s3a_entry.revenue_amount == Decimal("1000000")

    # S3b should have output VAT
    assert "s3b" in ledger_types
    s3b_entry = next(e for e in entries if e.ledger_type == "s3b")
    assert s3b_entry.vat_output == Decimal("100000")


@pytest.mark.django_db
def test_sales_tt58_khau_tru_group4_posts_to_s2b_and_s3b(tt58_group4_company):
    """VAL-TT58-047: Group 4 (khau_tru) posts revenue to S2b and output VAT to S3b."""
    customer = _make_customer(tt58_group4_company)
    product = _make_product(tt58_group4_company)
    service = SalesInvoiceService(company=tt58_group4_company)

    invoice = service.create(
        {
            "invoice_no": "HD0005",
            "invoice_date": date(2026, 7, 10),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("20"),
                    "unit_price": Decimal("50000"),
                    "vat_rate": Decimal("0.08"),
                },
            ],
            "post": True,
        }
    )

    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))
    ledger_types = [e.ledger_type for e in entries]

    # Group 4 uses S2b revenue ledger
    assert "s2b" in ledger_types
    s2b_entry = next(e for e in entries if e.ledger_type == "s2b")
    # Revenue should be subtotal (WITHOUT VAT)
    assert s2b_entry.revenue_amount == Decimal("1000000")

    # S3b should have output VAT
    assert "s3b" in ledger_types
    s3b_entry = next(e for e in entries if e.ledger_type == "s3b")
    assert s3b_entry.vat_output == Decimal("80000")


# ---------------------------------------------------------------------------
# VAL-TT58-048: Purchasing invoice VAT handling differs by vat_method
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_purchase_tt58_vat_percentage_no_input_vat(tt58_group1_company):
    """VAL-TT58-048: For vat_method=ty_le_phan_tram, no input VAT credit is
    recorded. Cost includes VAT (full total_amount)."""
    vendor = _make_vendor(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = PurchaseInvoiceService(company=tt58_group1_company)

    invoice = service.create(
        {
            "invoice_no": "PN0001",
            "invoice_date": date(2026, 7, 10),
            "vendor_id": vendor.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.05"),
                },
            ],
            "post": True,
        }
    )

    assert invoice.dnsn_voucher_id is not None
    assert invoice.gl_voucher_id is None

    voucher = invoice.dnsn_voucher
    assert voucher.voucher_type == DnsnVoucher.VoucherType.HOA_DON_MUA_HANG

    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))
    ledger_types = [e.ledger_type for e in entries]

    # No S3b entry (no input VAT deduction)
    assert "s3b" not in ledger_types, "ty_le_phan_tram should not record input VAT"

    # Cost should be total_amount (including VAT)
    cost_entry = entries[0]
    assert cost_entry.cost_amount == invoice.total_amount  # 1,050,000


@pytest.mark.django_db
def test_purchase_tt58_khau_tru_records_input_vat(tt58_group3_company):
    """VAL-TT58-048: For vat_method=khau_tru, input VAT is recorded to S3b
    and is creditable. Cost does NOT include VAT."""
    vendor = _make_vendor(tt58_group3_company)
    product = _make_product(tt58_group3_company)
    service = PurchaseInvoiceService(company=tt58_group3_company)

    invoice = service.create(
        {
            "invoice_no": "PN0002",
            "invoice_date": date(2026, 7, 10),
            "vendor_id": vendor.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.10"),
                },
            ],
            "post": True,
        }
    )

    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))
    ledger_types = [e.ledger_type for e in entries]

    # Cost should be subtotal (WITHOUT VAT)
    cost_entry = next(e for e in entries if e.cost_amount > 0)
    assert cost_entry.cost_amount == Decimal("1000000")

    # S3b should have input VAT
    assert "s3b" in ledger_types
    s3b_entry = next(e for e in entries if e.ledger_type == "s3b")
    assert s3b_entry.vat_input == Decimal("100000")


@pytest.mark.django_db
def test_purchase_tt58_group4_records_input_vat(tt58_group4_company):
    """VAL-TT58-048: Group 4 (khau_tru) purchase records input VAT in S3b."""
    vendor = _make_vendor(tt58_group4_company)
    product = _make_product(tt58_group4_company)
    service = PurchaseInvoiceService(company=tt58_group4_company)

    invoice = service.create(
        {
            "invoice_no": "PN0003",
            "invoice_date": date(2026, 7, 10),
            "vendor_id": vendor.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("5"),
                    "unit_price": Decimal("200000"),
                    "vat_rate": Decimal("0.08"),
                },
            ],
            "post": True,
        }
    )

    voucher = invoice.dnsn_voucher
    entries = list(DnsnLedgerEntry.objects.filter(voucher=voucher))
    ledger_types = [e.ledger_type for e in entries]

    # Cost recorded in S2b without VAT
    assert "s2b" in ledger_types
    cost_entry = next(e for e in entries if e.ledger_type == "s2b")
    assert cost_entry.cost_amount == Decimal("1000000")  # subtotal only

    # Input VAT in S3b
    assert "s3b" in ledger_types
    s3b_entry = next(e for e in entries if e.ledger_type == "s3b")
    assert s3b_entry.vat_input == Decimal("80000")


# ---------------------------------------------------------------------------
# VAL-TT58-049: TNDN calculation uses tndn_method
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tndn_calculation_percentage_method(tt58_group1_company):
    """VAL-TT58-049: When tndn_method=ty_le_phan_tram, tax = revenue × rate."""
    from apps.core.services.tndn_calculation_service import TndnCalculationService

    service = TndnCalculationService(tt58_group1_company)
    result = service.calculate(revenue=Decimal("100000000"))  # 100M

    assert result["method"] == "ty_le_phan_tram"
    # Default industry is 'other' = 1.0%
    assert result["rate"] == Decimal("0.01")
    # 100M × 1% = 1M
    assert result["tax_amount"] == Decimal("1000000")
    assert result["taxable_income"] == Decimal("100000000")


@pytest.mark.django_db
def test_tndn_calculation_tinh_thue_method(tt58_group4_company):
    """VAL-TT58-049: When tndn_method=tinh_thue, tax = taxable_income × CIT rate."""
    from apps.core.services.tndn_calculation_service import TndnCalculationService

    service = TndnCalculationService(tt58_group4_company)
    # Revenue 200M, costs 150M, taxable income = 50M
    result = service.calculate(
        revenue=Decimal("200000000"),
        deductible_costs=Decimal("150000000"),
    )

    assert result["method"] == "tinh_thue"
    assert result["taxable_income"] == Decimal("50000000")
    # CIT rate from TaxConfigService or fallback 20%
    expected_tax = (Decimal("50000000") * result["rate"]).quantize(Decimal("0.0001"))
    assert result["tax_amount"] == expected_tax


@pytest.mark.django_db
def test_tndn_calculation_via_sales_service(tt58_group1_company):
    """VAL-TT58-049: SalesInvoiceService.calculate_tndn uses tndn_method."""
    service = SalesInvoiceService(company=tt58_group1_company)
    result = service.calculate_tndn(revenue=Decimal("500000000"))  # 500M

    assert result["method"] == "ty_le_phan_tram"
    assert result["tax_amount"] == Decimal("5000000")  # 500M × 1% = 5M


@pytest.mark.django_db
def test_tndn_calculation_tinh_thue_zero_income(tt58_group4_company):
    """VAL-TT58-049: tinh_thue with negative taxable income gives zero tax."""
    from apps.core.services.tndn_calculation_service import TndnCalculationService

    service = TndnCalculationService(tt58_group4_company)
    result = service.calculate(
        revenue=Decimal("100000000"),
        deductible_costs=Decimal("150000000"),
    )

    assert result["method"] == "tinh_thue"
    assert result["taxable_income"] == Decimal("0")
    assert result["tax_amount"] == Decimal("0")


# ---------------------------------------------------------------------------
# VAL-TT58-050: Full TT58 period cycle for Group 1
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_full_tt58_group1_cycle(tt58_group1_company):
    """VAL-TT58-050: Group 1 company can create vouchers, post to S1-DNSN,
    and generate reports without errors."""
    customer = _make_customer(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = SalesInvoiceService(company=tt58_group1_company)

    # Create and post a sales invoice
    invoice = service.create(
        {
            "invoice_no": "HD0100",
            "invoice_date": date(2026, 7, 1),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("1000000"),
                    "vat_rate": Decimal("0.05"),
                },
            ],
            "post": True,
        }
    )

    # Verify DNSN voucher created and posted
    assert invoice.dnsn_voucher is not None
    assert invoice.dnsn_voucher.status == DnsnVoucher.Status.POSTED

    # Verify ledger entry in S1
    entries = DnsnLedgerEntry.objects.filter(
        company=tt58_group1_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert entries.count() == 1
    # Revenue includes VAT for ty_le_phan_tram: 10M + 5% = 10.5M
    assert entries.first().revenue_amount == Decimal("10500000")

    # Verify ledger balance updated
    balance = DnsnLedgerBalance.objects.get(
        company=tt58_group1_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert balance.closing_revenue == Decimal("10500000")

    # Verify BCTC is optional for Group 1
    from apps.reporting.services.dnsn_report_service import DnsnReportService

    report_service = DnsnReportService(tt58_group1_company)
    assert not report_service.is_bctc_mandatory()

    # Verify B02-DNSN report can be generated
    b02 = report_service.generate_b02_dnsn(2026, 7)
    assert b02["revenue"] == Decimal("10500000")

    # Verify period close check passes (BCTC optional)
    close_check = report_service.check_bctc_for_period_close(2026, 7)
    assert close_check["can_close"] is True


@pytest.mark.django_db
def test_full_tt58_group1_multiple_invoices_accumulate(tt58_group1_company):
    """VAL-TT58-050: Multiple sales invoices accumulate in S1-DNSN."""
    customer = _make_customer(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = SalesInvoiceService(company=tt58_group1_company)

    for i in range(3):
        service.create(
            {
                "invoice_no": f"HD{i:04d}",
                "invoice_date": date(2026, 7, 5 + i),
                "customer_id": customer.id,
                "lines": [
                    {
                        "product_id": product.id,
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("1000000"),
                        "vat_rate": Decimal("0.05"),
                    },
                ],
                "post": True,
            }
        )

    # S1 should have 3 entries, total = 3 * 1.05M = 3.15M
    entries = DnsnLedgerEntry.objects.filter(
        company=tt58_group1_company,
        ledger_type="s1",
    )
    assert entries.count() == 3

    balance = DnsnLedgerBalance.objects.get(
        company=tt58_group1_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert balance.closing_revenue == Decimal("3150000")


@pytest.mark.django_db
def test_full_tt58_cycle_unpost_invoice(tt58_group1_company):
    """VAL-TT58-050: Unposting a TT58 invoice reverses DNSN entries."""
    customer = _make_customer(tt58_group1_company)
    product = _make_product(tt58_group1_company)
    service = SalesInvoiceService(company=tt58_group1_company)

    invoice = service.create(
        {
            "invoice_no": "HD0200",
            "invoice_date": date(2026, 7, 1),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("1"),
                    "unit_price": Decimal("1000000"),
                    "vat_rate": Decimal("0.05"),
                },
            ],
            "post": True,
        }
    )

    assert invoice.dnsn_voucher.status == DnsnVoucher.Status.POSTED
    assert DnsnLedgerEntry.objects.filter(voucher=invoice.dnsn_voucher).count() == 1

    # Unpost
    service.unpost(invoice)
    invoice.refresh_from_db()
    assert invoice.status == 0  # DRAFT

    invoice.dnsn_voucher.refresh_from_db()
    assert invoice.dnsn_voucher.status == DnsnVoucher.Status.DRAFT
    assert DnsnLedgerEntry.objects.filter(voucher=invoice.dnsn_voucher).count() == 0


# ---------------------------------------------------------------------------
# Regression: Existing TT133/TT200 behavior unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tt133_sales_invoice_unchanged(tt133_company):
    """Existing TT133 sales behavior is unchanged: creates AccountingVoucher."""
    customer = _make_customer(tt133_company)
    product = _make_product(tt133_company)
    service = SalesInvoiceService(company=tt133_company)

    invoice = service.create(
        {
            "invoice_no": "BC0001",
            "invoice_date": date(2026, 6, 15),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.10"),
                },
            ],
            "post": True,
        }
    )

    # Should use AccountingVoucher, NOT DnsnVoucher
    assert invoice.gl_voucher_id is not None
    assert invoice.dnsn_voucher_id is None

    voucher = invoice.gl_voucher
    assert voucher.voucher_type == "sales_invoice"
    assert voucher.is_posted

    # Verify standard VAT posting to TK 33311
    lines = voucher.lines.all()
    account_codes = {line.account_code for line in lines}
    assert "33311" in account_codes  # VAT output


@pytest.mark.django_db
def test_tt133_purchase_invoice_unchanged(tt133_company):
    """Existing TT133 purchase behavior is unchanged: creates AccountingVoucher."""
    vendor = _make_vendor(tt133_company)
    product = _make_product(tt133_company)
    service = PurchaseInvoiceService(company=tt133_company)

    invoice = service.create(
        {
            "invoice_no": "PN0001",
            "invoice_date": date(2026, 6, 15),
            "vendor_id": vendor.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.10"),
                },
            ],
            "post": True,
        }
    )

    # Should use AccountingVoucher, NOT DnsnVoucher
    assert invoice.gl_voucher_id is not None
    assert invoice.dnsn_voucher_id is None

    voucher = invoice.gl_voucher
    assert voucher.voucher_type == "purchase_invoice"

    # Verify standard VAT posting to TK 1331
    lines = voucher.lines.all()
    account_codes = {line.account_code for line in lines}
    assert "1331" in account_codes  # VAT input


@pytest.mark.django_db
def test_tt133_sales_unpost_unchanged(tt133_company):
    """TT133 sales unpost still works via standard VoucherPostingService."""
    customer = _make_customer(tt133_company)
    product = _make_product(tt133_company)
    service = SalesInvoiceService(company=tt133_company)

    invoice = service.create(
        {
            "invoice_no": "BC0002",
            "invoice_date": date(2026, 6, 15),
            "customer_id": customer.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("1"),
                    "unit_price": Decimal("100000"),
                    "vat_rate": Decimal("0.10"),
                },
            ],
            "post": True,
        }
    )
    assert invoice.gl_voucher.is_posted

    service.unpost(invoice)
    invoice.refresh_from_db()
    assert invoice.status == 0

    invoice.gl_voucher.refresh_from_db()
    assert not invoice.gl_voucher.is_posted
