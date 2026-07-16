"""Regression tests for VAL-DNSN-001: DNSN entry total sign.

Verifies that cash_out and bank_out are SUBTRACTED from running balance
(not added), and that voucher total calculation does not double-count.
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
from apps.ledger.services import DnsnPostingService


@pytest.fixture
def dnsn_company(db):
    return Company.objects.create(
        code="DNSN001",
        name="DNSN Sign Test Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


def _make_voucher(company, vno="PV0001", vtype="phieu_chi", d=date(2026, 7, 1)):
    return DnsnVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=7,
        voucher_no=vno,
        voucher_type=vtype,
        voucher_date=d,
    )


# ---------------------------------------------------------------------------
# _entry_total sign: cash_out / bank_out must be subtracted, not added
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_entry_total_subtracts_cash_out(dnsn_company):
    """_entry_total must subtract cash_out, not add it.

    VAL-DNSN-001: outflows decrease the running balance.
    """
    service = DnsnPostingService()
    voucher = _make_voucher(dnsn_company)
    entry = service._create_entry(
        voucher,
        1,
        {
            "ledger_type": "s2d",
            "description": "Chi tien mat",
            "cash_in": Decimal("0"),
            "cash_out": Decimal("500000"),
        },
    )
    # A pure outflow must yield a negative entry total.
    assert service._entry_total(entry) == Decimal("-500000")


@pytest.mark.django_db
def test_entry_total_subtracts_bank_out(dnsn_company):
    """_entry_total must subtract bank_out, not add it."""
    service = DnsnPostingService()
    voucher = _make_voucher(dnsn_company)
    entry = service._create_entry(
        voucher,
        1,
        {
            "ledger_type": "s2d",
            "description": "Chuyen khoan tra",
            "bank_out": Decimal("800000"),
        },
    )
    assert service._entry_total(entry) == Decimal("-800000")


@pytest.mark.django_db
def test_entry_total_cash_in_minus_cash_out(dnsn_company):
    """Net cash entry: cash_in increases, cash_out decreases the total."""
    service = DnsnPostingService()
    voucher = _make_voucher(dnsn_company)
    entry = service._create_entry(
        voucher,
        1,
        {
            "ledger_type": "s2d",
            "description": "Thu + chi",
            "cash_in": Decimal("1000000"),
            "cash_out": Decimal("300000"),
            "bank_in": Decimal("200000"),
            "bank_out": Decimal("100000"),
        },
    )
    # Expected: 1,000,000 - 300,000 + 200,000 - 100,000 = 800,000
    assert service._entry_total(entry) == Decimal("800000")


# ---------------------------------------------------------------------------
# Running balance: outflows decrease the cumulative running balance
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cash_out_decreases_running_balance(dnsn_company):
    """VAL-DNSN-001: cash outflow must DECREASE the running balance."""
    service = DnsnPostingService()

    v1 = _make_voucher(dnsn_company, vno="PT0001", vtype="phieu_thu", d=date(2026, 7, 1))
    service.post(
        v1,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Thu tien",
                "cash_in": Decimal("1000000"),
            },
        ],
    )

    v2 = _make_voucher(dnsn_company, vno="PC0001", vtype="phieu_chi", d=date(2026, 7, 2))
    service.post(
        v2,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Chi tien",
                "cash_out": Decimal("400000"),
            },
        ],
    )

    entries = list(
        DnsnLedgerEntry.objects.filter(
            company=dnsn_company,
            ledger_type="s2d",
        ).order_by("entry_date", "id")
    )
    assert len(entries) == 2
    # First entry: +1,000,000
    assert entries[0].running_balance == Decimal("1000000")
    # Second entry: 1,000,000 - 400,000 = 600,000 (NOT 1,400,000)
    assert entries[1].running_balance == Decimal("600000")


@pytest.mark.django_db
def test_bank_out_decreases_running_balance(dnsn_company):
    """VAL-DNSN-001: bank outflow must DECREASE the running balance."""
    service = DnsnPostingService()

    v1 = _make_voucher(dnsn_company, vno="PT0001", vtype="phieu_thu", d=date(2026, 7, 1))
    service.post(
        v1,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Thu qua ngan hang",
                "bank_in": Decimal("2000000"),
            },
        ],
    )

    v2 = _make_voucher(dnsn_company, vno="PC0001", vtype="phieu_chi", d=date(2026, 7, 2))
    service.post(
        v2,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Tra qua ngan hang",
                "bank_out": Decimal("700000"),
            },
        ],
    )

    entries = list(
        DnsnLedgerEntry.objects.filter(
            company=dnsn_company,
            ledger_type="s2d",
        ).order_by("entry_date", "id")
    )
    assert len(entries) == 2
    assert entries[0].running_balance == Decimal("2000000")
    # 2,000,000 - 700,000 = 1,300,000 (NOT 2,700,000)
    assert entries[1].running_balance == Decimal("1300000")


@pytest.mark.django_db
def test_period_cash_balance_reflects_outflow(dnsn_company):
    """DnsnLedgerBalance.period_cash must subtract outflows correctly."""
    service = DnsnPostingService()

    v = _make_voucher(dnsn_company, vno="PC0001", vtype="phieu_chi", d=date(2026, 7, 5))
    service.post(
        v,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Chi hop ly",
                "cash_in": Decimal("500000"),
                "cash_out": Decimal("200000"),
                "bank_in": Decimal("0"),
                "bank_out": Decimal("0"),
            },
        ],
    )

    bal = DnsnLedgerBalance.objects.get(
        company=dnsn_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s2d",
    )
    # Net: 500,000 - 200,000 = 300,000
    assert bal.period_cash == Decimal("300000")
    assert bal.closing_cash == Decimal("300000")


# ---------------------------------------------------------------------------
# Double-counting: total_amount must not be added on top of component fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_entry_total_no_double_count_revenue_and_total(dnsn_company):
    """_entry_total must NOT sum revenue_amount + total_amount together.

    The entry total should represent a single coherent value, not the sum
    of overlapping fields (which would double-count).
    """
    service = DnsnPostingService()
    voucher = _make_voucher(dnsn_company)
    entry = service._create_entry(
        voucher,
        1,
        {
            "ledger_type": "s1",
            "description": "Doanh thu",
            "revenue_amount": Decimal("1000000"),
            # total_amount set to same value must NOT be double-counted
            "total_amount": Decimal("1000000"),
        },
    )
    # Must be 1,000,000 (not 2,000,000)
    assert service._entry_total(entry) == Decimal("1000000")


@pytest.mark.django_db
def test_voucher_total_amount_reflects_outflow(dnsn_company):
    """Voucher.total_amount must subtract outflows (regression for VAL-DNSN-001)."""
    service = DnsnPostingService()
    v = _make_voucher(dnsn_company, vno="PC0001", vtype="phieu_chi")
    service.post(
        v,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Chi tien",
                "cash_out": Decimal("600000"),
            },
        ],
    )
    v.refresh_from_db()
    # A pure outflow yields a negative voucher total.
    assert v.total_amount == Decimal("-600000")


@pytest.mark.django_db
def test_voucher_total_mixed_inflows_outflows(dnsn_company):
    """Voucher total with mixed inflows/outflows is computed correctly."""
    service = DnsnPostingService()
    v = _make_voucher(dnsn_company, vno="PT0001", vtype="phieu_thu")
    service.post(
        v,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Thu va chi",
                "cash_in": Decimal("1500000"),
                "cash_out": Decimal("500000"),
                "bank_in": Decimal("0"),
                "bank_out": Decimal("300000"),
            },
        ],
    )
    v.refresh_from_db()
    # 1,500,000 - 500,000 - 300,000 = 700,000
    assert v.total_amount == Decimal("700000")
