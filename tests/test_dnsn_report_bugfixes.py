"""Regression tests for TT58 DNSN report service bug fixes.

Covers fixes identified by scrutiny:
- B01: S4c (thuế khác) reads closing_vat, not closing_cash
- B02: get_b01_export_rows headers/data column alignment
- Non-blocking: has_bctc_for_period requires posted entries
- Non-blocking: S2c total_amount accumulated into closing_revenue
- Non-blocking: S3b VAT input/output sign distinction
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.ledger.models import DnsnLedgerBalance, DnsnVoucher
from apps.ledger.services.dnsn_posting_service import DnsnPostingService
from apps.reporting.services.dnsn_report_service import DnsnReportService

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_company(group: int, code: str = "TT58") -> Company:
    """Create a TT58 company with the given tax method group."""
    vat = "ty_le_phan_tram" if group in (1, 2) else "khau_tru"
    tndn = "ty_le_phan_tram" if group in (1, 3) else "tinh_thue"
    return Company.objects.create(
        code=code,
        name=f"Bugfix Group {group} Co",
        accounting_regime="tt58",
        vat_method=vat,
        tndn_method=tndn,
        entity_type="doanh_nghiep_sieu_nho",
    )


def _create_balance(
    company,
    ledger_type,
    fy=2026,
    period=7,
    closing_cash=None,
    closing_revenue=None,
    closing_cost=None,
    closing_vat=None,
):
    """Create or update a DnsnLedgerBalance with given closing values."""
    balance, _ = DnsnLedgerBalance.objects.get_or_create(
        company=company,
        fiscal_year=fy,
        period=period,
        ledger_type=ledger_type,
    )
    if closing_cash is not None:
        balance.closing_cash = Decimal(str(closing_cash))
    if closing_revenue is not None:
        balance.closing_revenue = Decimal(str(closing_revenue))
    if closing_cost is not None:
        balance.closing_cost = Decimal(str(closing_cost))
    if closing_vat is not None:
        balance.closing_vat = Decimal(str(closing_vat))
    balance.save()
    return balance


def _post_voucher(company, voucher_no, entries_data, fy=2026, period=7, day=15):
    """Create a posted DnsnVoucher with the given entries."""
    voucher = DnsnVoucher.objects.create(
        company=company,
        fiscal_year=fy,
        period=period,
        voucher_no=voucher_no,
        voucher_type="phieu_thu",
        voucher_date=date(fy, period, day),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(voucher, entries_data)
    return voucher


@pytest.fixture
def g4_company(db):
    return _make_company(4, "BFXG4")


@pytest.fixture
def g2_company(db):
    return _make_company(2, "BFXG2")


@pytest.fixture
def g3_company(db):
    return _make_company(3, "BFXG3")


# ---------------------------------------------------------------------------
# Bug 1 (blocking): B01-DNSN S4c reads closing_vat not closing_cash
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b01_s4c_reads_closing_vat_not_closing_cash(g4_company):
    """B01-DNSN: S4c (thuế khác) should use closing_vat, not closing_cash.

    If we set closing_vat=50M but closing_cash=0, the report should show 50M.
    If we set closing_cash=99M but closing_vat=0, the report should show 0.
    """
    # Set only closing_vat
    _create_balance(g4_company, "s4c", closing_vat=50_000_000, closing_cash=0)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    # Find the "Thuế khác phải nộp" row in liabilities
    other_taxes_row = next(r for r in data["liabilities"] if "thuế khác" in r["label"].lower())
    assert other_taxes_row["amount"] == Decimal("50000000"), (
        f"Expected 50M from closing_vat, got {other_taxes_row['amount']}"
    )


@pytest.mark.django_db
def test_b01_s4c_ignores_closing_cash(g4_company):
    """B01-DNSN: closing_cash on S4c should NOT be used for thuế khác."""
    _create_balance(g4_company, "s4c", closing_vat=0, closing_cash=99_000_000)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    other_taxes_row = next(r for r in data["liabilities"] if "thuế khác" in r["label"].lower())
    assert other_taxes_row["amount"] == Decimal("0"), (
        f"Should be 0 (closing_vat=0), but got {other_taxes_row['amount']}"
    )


@pytest.mark.django_db
def test_b01_s4c_with_both_fields_set(g4_company):
    """B01-DNSN: when both closing_vat and closing_cash are set, uses closing_vat."""
    _create_balance(g4_company, "s4c", closing_vat=30_000_000, closing_cash=70_000_000)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    other_taxes_row = next(r for r in data["liabilities"] if "thuế khác" in r["label"].lower())
    assert other_taxes_row["amount"] == Decimal("30000000")


# ---------------------------------------------------------------------------
# Bug 2 (blocking): get_b01_export_rows headers/data column alignment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b01_export_rows_header_count_matches_data_columns(g4_company):
    """get_b01_export_rows: every data row has the same number of columns as headers."""
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)
    _create_balance(g4_company, "s4d", closing_cash=100_000_000)

    svc = DnsnReportService(g4_company)
    headers, rows = svc.get_b01_export_rows(2026, 7)

    header_count = len(headers)
    assert header_count >= 3, f"Headers should have at least 3 columns, got {header_count}"

    for i, row in enumerate(rows):
        assert len(row) == header_count, (
            f"Row {i} has {len(row)} columns but headers has {header_count}: {row}"
        )


@pytest.mark.django_db
def test_b01_export_rows_has_four_headers(g4_company):
    """get_b01_export_rows should have 4 headers: STT, Chỉ tiêu, Mã số, Số tiền."""
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)

    svc = DnsnReportService(g4_company)
    headers, rows = svc.get_b01_export_rows(2026, 7)

    assert len(headers) == 4
    assert headers[0] == "STT"
    assert headers[1] == "Chỉ tiêu"
    assert "Số tiền" in headers[-1]  # last header is the amount column


@pytest.mark.django_db
def test_b01_export_rows_data_is_in_last_column(g4_company):
    """get_b01_export_rows: the formatted amount should be in the last column."""
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)

    svc = DnsnReportService(g4_company)
    headers, rows = svc.get_b01_export_rows(2026, 7)

    # Find the "Tiền" row (first asset row after section header)
    tien_row = None
    for r in rows:
        if r[1] == "Tiền":
            tien_row = r
            break

    assert tien_row is not None, "Could not find 'Tiền' row"
    # The amount should be in the last column (index 3)
    assert tien_row[-1] == "100.000.000", f"Expected '100.000.000' in last col, got {tien_row[-1]}"


# ---------------------------------------------------------------------------
# Non-blocking fix 1: has_bctc_for_period requires posted entries
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_has_bctc_for_period_false_with_only_empty_balances(g2_company):
    """has_bctc_for_period should be False when only empty zero-balance rows exist."""
    # Create a balance row with all zeros (no entries posted)
    _create_balance(
        g2_company,
        "s2a",
        closing_revenue=0,
        closing_cost=0,
        closing_cash=0,
        closing_vat=0,
    )

    svc = DnsnReportService(g2_company)
    assert svc.has_bctc_for_period(2026, 7) is False, (
        "Should be False: no posted ledger entries exist, only empty balance rows"
    )


@pytest.mark.django_db
def test_has_bctc_for_period_true_with_posted_entries(g2_company):
    """has_bctc_for_period should be True when posted ledger entries exist."""
    _post_voucher(
        g2_company,
        "BV001",
        [
            {
                "ledger_type": "s2a",
                "description": "Sale",
                "revenue_amount": 100_000_000,
            }
        ],
    )

    svc = DnsnReportService(g2_company)
    assert svc.has_bctc_for_period(2026, 7) is True


@pytest.mark.django_db
def test_has_bctc_for_period_false_for_different_period(g2_company):
    """has_bctc_for_period should be False for a period with no entries."""
    _post_voucher(
        g2_company,
        "BV002",
        [{"ledger_type": "s2a", "description": "Sale", "revenue_amount": 50_000}],
        period=7,
    )

    svc = DnsnReportService(g2_company)
    # Period 12 should have no entries
    assert svc.has_bctc_for_period(2026, 12) is False


@pytest.mark.django_db
def test_bctc_period_close_requires_entries_not_just_balance(g2_company):
    """BCTC close check should not pass just because a balance row exists."""
    # Create an empty balance row
    _create_balance(g2_company, "s2a")

    svc = DnsnReportService(g2_company)
    result = svc.check_bctc_for_period_close(2026, 7)
    assert result["mandatory"] is True
    assert result["has_bctc"] is False, (
        "Should require actual posted entries, not just empty balance rows"
    )
    assert result["can_close"] is False


# ---------------------------------------------------------------------------
# Non-blocking fix 2: S2c total_amount accumulated into balance
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_s2c_total_amount_accumulated_in_closing_revenue(g4_company):
    """S2c entries with total_amount should accumulate into closing_revenue.

    When posting S2c entries, the total_amount should be reflected in
    the DnsnLedgerBalance.closing_revenue (which B01-DNSN reads as inventory).
    """
    _post_voucher(
        g4_company,
        "INV001",
        [
            {
                "ledger_type": "s2c",
                "description": "Purchase inventory",
                "item_code": "SP001",
                "item_name": "Sản phẩm A",
                "quantity": 100,
                "unit_price": 500_000,
                "total_amount": 50_000_000,
            }
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g4_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s2c",
    )
    assert balance.closing_revenue == Decimal("50000000"), (
        f"Expected 50M in closing_revenue, got {balance.closing_revenue}"
    )


@pytest.mark.django_db
def test_s2c_multiple_entries_accumulate(g4_company):
    """Multiple S2c entries should all accumulate into closing_revenue."""
    _post_voucher(
        g4_company,
        "INV002",
        [
            {
                "ledger_type": "s2c",
                "description": "Buy item A",
                "item_code": "A",
                "total_amount": 30_000_000,
            }
        ],
    )
    _post_voucher(
        g4_company,
        "INV003",
        [
            {
                "ledger_type": "s2c",
                "description": "Buy item B",
                "item_code": "B",
                "total_amount": 20_000_000,
            }
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g4_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s2c",
    )
    assert balance.closing_revenue == Decimal("50000000"), (
        f"Expected 50M (30M + 20M), got {balance.closing_revenue}"
    )


@pytest.mark.django_db
def test_s2c_reflected_in_b01_inventory(g4_company):
    """S2c posted entries should appear as inventory in B01-DNSN."""
    _post_voucher(
        g4_company,
        "INV004",
        [
            {
                "ledger_type": "s2c",
                "description": "Buy item",
                "total_amount": 80_000_000,
            }
        ],
    )

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    inventory_row = next(r for r in data["assets"] if "tồn kho" in r["label"].lower())
    assert inventory_row["amount"] == Decimal("80000000"), (
        f"Expected 80M inventory, got {inventory_row['amount']}"
    )


# ---------------------------------------------------------------------------
# Non-blocking fix 3: S3b VAT input/output sign distinction
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_s3b_vat_output_minus_input(g3_company):
    """S3b balance should compute net VAT = output - input.

    VAT output (đầu ra, payable) minus VAT input (đầu vào, creditable).
    """
    _post_voucher(
        g3_company,
        "VAT001",
        [
            {
                "ledger_type": "s3b",
                "description": "Output VAT from sale",
                "vat_output": 10_000_000,
                "vat_input": 0,
            }
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g3_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s3b",
    )
    assert balance.closing_vat == Decimal("10000000"), (
        f"Expected 10M (output only), got {balance.closing_vat}"
    )


@pytest.mark.django_db
def test_s3b_vat_input_reduces_payable(g3_company):
    """S3b: VAT input should reduce the net VAT payable."""
    _post_voucher(
        g3_company,
        "VAT002",
        [
            {
                "ledger_type": "s3b",
                "description": "Output VAT",
                "vat_output": 10_000_000,
            },
            {
                "ledger_type": "s3b",
                "description": "Input VAT",
                "vat_input": 6_000_000,
            },
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g3_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s3b",
    )
    # Net payable = 10M output - 6M input = 4M
    assert balance.closing_vat == Decimal("4000000"), (
        f"Expected 4M (10M output - 6M input), got {balance.closing_vat}"
    )


@pytest.mark.django_db
def test_s3b_vat_input_exceeds_output(g3_company):
    """S3b: when input > output, net VAT is negative (refund/credit)."""
    _post_voucher(
        g3_company,
        "VAT003",
        [
            {
                "ledger_type": "s3b",
                "description": "Small output VAT",
                "vat_output": 3_000_000,
            },
            {
                "ledger_type": "s3b",
                "description": "Large input VAT",
                "vat_input": 8_000_000,
            },
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g3_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s3b",
    )
    # Net = 3M - 8M = -5M (credit / refund)
    assert balance.closing_vat == Decimal("-5000000"), (
        f"Expected -5M (3M output - 8M input), got {balance.closing_vat}"
    )


@pytest.mark.django_db
def test_s3b_vat_output_and_input_on_same_voucher(g3_company):
    """S3b: entries on same voucher should still distinguish signs."""
    _post_voucher(
        g3_company,
        "VAT004",
        [
            {
                "ledger_type": "s3b",
                "description": "Output VAT",
                "vat_output": 15_000_000,
            },
            {
                "ledger_type": "s3b",
                "description": "Input VAT",
                "vat_input": 4_000_000,
            },
        ],
    )

    balance = DnsnLedgerBalance.objects.get(
        company=g3_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s3b",
    )
    assert balance.closing_vat == Decimal("11000000"), (
        f"Expected 11M (15M - 4M), got {balance.closing_vat}"
    )
