"""Tests for TT58 BalanceConversionService.

Covers VAL-TT58-038, VAL-TT58-039, VAL-TT58-040, VAL-TT58-041:
- VAL-TT58-038: Convert TT132 balances to TT58 opening balances
- VAL-TT58-039: Convert TT133 balances to TT58 opening balances
- VAL-TT58-040: Balance conversion is idempotent
- VAL-TT58-041: Conversion summary report shows source/target mapping
"""

from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.ledger.models import (
    AccountPeriodBalance,
    DnsnLedgerBalance,
)
from apps.ledger.services.balance_conversion_service import (
    BalanceConversionService,
    ConversionSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt132_company(db):
    """A company with TT132 regime and AccountPeriodBalance data."""
    company = Company.objects.create(
        code="CV132",
        name="TT132 Conversion Co",
        accounting_regime="tt133",  # TT132 uses same codes as TT133
    )
    # Create AccountPeriodBalance records matching the conversion mapping
    # TK 111 (cash) → S2d
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="111",
        closing_debit=Decimal("100000000"),
    )
    # TK 112 (bank) → S2d
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="112",
        closing_debit=Decimal("50000000"),
    )
    # TK 131 (receivables) → S4a
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="131",
        closing_debit=Decimal("30000000"),
    )
    # TK 1521 (inventory) → S2c
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="1521",
        closing_debit=Decimal("40000000"),
    )
    # TK 211 (fixed assets) → S4b
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="211",
        closing_debit=Decimal("200000000"),
    )
    # TK 1331 (input VAT) → S3b
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="1331",
        closing_debit=Decimal("5000000"),
    )
    # TK 3311 (payables) → S4a
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="3311",
        closing_credit=Decimal("40000000"),
    )
    # TK 33311 (output VAT) → S3b
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="33311",
        closing_credit=Decimal("10000000"),
    )
    # TK 33334 (other taxes) → S4c
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="33334",
        closing_credit=Decimal("5000000"),
    )
    # TK 411 (owner's equity) → S4d
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=1,
        account_code="411",
        closing_credit=Decimal("480000000"),
    )
    return company


@pytest.fixture
def tt133_company(db):
    """A company with TT133 regime and AccountPeriodBalance data."""
    company = Company.objects.create(
        code="CV133",
        name="TT133 Conversion Co",
        accounting_regime="tt133",
    )
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="111",
        closing_debit=Decimal("50000000"),
    )
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="411",
        closing_credit=Decimal("50000000"),
    )
    return company


@pytest.fixture
def empty_company(db):
    """A TT133 company with no balance data."""
    return Company.objects.create(
        code="CVEMPTY",
        name="Empty Conversion Co",
        accounting_regime="tt133",
    )


# ---------------------------------------------------------------------------
# Conversion tests — VAL-TT58-038, VAL-TT58-039
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_convert_tt132_balances_to_tt58(tt132_company):
    """VAL-TT58-038: Convert TT132 account balances to TT58 DNSN ledger opening balances."""
    service = BalanceConversionService()
    service.convert(tt132_company, fiscal_year=2026, source_period=1)

    # Should create DnsnLedgerBalance for each target ledger type
    # S2d (TK 111 + 112), S4a (TK 131 + 3311), S2c (TK 1521), S4b (TK 211),
    # S3b (TK 1331 + 33311), S4c (TK 33334), S4d (TK 411)
    balances = DnsnLedgerBalance.objects.filter(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
    )
    ledger_types = set(balances.values_list("ledger_type", flat=True))
    assert "s2d" in ledger_types
    assert "s4a" in ledger_types
    assert "s2c" in ledger_types
    assert "s4b" in ledger_types
    assert "s3b" in ledger_types
    assert "s4c" in ledger_types
    assert "s4d" in ledger_types

    # Verify specific mapping amounts
    bal_s2d = balances.get(ledger_type="s2d")
    # TK 111 (100M) + TK 112 (50M) = 150M
    assert bal_s2d.opening_cash == Decimal("150000000")

    bal_s2c = balances.get(ledger_type="s2c")
    assert bal_s2c.opening_revenue == Decimal("40000000")

    bal_s4b = balances.get(ledger_type="s4b")
    assert bal_s4b.opening_cash == Decimal("200000000")

    bal_s4d = balances.get(ledger_type="s4d")
    assert bal_s4d.opening_cash == Decimal("480000000")


@pytest.mark.django_db
def test_convert_tt133_balances_to_tt58(tt133_company):
    """VAL-TT58-039: Convert TT133 AccountPeriodBalance to TT58 ledger opening balances."""
    service = BalanceConversionService()
    service.convert(tt133_company, fiscal_year=2026, source_period=6)

    balances = DnsnLedgerBalance.objects.filter(
        company=tt133_company,
        fiscal_year=2026,
        period=6,
    )
    assert balances.exists()

    # TK 111 → S2d
    bal_s2d = balances.get(ledger_type="s2d")
    assert bal_s2d.opening_cash == Decimal("50000000")

    # TK 411 → S4d
    bal_s4d = balances.get(ledger_type="s4d")
    assert bal_s4d.opening_cash == Decimal("50000000")


@pytest.mark.django_db
def test_convert_tt132_specific_mappings(tt132_company):
    """Test each specific account mapping produces correct ledger amounts."""
    service = BalanceConversionService()
    service.convert(tt132_company, fiscal_year=2026, source_period=1)

    balances = {
        b.ledger_type: b
        for b in DnsnLedgerBalance.objects.filter(
            company=tt132_company,
            fiscal_year=2026,
            period=1,
        )
    }

    # S2d: TK 111 (100M) + TK 112 (50M) = 150M (asset: debit)
    assert balances["s2d"].opening_cash == Decimal("150000000")

    # S4a: TK 131 (30M debit = receivable) - TK 3311 (40M credit = payable)
    # Net receivables - payables stored in opening_cash
    assert balances["s4a"].opening_cash == Decimal("30000000")
    assert balances["s4a"].opening_cost == Decimal("40000000")

    # S2c: TK 1521 = 40M
    assert balances["s2c"].opening_revenue == Decimal("40000000")

    # S4b: TK 211 = 200M
    assert balances["s4b"].opening_cash == Decimal("200000000")

    # S3b: TK 1331 (5M debit = input VAT) + TK 33311 (10M credit = output VAT) = 15M total
    assert balances["s3b"].opening_vat == Decimal("15000000")

    # S4c: TK 33334 = 5M (credit = payable tax)
    assert balances["s4c"].opening_vat == Decimal("5000000")

    # S4d: TK 411 = 480M
    assert balances["s4d"].opening_cash == Decimal("480000000")


@pytest.mark.django_db
def test_convert_sets_closing_equal_to_opening(tt132_company):
    """After conversion, closing balances equal opening (no period activity yet)."""
    service = BalanceConversionService()
    service.convert(tt132_company, fiscal_year=2026, source_period=1)

    for bal in DnsnLedgerBalance.objects.filter(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
    ):
        assert bal.closing_cash == bal.opening_cash
        assert bal.closing_revenue == bal.opening_revenue
        assert bal.closing_cost == bal.opening_cost
        assert bal.closing_vat == bal.opening_vat


# ---------------------------------------------------------------------------
# Idempotency — VAL-TT58-040
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_conversion_is_idempotent(tt132_company):
    """VAL-TT58-040: Running conversion twice produces no duplicates."""
    service = BalanceConversionService()

    # First run
    service.convert(tt132_company, fiscal_year=2026, source_period=1)
    count1 = DnsnLedgerBalance.objects.filter(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
    ).count()

    # Second run
    summary2 = service.convert(tt132_company, fiscal_year=2026, source_period=1)
    count2 = DnsnLedgerBalance.objects.filter(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
    ).count()

    assert count1 == count2
    assert summary2.converted_count == 0  # No new conversions on second run


@pytest.mark.django_db
def test_conversion_idempotent_preserves_amounts(tt132_company):
    """Re-running conversion does not corrupt existing balances."""
    service = BalanceConversionService()

    service.convert(tt132_company, fiscal_year=2026, source_period=1)
    bal_s2d_before = DnsnLedgerBalance.objects.get(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
        ledger_type="s2d",
    )

    service.convert(tt132_company, fiscal_year=2026, source_period=1)
    bal_s2d_after = DnsnLedgerBalance.objects.get(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
        ledger_type="s2d",
    )

    assert bal_s2d_before.opening_cash == bal_s2d_after.opening_cash


# ---------------------------------------------------------------------------
# Summary report — VAL-TT58-041
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_conversion_summary_shows_source_target_mapping(tt132_company):
    """VAL-TT58-041: Summary shows source accounts, target ledgers, matching totals."""
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    assert isinstance(summary, ConversionSummary)
    assert len(summary.rows) > 0

    # Each row should have source account, source balance, target ledger, target amount
    for row in summary.rows:
        assert row.source_account_code
        assert row.source_balance is not None
        assert row.target_ledger_type
        assert row.target_ledger_label
        assert row.converted_amount is not None


@pytest.mark.django_db
def test_conversion_summary_totals_match(tt132_company):
    """VAL-TT58-041: Summary totals match between source and target."""
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    # Total source balances should equal total converted amounts
    total_source = sum(r.source_balance for r in summary.rows)
    total_target = sum(r.converted_amount for r in summary.rows)
    assert total_source == total_target

    assert summary.total_source == total_source
    assert summary.total_converted == total_target


@pytest.mark.django_db
def test_conversion_summary_contains_all_mappings(tt132_company):
    """Summary should contain all source account codes that were mapped."""
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    source_codes = {r.source_account_code for r in summary.rows}
    assert "111" in source_codes
    assert "112" in source_codes
    assert "131" in source_codes
    assert "1521" in source_codes
    assert "211" in source_codes
    assert "1331" in source_codes
    assert "3311" in source_codes
    assert "33311" in source_codes
    assert "33334" in source_codes
    assert "411" in source_codes


@pytest.mark.django_db
def test_conversion_summary_grouped_by_ledger(tt132_company):
    """Summary groups source accounts by target ledger."""
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    # Group by target ledger
    ledgers = {}
    for row in summary.rows:
        ledgers.setdefault(row.target_ledger_type, []).append(row)

    # S2d should have TK 111 and TK 112
    s2d_accounts = {r.source_account_code for r in ledgers.get("s2d", [])}
    assert "111" in s2d_accounts
    assert "112" in s2d_accounts


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_conversion_empty_company_returns_empty_summary(empty_company):
    """Converting a company with no balances returns empty summary."""
    service = BalanceConversionService()
    summary = service.convert(empty_company, fiscal_year=2026, source_period=1)

    assert summary.converted_count == 0
    assert len(summary.rows) == 0
    assert summary.total_source == Decimal("0")
    assert summary.total_converted == Decimal("0")


@pytest.mark.django_db
def test_conversion_unmapped_accounts_skipped(tt132_company):
    """Accounts not in the mapping should be skipped, not cause errors."""
    # Add an unmapped account
    AccountPeriodBalance.objects.create(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
        account_code="9999",
        closing_debit=Decimal("123456789"),
    )
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    # Unmapped account should not appear in summary
    source_codes = {r.source_account_code for r in summary.rows}
    assert "9999" not in source_codes


@pytest.mark.django_db
def test_conversion_handles_sub_accounts(tt132_company):
    """Sub-account codes (prefix match) should map correctly.

    E.g., TK 3318 (a sub of 331) maps to S4a like TK 331.
    """
    AccountPeriodBalance.objects.create(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
        account_code="3318",
        closing_credit=Decimal("15000000"),
    )
    AccountPeriodBalance.objects.create(
        company=tt132_company,
        fiscal_year=2026,
        period=1,
        account_code="1318",
        closing_debit=Decimal("8000000"),
    )

    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    source_codes = {r.source_account_code for r in summary.rows}
    assert "3318" in source_codes
    assert "1318" in source_codes

    # Both should map to S4a
    s4a_rows = [r for r in summary.rows if r.target_ledger_type == "s4a"]
    s4a_codes = {r.source_account_code for r in s4a_rows}
    assert "3318" in s4a_codes
    assert "1318" in s4a_codes


@pytest.mark.django_db
def test_conversion_returns_conversion_summary_type(tt132_company):
    """convert() returns a ConversionSummary instance."""
    service = BalanceConversionService()
    result = service.convert(tt132_company, fiscal_year=2026, source_period=1)
    assert isinstance(result, ConversionSummary)


@pytest.mark.django_db
def test_conversion_summary_has_metadata(tt132_company):
    """Summary includes company, fiscal_year, and source_period metadata."""
    service = BalanceConversionService()
    summary = service.convert(tt132_company, fiscal_year=2026, source_period=1)

    assert summary.company == tt132_company
    assert summary.fiscal_year == 2026
    assert summary.source_period == 1
