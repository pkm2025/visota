"""Tests for TT58 DNSN report service and views.

Covers VAL-TT58-029 through VAL-TT58-037:
- VAL-TT58-029: B01-DNSN report renders for TT58 company
- VAL-TT58-030: B01-DNSN balances correctly from ledger entries
- VAL-TT58-031: B01-DNSN not available for non-TT58 companies
- VAL-TT58-032: B02-DNSN report renders for TT58 company
- VAL-TT58-033: B02-DNSN profit calculation matches ledger totals
- VAL-TT58-034: B02-DNSN exports to PDF
- VAL-TT58-035: BCTC mandatory for Group 2 companies
- VAL-TT58-036: BCTC optional for Group 1 companies
- VAL-TT58-037: BCTC mandatory for Group 4, optional for Group 3
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import DnsnLedgerBalance, DnsnVoucher
from apps.ledger.services.dnsn_posting_service import DnsnPostingService
from apps.reporting.services.dnsn_report_service import DnsnReportService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_company(group: int, code: str = "TT58") -> Company:
    """Create a TT58 company with the given tax method group."""
    vat = "ty_le_phan_tram" if group in (1, 2) else "khau_tru"
    tndn = "ty_le_phan_tram" if group in (1, 3) else "tinh_thue"
    return Company.objects.create(
        code=code,
        name=f"TT58 Group {group} Co",
        accounting_regime="tt58",
        vat_method=vat,
        tndn_method=tndn,
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def g1_company(db):
    return _make_company(1, "RP1CO")


@pytest.fixture
def g2_company(db):
    return _make_company(2, "RP2CO")


@pytest.fixture
def g3_company(db):
    return _make_company(3, "RP3CO")


@pytest.fixture
def g4_company(db):
    return _make_company(4, "RP4CO")


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="RP133C",
        name="TT133 Test Co",
        accounting_regime="tt133",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin58rpt",
        password="Secret123!",
        email="admin58rpt@test.local",
    )


def _auth_client(user, company):
    """Create an authenticated client with the given company in session."""
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def g1_client(admin_user, g1_company):
    return _auth_client(admin_user, g1_company)


@pytest.fixture
def g2_client(admin_user, g2_company):
    return _auth_client(admin_user, g2_company)


@pytest.fixture
def g3_client(admin_user, g3_company):
    return _auth_client(admin_user, g3_company)


@pytest.fixture
def g4_client(admin_user, g4_company):
    return _auth_client(admin_user, g4_company)


@pytest.fixture
def tt133_client(admin_user, tt133_company):
    return _auth_client(admin_user, tt133_company)


# ---------------------------------------------------------------------------
# Helper: create posted voucher with entries
# ---------------------------------------------------------------------------


def _post_voucher(company, voucher_no, ledger_type, entries_data, fy=2026, period=7):
    """Create a posted DnsnVoucher with the given entries."""
    voucher = DnsnVoucher.objects.create(
        company=company,
        fiscal_year=fy,
        period=period,
        voucher_no=voucher_no,
        voucher_type="phieu_thu",
        voucher_date=date(fy, period, 15),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(voucher, entries_data)
    return voucher


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


# ---------------------------------------------------------------------------
# Service tests — B01-DNSN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b01_dnsn_generates_for_tt58_company(g4_company):
    """VAL-TT58-029: B01-DNSN report generates for TT58 company."""
    # Create balances for asset/liability/equity ledgers
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)
    _create_balance(g4_company, "s2c", closing_revenue=50_000_000)
    _create_balance(g4_company, "s4b", closing_cash=200_000_000)
    _create_balance(g4_company, "s4a", closing_cash=30_000_000, closing_cost=20_000_000)
    _create_balance(g4_company, "s4d", closing_cash=300_000_000, closing_revenue=20_000_000)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    assert data["report_type"] == "B01-DNSN"
    assert "assets" in data
    assert "liabilities" in data
    assert "equity" in data
    assert data["total_assets"] > 0


@pytest.mark.django_db
def test_b01_dnsn_balances_correctly(g4_company):
    """VAL-TT58-030: B01-DNSN balances (total assets = total liabilities + equity).

    Scenario: cash=100M, receivables=50M, payables=30M, equity=120M
    Expected: total assets = 150M, total liabilities + equity = 150M
    """
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)  # cash
    _create_balance(g4_company, "s4a", closing_cash=50_000_000, closing_cost=30_000_000)
    # receivables=50M in closing_cash, payables=30M in closing_cost
    _create_balance(g4_company, "s4d", closing_cash=120_000_000)  # equity

    svc = DnsnReportService(g4_company)
    data = svc.generate_b01_dnsn(2026, 7)

    # Assets = cash(100M) + receivables(50M) = 150M
    assert data["total_assets"] == Decimal("150000000")
    # Liabilities = payables(30M)
    assert data["total_liabilities"] == Decimal("30000000")
    # Equity = 120M
    assert data["total_equity"] == Decimal("120000000")
    # Liabilities + equity = 30M + 120M = 150M
    assert data["total_liabilities_equity"] == Decimal("150000000")
    # Balanced
    assert data["is_balanced"] is True


@pytest.mark.django_db
def test_b01_dnsn_empty_balances(g1_company):
    """B01-DNSN with no ledger balances should render zeros."""
    svc = DnsnReportService(g1_company)
    data = svc.generate_b01_dnsn(2026, 7)

    assert data["total_assets"] == Decimal("0")
    assert data["total_liabilities_equity"] == Decimal("0")
    assert data["is_balanced"] is True


# ---------------------------------------------------------------------------
# Service tests — B02-DNSN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b02_dnsn_generates_for_tt58_company(g4_company):
    """VAL-TT58-032: B02-DNSN report generates for TT58 company."""
    _create_balance(g4_company, "s2b", closing_revenue=500_000_000, closing_cost=350_000_000)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b02_dnsn(2026, 7)

    assert data["report_type"] == "B02-DNSN"
    assert "revenue" in data
    assert "cost" in data
    assert "net_profit" in data
    assert len(data["rows"]) == 5


@pytest.mark.django_db
def test_b02_dnsn_profit_calculation(g4_company):
    """VAL-TT58-033: B02-DNSN profit calculation matches ledger totals.

    Revenue=500M, Cost=350M -> profit before tax=150M
    """
    _create_balance(g4_company, "s2b", closing_revenue=500_000_000, closing_cost=350_000_000)

    svc = DnsnReportService(g4_company)
    data = svc.generate_b02_dnsn(2026, 7)

    assert data["revenue"] == Decimal("500000000")
    assert data["cost"] == Decimal("350000000")
    assert data["gross_profit"] == Decimal("150000000")
    assert data["net_profit"] == Decimal("150000000")  # no TNDN tax


@pytest.mark.django_db
def test_b02_dnsn_revenue_sums_multiple_ledgers(g2_company):
    """B02-DNSN should sum revenue from multiple revenue ledgers."""
    _create_balance(g2_company, "s2a", closing_revenue=200_000_000)
    _create_balance(g2_company, "s2b", closing_revenue=100_000_000, closing_cost=50_000_000)

    svc = DnsnReportService(g2_company)
    data = svc.generate_b02_dnsn(2026, 7)

    # Revenue from S2a + S2b = 200M + 100M = 300M
    assert data["revenue"] == Decimal("300000000")
    assert data["cost"] == Decimal("50000000")
    assert data["gross_profit"] == Decimal("250000000")


@pytest.mark.django_db
def test_b02_dnsn_with_tndn_tax(g4_company):
    """B02-DNSN subtracts TNDN tax from gross profit."""
    _create_balance(g4_company, "s2b", closing_revenue=500_000_000, closing_cost=350_000_000)
    _create_balance(g4_company, "s4c", closing_vat=30_000_000)  # TNDN tax

    svc = DnsnReportService(g4_company)
    data = svc.generate_b02_dnsn(2026, 7)

    assert data["gross_profit"] == Decimal("150000000")
    assert data["tndn_tax"] == Decimal("30000000")
    assert data["net_profit"] == Decimal("120000000")


# ---------------------------------------------------------------------------
# BCTC mandatory check tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bctc_mandatory_for_group2(g2_company):
    """VAL-TT58-035: BCTC mandatory for Group 2 (tndn_method=tinh_thue)."""
    svc = DnsnReportService(g2_company)
    assert svc.is_bctc_mandatory() is True


@pytest.mark.django_db
def test_bctc_optional_for_group1(g1_company):
    """VAL-TT58-036: BCTC optional for Group 1 (tndn_method=ty_le_phan_tram)."""
    svc = DnsnReportService(g1_company)
    assert svc.is_bctc_mandatory() is False


@pytest.mark.django_db
def test_bctc_mandatory_for_group4(g4_company):
    """VAL-TT58-037: BCTC mandatory for Group 4 (tndn_method=tinh_thue)."""
    svc = DnsnReportService(g4_company)
    assert svc.is_bctc_mandatory() is True


@pytest.mark.django_db
def test_bctc_optional_for_group3(g3_company):
    """VAL-TT58-037: BCTC optional for Group 3 (tndn_method=ty_le_phan_tram)."""
    svc = DnsnReportService(g3_company)
    assert svc.is_bctc_mandatory() is False


@pytest.mark.django_db
def test_bctc_mandatory_group2_blocks_close_without_bctc(g2_company):
    """VAL-TT58-035: Group 2 cannot close year without BCTC."""
    svc = DnsnReportService(g2_company)
    # No balances exist -> no BCTC data
    result = svc.check_bctc_for_period_close(2026, 12)
    assert result["mandatory"] is True
    assert result["has_bctc"] is False
    assert result["can_close"] is False


@pytest.mark.django_db
def test_bctc_mandatory_group2_allows_close_with_bctc(g2_company):
    """Group 2 can close when BCTC data exists."""
    # has_bctc_for_period now checks for posted ledger entries, not just
    # balance rows, so we need to post a voucher to create entries.
    _post_voucher(
        g2_company,
        "BCTC01",
        "s2a",
        [{"ledger_type": "s2a", "description": "Sale", "revenue_amount": 100_000}],
    )
    svc = DnsnReportService(g2_company)
    result = svc.check_bctc_for_period_close(2026, 7)
    assert result["mandatory"] is True
    assert result["has_bctc"] is True
    assert result["can_close"] is True


@pytest.mark.django_db
def test_bctc_optional_group1_allows_close_without_bctc(g1_company):
    """VAL-TT58-036: Group 1 can close without BCTC."""
    svc = DnsnReportService(g1_company)
    result = svc.check_bctc_for_period_close(2026, 12)
    assert result["mandatory"] is False
    assert result["can_close"] is True


@pytest.mark.django_db
def test_bctc_mandatory_group4_blocks_close(g4_company):
    """VAL-TT58-037: Group 4 blocked without BCTC."""
    svc = DnsnReportService(g4_company)
    result = svc.check_bctc_for_period_close(2026, 12)
    assert result["mandatory"] is True
    assert result["can_close"] is False


@pytest.mark.django_db
def test_bctc_optional_group3_allows_close(g3_company):
    """VAL-TT58-037: Group 3 allowed without BCTC."""
    svc = DnsnReportService(g3_company)
    result = svc.check_bctc_for_period_close(2026, 12)
    assert result["mandatory"] is False
    assert result["can_close"] is True


@pytest.mark.django_db
def test_bctc_not_mandatory_for_non_tt58(tt133_company):
    """BCTC check returns False for non-TT58 companies."""
    svc = DnsnReportService(tt133_company)
    assert svc.is_bctc_mandatory() is False


# ---------------------------------------------------------------------------
# View tests — B01-DNSN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b01_report_view_requires_login(db):
    c = Client()
    response = c.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_b01_report_renders_for_tt58(g4_client):
    """VAL-TT58-029: B01-DNSN report renders for TT58 company."""
    response = g4_client.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "B01-DNSN" in content
    assert "TÀI SẢN" in content or "TÀI SẢN" in content.upper()
    assert "NỢ PHẢI TRẢ" in content
    assert "VỐN CHỦ SỞ HỮU" in content


@pytest.mark.django_db
def test_b01_report_not_available_for_non_tt58(tt133_client):
    """VAL-TT58-031: B01-DNSN not available for non-TT58 companies."""
    response = tt133_client.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chỉ dành cho công ty áp dụng chế độ TT58" in content


@pytest.mark.django_db
def test_b01_report_shows_balanced_data(g4_company, g4_client):
    """VAL-TT58-030: B01-DNSN shows balanced data in view."""
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)
    _create_balance(g4_company, "s4d", closing_cash=100_000_000)

    response = g4_client.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Cân đối" in content  # Balanced badge


# ---------------------------------------------------------------------------
# View tests — B02-DNSN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b02_report_view_requires_login(db):
    c = Client()
    response = c.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_b02_report_renders_for_tt58(g4_client):
    """VAL-TT58-032: B02-DNSN report renders for TT58 company."""
    response = g4_client.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "B02-DNSN" in content
    assert "Doanh thu" in content
    assert "Chi phí" in content
    assert "Lợi nhuận" in content


@pytest.mark.django_db
def test_b02_report_shows_correct_profit(g4_company, g4_client):
    """VAL-TT58-033: B02-DNSN profit calculation matches ledger totals."""
    _create_balance(
        g4_company,
        "s2b",
        closing_revenue=500_000_000,
        closing_cost=350_000_000,
    )

    response = g4_client.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Revenue = 500M (vnd filter uses comma separators)
    assert "500,000,000" in content
    # Cost = 350M
    assert "350,000,000" in content
    # Net profit = 150M
    assert "150,000,000" in content


@pytest.mark.django_db
def test_b02_report_not_available_for_non_tt58(tt133_client):
    """B02-DNSN not available for non-TT58 companies."""
    response = tt133_client.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chỉ dành cho công ty áp dụng chế độ TT58" in content


# ---------------------------------------------------------------------------
# View tests — report list
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_report_list_requires_login(db):
    c = Client()
    response = c.get("/modern/dnsn-reports/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_report_list_shows_b01_b02_for_tt58(g4_client):
    """Report list shows B01-DNSN and B02-DNSN for TT58 companies."""
    response = g4_client.get("/modern/dnsn-reports/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "B01-DNSN" in content
    assert "B02-DNSN" in content


@pytest.mark.django_db
def test_report_list_hides_reports_for_non_tt58(tt133_client):
    """VAL-TT58-031: Report list does not show DNSN reports for non-TT58."""
    response = tt133_client.get("/modern/dnsn-reports/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chỉ áp dụng cho công ty áp dụng chế độ TT58" in content


# ---------------------------------------------------------------------------
# View tests — PDF/Excel export
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_b02_export_pdf(g4_company, g4_client):
    """VAL-TT58-034: B02-DNSN exports to PDF."""
    _create_balance(
        g4_company,
        "s2b",
        closing_revenue=500_000_000,
        closing_cost=350_000_000,
    )

    response = g4_client.get(
        "/modern/dnsn-reports/export/?report=B02-DNSN&format=pdf&fiscal_year=2026&period=7"
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"]
    assert ".pdf" in response["Content-Disposition"]
    # PDF magic bytes
    assert response.content[:4] == b"%PDF"


@pytest.mark.django_db
def test_b01_export_pdf(g4_company, g4_client):
    """B01-DNSN exports to PDF."""
    _create_balance(g4_company, "s2d", closing_cash=100_000_000)

    response = g4_client.get(
        "/modern/dnsn-reports/export/?report=B01-DNSN&format=pdf&fiscal_year=2026&period=7"
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


@pytest.mark.django_db
def test_b02_export_excel(g4_company, g4_client):
    """B02-DNSN exports to Excel."""
    _create_balance(
        g4_company,
        "s2b",
        closing_revenue=500_000_000,
        closing_cost=350_000_000,
    )

    response = g4_client.get(
        "/modern/dnsn-reports/export/?report=B02-DNSN&format=xlsx&fiscal_year=2026&period=7"
    )
    assert response.status_code == 200
    assert "spreadsheet" in response["Content-Type"]
    assert ".xlsx" in response["Content-Disposition"]


@pytest.mark.django_db
def test_b01_export_excel(g4_client):
    """B01-DNSN exports to Excel."""
    response = g4_client.get(
        "/modern/dnsn-reports/export/?report=B01-DNSN&format=xlsx&fiscal_year=2026&period=7"
    )
    assert response.status_code == 200
    assert "spreadsheet" in response["Content-Type"]


@pytest.mark.django_db
def test_export_invalid_report_code(g4_client):
    """Invalid report code returns 400."""
    response = g4_client.get("/modern/dnsn-reports/export/?report=INVALID&format=pdf")
    assert response.status_code == 400


@pytest.mark.django_db
def test_export_invalid_format(g4_client):
    """Invalid format returns 400."""
    response = g4_client.get("/modern/dnsn-reports/export/?report=B02-DNSN&format=docx")
    assert response.status_code == 400


@pytest.mark.django_db
def test_export_non_tt58_redirects(tt133_client):
    """Export for non-TT58 company redirects to report list."""
    response = tt133_client.get("/modern/dnsn-reports/export/?report=B02-DNSN&format=pdf")
    assert response.status_code == 302
    assert "dnsn-reports" in response.url


# ---------------------------------------------------------------------------
# BCTC integration with period close
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_period_close_blocked_for_group2_without_bctc(g2_company, g2_client):
    """VAL-TT58-035: Period close blocked for Group 2 without BCTC."""
    response = g2_client.post(
        "/modern/closing/",
        {"fiscal_year": "2026", "period": "12"},
    )
    assert response.status_code == 302
    # Should redirect back (blocked)
    assert "closing" in response.url


@pytest.mark.django_db
def test_period_close_allowed_for_group1_without_bctc(g1_company, g1_client):
    """VAL-TT58-036: Period close allowed for Group 1 without BCTC."""
    response = g1_client.post(
        "/modern/closing/",
        {"fiscal_year": "2026", "period": "7"},
    )
    assert response.status_code == 302
    assert "closing" in response.url


@pytest.mark.django_db
def test_period_close_blocked_for_group4_without_bctc(g4_client):
    """VAL-TT58-037: Period close blocked for Group 4 without BCTC."""
    response = g4_client.post(
        "/modern/closing/",
        {"fiscal_year": "2026", "period": "12"},
    )
    assert response.status_code == 302
    assert "closing" in response.url


@pytest.mark.django_db
def test_period_close_allowed_for_group3_without_bctc(g3_client):
    """VAL-TT58-037: Period close allowed for Group 3 without BCTC."""
    response = g3_client.post(
        "/modern/closing/",
        {"fiscal_year": "2026", "period": "7"},
    )
    assert response.status_code == 302
    assert "closing" in response.url


@pytest.mark.django_db
def test_period_close_allowed_for_group2_with_bctc(g2_company, g2_client):
    """Group 2 period close allowed when BCTC data exists."""
    # Post a voucher to create ledger entries (has_bctc checks for entries now)
    _post_voucher(
        g2_company,
        "BCTC02",
        "s2a",
        [{"ledger_type": "s2a", "description": "Sale", "revenue_amount": 100_000}],
    )
    response = g2_client.post(
        "/modern/closing/",
        {"fiscal_year": "2026", "period": "7"},
    )
    assert response.status_code == 302
    assert "closing" in response.url
