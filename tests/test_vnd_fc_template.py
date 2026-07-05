"""Tests for m3-vnd-fc-template-selection feature (VAL-M3-016 .. VAL-M3-022).

Validates that the four sub-ledger views (CashBook, BankBook, SalesDetail,
SubLedger) accept a ``template=vnd|fc`` query parameter:

* ``template=fc`` adds three extra columns: "Ps nợ n.tệ", "Ps có n.tệ", "Tỷ giá"
* Default (no param) and ``template=vnd`` are identical and backward compatible
* Period filtering (``from_date`` / ``to_date``) works under both templates
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="FCTCO",
        name="FC Template Co",
        fiscal_year_start_month=1,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="fc_admin", password="Secret123", email="fc@test.local"
    )


def _make_fc_voucher(
    company,
    voucher_no,
    debit_lines,
    credit_lines,
    exchange_rate=Decimal("24000"),
    currency_code="USD",
    voucher_date=date(2026, 6, 15),
    period=6,
):
    """Create a posted voucher with foreign-currency amounts on its lines.

    Each debit/credit line is a tuple ``(account_code, vnd_amount, fc_amount)``.
    """
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=period,
        voucher_no=voucher_no,
        voucher_type="journal",
        voucher_date=voucher_date,
        status=AccountingVoucher.Status.DRAFT,
        currency_code=currency_code,
        exchange_rate=exchange_rate,
    )
    line_no = 1
    for acc, vnd, fc in debit_lines:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal(str(vnd)),
            credit_vnd=Decimal("0"),
            debit_fc=Decimal(str(fc)),
            credit_fc=Decimal("0"),
        )
        line_no += 1
    for acc, vnd, fc in credit_lines:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal("0"),
            credit_vnd=Decimal(str(vnd)),
            debit_fc=Decimal("0"),
            credit_fc=Decimal(str(fc)),
        )
        line_no += 1
    VoucherPostingService().post(v)
    return v


# ---------------------------------------------------------------------------
# VAL-M3-016 — Cash book FC template shows FC columns
# ---------------------------------------------------------------------------


@pytest.fixture
def cash_book_fc_setup(company, admin_user):
    v = _make_fc_voucher(
        company,
        "FC-CB-001",
        debit_lines=[("111", 24_000_000, 1000)],
        credit_lines=[("131", 24_000_000, 1000)],
    )
    return company, admin_user, v


def _table_headers(body: str) -> list:
    """Extract <th> cell texts from the first reporting table in body."""
    import re

    cells = re.findall(r"<th[^>]*>(.*?)</th>", body, re.DOTALL | re.IGNORECASE)
    return [re.sub(r"<[^>]+>", "", c).strip() for c in cells]


@pytest.mark.django_db
def test_cash_book_fc_template_shows_fc_columns(cash_book_fc_setup):
    """``?template=fc`` renders Ps nợ n.tệ, Ps có n.tệ, Tỷ giá headers."""
    _, user, _ = cash_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6&template=fc")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert any("Ps nợ n.tệ" in h for h in headers), headers
    assert any("Ps có n.tệ" in h for h in headers), headers
    assert any("Tỷ giá" in h for h in headers), headers


@pytest.mark.django_db
def test_cash_book_vnd_template_hides_fc_columns(cash_book_fc_setup):
    """``?template=vnd`` does NOT include the FC table headers."""
    _, user, _ = cash_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6&template=vnd")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert not any("Ps nợ n.tệ" in h for h in headers), headers
    assert not any("Ps có n.tệ" in h for h in headers), headers
    assert not any(h == "Tỷ giá" for h in headers), headers


# ---------------------------------------------------------------------------
# VAL-M3-017 — Bank book FC template shows FC columns
# ---------------------------------------------------------------------------


@pytest.fixture
def bank_book_fc_setup(company, admin_user):
    v = _make_fc_voucher(
        company,
        "FC-BB-001",
        debit_lines=[("331", 12_000_000, 500)],
        credit_lines=[("112", 12_000_000, 500)],
    )
    return company, admin_user, v


@pytest.mark.django_db
def test_bank_book_fc_template_shows_fc_columns(bank_book_fc_setup):
    _, user, _ = bank_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6&template=fc")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert any("Ps nợ n.tệ" in h for h in headers), headers
    assert any("Ps có n.tệ" in h for h in headers), headers
    assert any("Tỷ giá" in h for h in headers), headers


@pytest.mark.django_db
def test_bank_book_vnd_template_hides_fc_columns(bank_book_fc_setup):
    _, user, _ = bank_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6&template=vnd")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert not any("Ps nợ n.tệ" in h for h in headers), headers
    assert not any(h == "Tỷ giá" for h in headers), headers


# ---------------------------------------------------------------------------
# VAL-M3-018 — Sales detail FC template shows FC columns
# ---------------------------------------------------------------------------


@pytest.fixture
def sales_detail_fc_setup(company, admin_user):
    v = _make_fc_voucher(
        company,
        "FC-SD-001",
        debit_lines=[("131", 48_000_000, 2000)],
        credit_lines=[("511", 48_000_000, 2000)],
    )
    return company, admin_user, v


@pytest.mark.django_db
def test_sales_detail_fc_template_shows_fc_columns(sales_detail_fc_setup):
    _, user, _ = sales_detail_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/sales-detail/?fiscal_year=2026&period=6&template=fc")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert any("Ps nợ n.tệ" in h for h in headers), headers
    assert any("Ps có n.tệ" in h for h in headers), headers
    assert any("Tỷ giá" in h for h in headers), headers


@pytest.mark.django_db
def test_sales_detail_vnd_template_hides_fc_columns(sales_detail_fc_setup):
    _, user, _ = sales_detail_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/sales-detail/?fiscal_year=2026&period=6&template=vnd")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert not any("Ps nợ n.tệ" in h for h in headers), headers
    assert not any(h == "Tỷ giá" for h in headers), headers


# ---------------------------------------------------------------------------
# VAL-M3-019 — Sub-ledger FC template shows FC columns
# ---------------------------------------------------------------------------


@pytest.fixture
def sub_ledger_fc_setup(company, admin_user):
    v = _make_fc_voucher(
        company,
        "FC-SL-001",
        debit_lines=[("131", 24_000_000, 1000)],
        credit_lines=[("111", 24_000_000, 1000)],
    )
    return company, admin_user, v


@pytest.mark.django_db
def test_sub_ledger_fc_template_shows_fc_columns(sub_ledger_fc_setup):
    _, user, _ = sub_ledger_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/sub-ledger/?fiscal_year=2026&account_code=131&template=fc")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert any("Ps nợ n.tệ" in h for h in headers), headers
    assert any("Ps có n.tệ" in h for h in headers), headers
    assert any("Tỷ giá" in h for h in headers), headers


@pytest.mark.django_db
def test_sub_ledger_vnd_template_hides_fc_columns(sub_ledger_fc_setup):
    _, user, _ = sub_ledger_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/sub-ledger/?fiscal_year=2026&account_code=131&template=vnd")
    assert r.status_code == 200
    headers = _table_headers(r.content.decode())
    assert not any("Ps nợ n.tệ" in h for h in headers), headers
    assert not any(h == "Tỷ giá" for h in headers), headers


# ---------------------------------------------------------------------------
# VAL-M3-020 — Default template=vnd backward compatible
# ---------------------------------------------------------------------------


def _strip_csrf(body: bytes) -> bytes:
    """Remove csrfmiddlewaretoken values so two responses can be compared."""
    import re

    return re.sub(rb"csrfmiddlewaretoken[^&'\"]*", b"csrfmiddlewaretoken", body)


@pytest.mark.django_db
def test_cash_book_default_equals_vnd(cash_book_fc_setup):
    """No template param produces same output as template=vnd."""
    _, user, _ = cash_book_fc_setup
    c = Client()
    c.force_login(user)
    r_default = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6")
    r_vnd = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6&template=vnd")
    assert _strip_csrf(r_default.content) == _strip_csrf(r_vnd.content)


@pytest.mark.django_db
def test_bank_book_default_equals_vnd(bank_book_fc_setup):
    _, user, _ = bank_book_fc_setup
    c = Client()
    c.force_login(user)
    r_default = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6")
    r_vnd = c.get("/modern/reports/bank-book/?fiscal_year=2026&period=6&template=vnd")
    assert _strip_csrf(r_default.content) == _strip_csrf(r_vnd.content)


@pytest.mark.django_db
def test_sales_detail_default_equals_vnd(sales_detail_fc_setup):
    _, user, _ = sales_detail_fc_setup
    c = Client()
    c.force_login(user)
    r_default = c.get("/modern/reports/sales-detail/?fiscal_year=2026&period=6")
    r_vnd = c.get("/modern/reports/sales-detail/?fiscal_year=2026&period=6&template=vnd")
    assert _strip_csrf(r_default.content) == _strip_csrf(r_vnd.content)


@pytest.mark.django_db
def test_sub_ledger_default_equals_vnd(sub_ledger_fc_setup):
    _, user, _ = sub_ledger_fc_setup
    c = Client()
    c.force_login(user)
    r_default = c.get("/modern/reports/sub-ledger/?fiscal_year=2026&account_code=131")
    r_vnd = c.get("/modern/reports/sub-ledger/?fiscal_year=2026&account_code=131&template=vnd")
    assert _strip_csrf(r_default.content) == _strip_csrf(r_vnd.content)


# ---------------------------------------------------------------------------
# VAL-M3-021 — FC column header labels match spec
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fc_column_labels_match_spec(cash_book_fc_setup):
    """The three FC headers are present with exact Vietnamese labels."""
    _, user, _ = cash_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6&template=fc")
    headers = _table_headers(r.content.decode())
    # Exact substring match in the table header cells
    assert any("Ps nợ n.tệ" in h for h in headers)
    assert any("Ps có n.tệ" in h for h in headers)
    assert any("Tỷ giá" in h for h in headers)


# ---------------------------------------------------------------------------
# VAL-M3-022 — Period filter works in both templates
# ---------------------------------------------------------------------------


@pytest.fixture
def cash_book_two_periods(company, admin_user):
    """Two vouchers in different periods to test from_date/to_date filtering."""
    v1 = _make_fc_voucher(
        company,
        "FC-2P-001",
        debit_lines=[("111", 24_000_000, 1000)],
        credit_lines=[("131", 24_000_000, 1000)],
        voucher_date=date(2026, 6, 10),
        period=6,
    )
    v2 = _make_fc_voucher(
        company,
        "FC-2P-002",
        debit_lines=[("111", 12_000_000, 500)],
        credit_lines=[("131", 12_000_000, 500)],
        voucher_date=date(2026, 7, 10),
        period=7,
    )
    return company, admin_user, v1, v2


@pytest.mark.django_db
def test_period_filter_vnd_template(cash_book_two_periods):
    """from_date/to_date filters rows under template=vnd."""
    _, user, v1, v2 = cash_book_two_periods
    c = Client()
    c.force_login(user)

    # Filter to only June 2026
    r = c.get("/modern/reports/cash-book/?template=vnd&from_date=2026-06-01&to_date=2026-06-30")
    assert r.status_code == 200
    # Only v1 (June) appears
    nos = [row["voucher_no"] for row in r.context["rows"]]
    assert "FC-2P-001" in nos
    assert "FC-2P-002" not in nos


@pytest.mark.django_db
def test_period_filter_fc_template(cash_book_two_periods):
    """from_date/to_date filters rows under template=fc."""
    _, user, v1, v2 = cash_book_two_periods
    c = Client()
    c.force_login(user)

    # Filter to only July 2026
    r = c.get("/modern/reports/cash-book/?template=fc&from_date=2026-07-01&to_date=2026-07-31")
    assert r.status_code == 200
    nos = [row["voucher_no"] for row in r.context["rows"]]
    assert "FC-2P-002" in nos
    assert "FC-2P-001" not in nos
    # FC columns are present in the table
    headers = _table_headers(r.content.decode())
    assert any("Ps nợ n.tệ" in h for h in headers)
    assert any("Tỷ giá" in h for h in headers)


@pytest.mark.django_db
def test_period_filter_period_param(cash_book_two_periods):
    """period=6 returns the June voucher; period=7 returns the July voucher."""
    _, user, v1, v2 = cash_book_two_periods
    c = Client()
    c.force_login(user)

    r_june = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6")
    assert r_june.status_code == 200
    nos_june = [row["voucher_no"] for row in r_june.context["rows"]]
    assert "FC-2P-001" in nos_june
    assert "FC-2P-002" not in nos_june

    r_july = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=7")
    assert r_july.status_code == 200
    nos_july = [row["voucher_no"] for row in r_july.context["rows"]]
    assert "FC-2P-002" in nos_july
    assert "FC-2P-001" not in nos_july


# ---------------------------------------------------------------------------
# FC data flows to the template
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fc_amounts_in_response(cash_book_fc_setup):
    """When template=fc, the FC amounts and exchange rate are in the row dict."""
    _, user, v = cash_book_fc_setup
    c = Client()
    c.force_login(user)
    r = c.get("/modern/reports/cash-book/?fiscal_year=2026&period=6&template=fc")
    assert r.status_code == 200
    rows = r.context["rows"]
    assert len(rows) == 1
    # debit side line on 111 has debit_fc=1000
    row = rows[0]
    assert row["debit_fc"] == Decimal("1000")
    assert row["exchange_rate"] == Decimal("24000")
