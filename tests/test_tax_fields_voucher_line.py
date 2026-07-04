"""Tests for M1 tax fields on VoucherLine + TaxRateCode + InvoiceGroup + posting.

Covers VAL-M1-001 through VAL-M1-010 backend assertions.
"""

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.utils import IntegrityError

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.master_data.models import InvoiceGroup, TaxRateCode

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TCO",
        name="Test Co",
        fiscal_year_start_month=1,
    )


@pytest.fixture
def seeded(db):
    call_command("seed_tax_rates")
    call_command("seed_invoice_groups")


# ── TaxRateCode ───────────────────────────────────────────────────────────


def test_tax_rate_code_unique(db):
    TaxRateCode.objects.create(code="10", rate=Decimal("10"), display_name="10%")
    with pytest.raises(IntegrityError):
        TaxRateCode.objects.create(code="10", rate=Decimal("99"), display_name="dup")


def test_tax_rate_code_rate_range(db):
    obj = TaxRateCode(code="X", rate=Decimal("-1"), display_name="bad")
    with pytest.raises(ValidationError):
        obj.full_clean()
    obj2 = TaxRateCode(code="Y", rate=Decimal("101"), display_name="bad")
    with pytest.raises(ValidationError):
        obj2.full_clean()
    ok = TaxRateCode(code="0", rate=Decimal("0"), display_name="zero")
    ok.full_clean()
    ok100 = TaxRateCode(code="100p", rate=Decimal("100"), display_name="hundred")
    ok100.full_clean()


def test_tax_rate_code_decimal_precision(db):
    obj = TaxRateCode.objects.create(code="85", rate=Decimal("8.50"), display_name="8.5%")
    obj.refresh_from_db()
    assert obj.rate == Decimal("8.50")
    field = TaxRateCode._meta.get_field("rate")
    assert field.max_digits == 5
    assert field.decimal_places == 2


def test_seed_creates_8_codes(seeded):
    codes = list(TaxRateCode.objects.values_list("code", flat=True))
    expected = {"00", "05", "04", "10", "08", "KT", "TS05", "kht"}
    assert set(codes) == expected
    assert TaxRateCode.objects.count() == 8


def test_seed_idempotent(seeded):
    n1 = TaxRateCode.objects.count()
    call_command("seed_tax_rates")
    n2 = TaxRateCode.objects.count()
    assert n1 == n2 == 8


def test_tax_rate_code_rate_for_10(seeded):
    t = TaxRateCode.objects.get(code="10")
    assert t.rate == Decimal("10.00")


# ── InvoiceGroup ──────────────────────────────────────────────────────────


def test_invoice_group_seed(seeded):
    codes = list(InvoiceGroup.objects.values_list("code", flat=True))
    assert set(codes) == {"4", "5", "6"}
    assert InvoiceGroup.objects.count() == 3


def test_invoice_group_idempotent(seeded):
    n1 = InvoiceGroup.objects.count()
    call_command("seed_invoice_groups")
    n2 = InvoiceGroup.objects.count()
    assert n1 == n2 == 3


def test_invoice_group_unique(db):
    InvoiceGroup.objects.create(code="4", name_vi="INPUT")
    with pytest.raises(IntegrityError):
        InvoiceGroup.objects.create(code="4", name_vi="dup")


def test_invoice_group_4_input_defaults(seeded):
    g = InvoiceGroup.objects.get(code="4")
    assert g.default_tax_account_debit == "1331"
    assert g.default_tax_account_credit == "331"


def test_invoice_group_5_output_defaults(seeded):
    g = InvoiceGroup.objects.get(code="5")
    assert g.default_tax_account_credit == "33311"
    assert g.default_tax_account_debit == "131"


# ── VoucherLine FK references ─────────────────────────────────────────────


def test_voucher_line_has_tax_fields():
    """VAL: VoucherLine has 12 new tax fields."""
    expected_fields = {
        "invoice_no",
        "invoice_date",
        "invoice_form",
        "invoice_symbol",
        "invoice_serial",
        "tax_code",
        "tax_rate",
        "goods_amount_vnd",
        "tax_amount_vnd",
        "offset_account_code",
        "invoice_group_code",
        "object_address",
    }
    actual = {f.name for f in VoucherLine._meta.get_fields()}
    missing = expected_fields - actual
    assert not missing, f"Missing fields: {missing}"


def test_voucher_line_tax_code_fk_roundtrip(company, seeded):
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="T-1",
        voucher_type="journal",
        voucher_date=datetime.date(2026, 6, 1),
        status=AccountingVoucher.Status.DRAFT,
    )
    tax = TaxRateCode.objects.get(code="10")
    line = VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="642",
        tax_code=tax,
        tax_rate=Decimal("10"),
        goods_amount_vnd=Decimal("1000000"),
        tax_amount_vnd=Decimal("100000"),
    )
    line.refresh_from_db()
    assert line.tax_code_id == tax.code
    assert line.tax_code.code == "10"
    assert line.goods_amount_vnd == Decimal("1000000")


def test_voucher_line_invoice_group_fk_roundtrip(company, seeded):
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="T-2",
        voucher_type="journal",
        voucher_date=datetime.date(2026, 6, 1),
        status=AccountingVoucher.Status.DRAFT,
    )
    grp = InvoiceGroup.objects.get(code="4")
    line = VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="642",
        invoice_group_code=grp,
        invoice_no="HD-001",
    )
    line.refresh_from_db()
    assert line.invoice_group_code_id == grp.code
    assert line.invoice_group_code.code == "4"


# ── Posting service tax logic ─────────────────────────────────────────────


def _make_voucher_with_input_tax(company, seeded, tax_amount=Decimal("100000")):
    """Voucher with INPUT tax line. Manual voucher: line1 debits 642 1.1M,
    line2 credits 111 1.1M (balanced). Plus a tax line marking INPUT 100K."""
    grp_input = InvoiceGroup.objects.get(code="4")
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=f"TX-{company.pk}-{AccountingVoucher.objects.count() + 1}",
        voucher_type="journal",
        voucher_date=datetime.date(2026, 6, 15),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="642",
        debit_vnd=Decimal("1100000"),
        credit_vnd=Decimal("0"),
        invoice_group_code=grp_input,
        tax_amount_vnd=tax_amount,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="111",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("1100000"),
    )
    return v


def test_post_input_tax_creates_1331(company, seeded):
    """VAL-M1-005: INPUT tax lines generate TK 1331 debit."""
    v = _make_voucher_with_input_tax(company, seeded)
    VoucherPostingService().post(v)
    tax_lines = VoucherLine.objects.filter(voucher=v, account_code="1331")
    assert tax_lines.count() >= 1
    total = sum(tl.debit_vnd for tl in tax_lines)
    assert total == Decimal("100000")


def test_post_output_tax_creates_33311(company, seeded):
    """VAL-M1-005: OUTPUT tax lines generate TK 33311 credit."""
    grp_output = InvoiceGroup.objects.get(code="5")
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=f"OUT-{company.pk}-{AccountingVoucher.objects.count() + 1}",
        voucher_type="journal",
        voucher_date=datetime.date(2026, 6, 15),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="131",
        debit_vnd=Decimal("1100000"),
        credit_vnd=Decimal("0"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="5111",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("1100000"),
        invoice_group_code=grp_output,
        tax_amount_vnd=Decimal("100000"),
    )
    VoucherPostingService().post(v)
    tax_lines = VoucherLine.objects.filter(voucher=v, account_code="33311")
    assert tax_lines.count() >= 1
    total = sum(tl.credit_vnd for tl in tax_lines)
    assert total == Decimal("100000")


def test_unpost_removes_tax_postings(company, seeded):
    """VAL-M1-008: unpost removes auto-generated 1331/33311 lines."""
    v = _make_voucher_with_input_tax(company, seeded)
    service = VoucherPostingService()
    service.post(v)
    assert VoucherLine.objects.filter(voucher=v, account_code="1331").exists()

    service.unpost(v)

    assert VoucherLine.objects.filter(voucher=v, account_code="1331").count() == 0
    assert VoucherLine.objects.filter(voucher=v, is_auto_tax_posting=True).count() == 0

    bal = AccountPeriodBalance.objects.get(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="1331",
    )
    assert bal.period_debit == Decimal("0")
    v.refresh_from_db()
    assert not v.is_posted


def test_post_without_tax_lines_no_extra_lines(company, seeded):
    """VAL-M1-010: voucher without tax lines produces no 1331/33311 rows."""
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=f"NT-{company.pk}-{AccountingVoucher.objects.count() + 1}",
        voucher_type="journal",
        voucher_date=datetime.date(2026, 6, 15),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="111",
        debit_vnd=Decimal("1000"),
        credit_vnd=Decimal("0"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="5111",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("1000"),
    )
    VoucherPostingService().post(v)
    assert VoucherLine.objects.filter(voucher=v, account_code__startswith="1331").count() == 0
    assert VoucherLine.objects.filter(voucher=v, account_code__startswith="33311").count() == 0
    assert VoucherLine.objects.filter(voucher=v, is_auto_tax_posting=True).count() == 0


def test_post_idempotent_on_repost(company, seeded):
    """VAL-M1-007: reposting should be idempotent (no double counting)."""
    v = _make_voucher_with_input_tax(company, seeded)
    service = VoucherPostingService()
    service.post(v)
    # Unpost then post again
    service.unpost(v)
    service.post(v)
    tax_lines = VoucherLine.objects.filter(voucher=v, account_code="1331")
    assert tax_lines.count() == 1
    assert tax_lines.first().debit_vnd == Decimal("100000")


def test_trial_balance_reflects_tax_posting(company, seeded):
    """VAL-M1-006: AccountPeriodBalance for 1331 has period_debit."""
    v = _make_voucher_with_input_tax(company, seeded)
    VoucherPostingService().post(v)
    bal = AccountPeriodBalance.objects.get(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="1331",
    )
    assert bal.period_debit == Decimal("100000")
    assert bal.closing_debit == Decimal("100000")


def test_post_zero_tax_amount_no_line(company, seeded):
    """Tax line with tax_amount_vnd=0 generates no auto posting."""
    v = _make_voucher_with_input_tax(company, seeded, tax_amount=Decimal("0"))
    VoucherPostingService().post(v)
    assert VoucherLine.objects.filter(voucher=v, account_code="1331").count() == 0
