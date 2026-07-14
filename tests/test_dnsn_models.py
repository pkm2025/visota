"""Tests for TT58 DNSN models and posting service.

Covers VAL-TT58-018, VAL-TT58-019, VAL-TT58-020, VAL-TT58-021:
- DnsnLedgerEntry stores entries without account_code/debit/credit
- DnsnLedgerEntry linked to source voucher
- Running balance computed for ledger entries
- Posting does not enforce debit == credit
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.core.models import Company
from apps.ledger.models import (
    DnsnLedgerBalance,
    DnsnLedgerEntry,
    DnsnVoucher,
)
from apps.ledger.services import DnsnPostingService
from apps.ledger.services.dnsn_posting_service import DnsnVoucherLockedError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_company(db):
    return Company.objects.create(
        code="TT58M",
        name="TT58 Models Test Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def group4_company(db):
    return Company.objects.create(
        code="TT58G4",
        name="TT58 Group 4 Co",
        accounting_regime="tt58",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
        entity_type="doanh_nghiep_sieu_nho",
    )


# ---------------------------------------------------------------------------
# DnsnVoucher model tests
# ---------------------------------------------------------------------------


def test_dnsn_voucher_has_voucher_type_choices():
    """DnsnVoucher must have all required voucher_type choices."""
    choices = [code for code, _label in DnsnVoucher.VoucherType.choices]
    assert "phieu_thu" in choices
    assert "phieu_chi" in choices
    assert "phieu_nhap" in choices
    assert "phieu_xuat" in choices
    assert "hoa_don_ban_hang" in choices
    assert "hoa_don_mua_hang" in choices
    assert "chung_tu_khac" in choices


def test_dnsn_voucher_has_status_choices():
    """DnsnVoucher must have draft, posted, locked statuses."""
    choices = [code for code, _label in DnsnVoucher.Status.choices]
    assert "draft" in choices
    assert "posted" in choices
    assert "locked" in choices


def test_dnsn_voucher_inherits_company_owned_model():
    """DnsnVoucher must inherit CompanyOwnedModel for multi-tenant isolation."""
    from apps.core.managers import CompanyOwnedModel

    assert issubclass(DnsnVoucher, CompanyOwnedModel)


def test_dnsn_voucher_has_no_account_code_field():
    """DnsnVoucher must NOT have account_code, debit, or credit fields."""
    field_names = {f.name for f in DnsnVoucher._meta.get_fields()}
    assert "account_code" not in field_names
    assert "debit" not in field_names
    assert "credit" not in field_names


@pytest.mark.django_db
def test_dnsn_voucher_creation(tt58_company):
    """A DnsnVoucher can be created with all fields."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien ban hang",
        partner_name="Khach hang A",
        partner_tax_code="0101234567",
        partner_address="Ha Noi",
        invoice_no="HD001",
        invoice_date=date(2026, 7, 1),
        invoice_form="02BANHANG",
        invoice_serial="AA/26E",
    )
    assert v.pk is not None
    assert v.voucher_type == "phieu_thu"
    assert v.status == "draft"
    assert v.partner_name == "Khach hang A"


@pytest.mark.django_db
def test_dnsn_voucher_unique_per_company_year_type(tt58_company):
    """voucher_no is unique per (company, fiscal_year, voucher_type)."""
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    with pytest.raises(IntegrityError):
        DnsnVoucher.objects.create(
            company=tt58_company,
            fiscal_year=2026,
            period=7,
            voucher_no="PT0001",
            voucher_type="phieu_thu",
            voucher_date=date(2026, 7, 2),
        )


@pytest.mark.django_db
def test_dnsn_voucher_str(tt58_company):
    """DnsnVoucher __str__ includes voucher_no and date."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    s = str(v)
    assert "PT0001" in s


@pytest.mark.django_db
def test_dnsn_voucher_is_posted_property(tt58_company):
    """is_posted returns True when status is posted or locked."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    assert not v.is_posted
    v.status = "posted"
    assert v.is_posted
    v.status = "locked"
    assert v.is_posted


# ---------------------------------------------------------------------------
# DnsnLedgerEntry model tests (VAL-TT58-018, VAL-TT58-019)
# ---------------------------------------------------------------------------


def test_dnsn_ledger_entry_has_no_account_code_debit_credit():
    """VAL-TT58-018: DnsnLedgerEntry must NOT have account_code, debit, credit fields."""
    field_names = {f.name for f in DnsnLedgerEntry._meta.get_fields()}
    assert "account_code" not in field_names
    assert "debit" not in field_names
    assert "credit" not in field_names
    assert "offset_account_code" not in field_names


def test_dnsn_ledger_entry_has_ledger_type_choices():
    """DnsnLedgerEntry must have all S1-S4 ledger types."""
    choices = [code for code, _label in DnsnLedgerEntry.LedgerType.choices]
    assert "s1" in choices
    assert "s2a" in choices
    assert "s2b" in choices
    assert "s2c" in choices
    assert "s2d" in choices
    assert "s3a" in choices
    assert "s3b" in choices
    assert "s4a" in choices
    assert "s4b" in choices
    assert "s4c" in choices
    assert "s4d" in choices


def test_dnsn_ledger_entry_has_revenue_cost_tax_cash_fields():
    """DnsnLedgerEntry must have revenue, cost, tax, and cash fields."""
    field_names = {f.name for f in DnsnLedgerEntry._meta.get_fields()}
    assert "revenue_amount" in field_names
    assert "cost_amount" in field_names
    assert "vat_amount" in field_names
    assert "tndn_amount" in field_names
    assert "cash_in" in field_names
    assert "cash_out" in field_names
    assert "bank_in" in field_names
    assert "bank_out" in field_names


def test_dnsn_ledger_entry_has_running_balance():
    """DnsnLedgerEntry must have a running_balance field."""
    field_names = {f.name for f in DnsnLedgerEntry._meta.get_fields()}
    assert "running_balance" in field_names


@pytest.mark.django_db
def test_dnsn_ledger_entry_creation(tt58_company):
    """A DnsnLedgerEntry can be created linked to a voucher."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    entry = DnsnLedgerEntry.objects.create(
        voucher=v,
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        line_no=1,
        entry_date=date(2026, 7, 1),
        ledger_type="s1",
        description="Doanh thu ban hang",
        revenue_amount=Decimal("1000000"),
    )
    assert entry.pk is not None
    assert entry.ledger_type == "s1"
    assert entry.revenue_amount == Decimal("1000000")
    assert entry.voucher == v


@pytest.mark.django_db
def test_dnsn_ledger_entry_linked_to_voucher(tt58_company):
    """VAL-TT58-019: DnsnLedgerEntry is linked to its source voucher."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="hoa_don_ban_hang",
        voucher_date=date(2026, 7, 1),
    )
    entry = DnsnLedgerEntry.objects.create(
        voucher=v,
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        line_no=1,
        entry_date=date(2026, 7, 1),
        ledger_type="s2a",
        revenue_amount=Decimal("500000"),
    )
    assert entry.voucher_id == v.id
    # Reverse lookup
    assert v.ledger_entries.count() == 1
    assert v.ledger_entries.first() == entry


# ---------------------------------------------------------------------------
# DnsnLedgerBalance model tests
# ---------------------------------------------------------------------------


def test_dnsn_ledger_balance_has_opening_closing_fields():
    """DnsnLedgerBalance must have opening and closing balance fields."""
    field_names = {f.name for f in DnsnLedgerBalance._meta.get_fields()}
    assert "opening_revenue" in field_names
    assert "closing_revenue" in field_names
    assert "opening_cost" in field_names
    assert "closing_cost" in field_names


def test_dnsn_ledger_balance_has_ledger_type():
    """DnsnLedgerBalance tracks per ledger_type."""
    field_names = {f.name for f in DnsnLedgerBalance._meta.get_fields()}
    assert "ledger_type" in field_names


@pytest.mark.django_db
def test_dnsn_ledger_balance_creation(tt58_company):
    """A DnsnLedgerBalance can be created for a period + ledger_type."""
    bal = DnsnLedgerBalance.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
        opening_revenue=Decimal("0"),
        closing_revenue=Decimal("0"),
    )
    assert bal.pk is not None
    assert bal.ledger_type == "s1"


@pytest.mark.django_db
def test_dnsn_ledger_balance_unique_per_company_period_ledger(tt58_company):
    """One balance row per (company, fiscal_year, period, ledger_type)."""
    DnsnLedgerBalance.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    with pytest.raises(IntegrityError):
        DnsnLedgerBalance.objects.create(
            company=tt58_company,
            fiscal_year=2026,
            period=7,
            ledger_type="s1",
        )


# ---------------------------------------------------------------------------
# DnsnPostingService tests (VAL-TT58-021, VAL-TT58-020)
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_voucher(tt58_company):
    """A DnsnVoucher with a single-sided revenue entry (no matching debit/credit)."""
    return DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien ban hang",
    )


@pytest.mark.django_db
def test_posting_service_post_creates_entries(tt58_voucher):
    """VAL-TT58-021: DnsnPostingService.post() creates entries without debit=credit validation."""
    service = DnsnPostingService()
    entry_data = [
        {
            "ledger_type": "s1",
            "description": "Doanh thu ban hang",
            "revenue_amount": Decimal("1000000"),
        },
    ]
    service.post(tt58_voucher, entries=entry_data)

    tt58_voucher.refresh_from_db()
    assert tt58_voucher.status == "posted"
    assert DnsnLedgerEntry.objects.filter(voucher=tt58_voucher).count() == 1


@pytest.mark.django_db
def test_posting_service_no_balance_check(tt58_voucher):
    """VAL-TT58-021: Posting does not enforce debit == credit (single-sided entries OK)."""
    service = DnsnPostingService()
    # Single-sided entry — no matching debit/credit pair
    entry_data = [
        {
            "ledger_type": "s1",
            "description": "Doanh thu",
            "revenue_amount": Decimal("500000"),
            "cost_amount": Decimal("200000"),  # Unbalanced in double-entry terms
        },
    ]
    # Should not raise any balance error
    service.post(tt58_voucher, entries=entry_data)
    tt58_voucher.refresh_from_db()
    assert tt58_voucher.status == "posted"


@pytest.mark.django_db
def test_posting_service_updates_balance(tt58_voucher):
    """Posting updates DnsnLedgerBalance correctly."""
    service = DnsnPostingService()
    entry_data = [
        {
            "ledger_type": "s1",
            "description": "Doanh thu thang 7",
            "revenue_amount": Decimal("1000000"),
        },
    ]
    service.post(tt58_voucher, entries=entry_data)

    bal = DnsnLedgerBalance.objects.get(
        company=tt58_voucher.company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert bal.closing_revenue == Decimal("1000000")


@pytest.mark.django_db
def test_posting_service_unpost_reverses_entries(tt58_voucher):
    """DnsnPostingService.unpost() reverses entries and resets balances."""
    service = DnsnPostingService()
    entry_data = [
        {
            "ledger_type": "s1",
            "description": "Doanh thu",
            "revenue_amount": Decimal("1000000"),
        },
    ]
    service.post(tt58_voucher, entries=entry_data)
    assert DnsnLedgerEntry.objects.filter(voucher=tt58_voucher).count() == 1

    service.unpost(tt58_voucher)
    tt58_voucher.refresh_from_db()
    assert tt58_voucher.status == "draft"

    # Entries should be deleted/reversed
    assert DnsnLedgerEntry.objects.filter(voucher=tt58_voucher).count() == 0

    # Balance should be zero
    bal = DnsnLedgerBalance.objects.get(
        company=tt58_voucher.company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert bal.closing_revenue == Decimal("0")


@pytest.mark.django_db
def test_posting_service_locked_voucher_raises(tt58_company):
    """Posting a locked voucher raises DnsnVoucherLockedError."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status="locked",
    )
    service = DnsnPostingService()
    with pytest.raises(DnsnVoucherLockedError):
        service.post(v, entries=[])


@pytest.mark.django_db
def test_posting_service_unpost_idempotent(tt58_voucher):
    """Unposting an already-draft voucher is a no-op."""
    service = DnsnPostingService()
    # Not posted yet
    service.unpost(tt58_voucher)
    tt58_voucher.refresh_from_db()
    assert tt58_voucher.status == "draft"


@pytest.mark.django_db
def test_posting_running_balance_computed(tt58_company):
    """VAL-TT58-020: Running balance is computed for ledger entries."""
    service = DnsnPostingService()

    # Post first voucher
    v1 = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    service.post(
        v1,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Thu tien lan 1",
                "cash_in": Decimal("500000"),
            },
        ],
    )

    # Post second voucher
    v2 = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0002",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 2),
    )
    service.post(
        v2,
        entries=[
            {
                "ledger_type": "s2d",
                "description": "Thu tien lan 2",
                "cash_in": Decimal("300000"),
            },
        ],
    )

    entries = list(
        DnsnLedgerEntry.objects.filter(
            company=tt58_company,
            fiscal_year=2026,
            period=7,
            ledger_type="s2d",
        ).order_by("entry_date", "id")
    )

    assert len(entries) == 2
    # Running balance should be cumulative
    assert entries[0].running_balance == Decimal("500000")
    assert entries[1].running_balance == Decimal("800000")


@pytest.mark.django_db
def test_posting_multiple_entries_different_ledgers(tt58_voucher):
    """Posting creates entries in different ledger types from one voucher."""
    service = DnsnPostingService()
    entry_data = [
        {
            "ledger_type": "s2a",
            "description": "Doanh thu",
            "revenue_amount": Decimal("1000000"),
        },
        {
            "ledger_type": "s2d",
            "description": "Tien thu",
            "cash_in": Decimal("1000000"),
        },
    ]
    service.post(tt58_voucher, entries=entry_data)

    assert DnsnLedgerEntry.objects.filter(voucher=tt58_voucher).count() == 2

    bal_s2a = DnsnLedgerBalance.objects.get(
        company=tt58_voucher.company,
        fiscal_year=2026,
        period=7,
        ledger_type="s2a",
    )
    assert bal_s2a.closing_revenue == Decimal("1000000")

    bal_s2d = DnsnLedgerBalance.objects.get(
        company=tt58_voucher.company,
        fiscal_year=2026,
        period=7,
        ledger_type="s2d",
    )
    assert bal_s2d.closing_cash == Decimal("1000000")


@pytest.mark.django_db
def test_posting_accumulates_balance_across_vouchers(tt58_company):
    """Multiple vouchers accumulate into the same balance row."""
    service = DnsnPostingService()

    for i in range(3):
        v = DnsnVoucher.objects.create(
            company=tt58_company,
            fiscal_year=2026,
            period=7,
            voucher_no=f"PT{i:04d}",
            voucher_type="phieu_thu",
            voucher_date=date(2026, 7, 1 + i),
        )
        service.post(
            v,
            entries=[
                {
                    "ledger_type": "s1",
                    "description": f"Doanh thu {i}",
                    "revenue_amount": Decimal("500000"),
                },
            ],
        )

    bal = DnsnLedgerBalance.objects.get(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        ledger_type="s1",
    )
    assert bal.closing_revenue == Decimal("1500000")
