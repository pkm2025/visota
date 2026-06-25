"""Tests for FX module: exchange rate, period-end revaluation."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.fx.models import Currency, ExchangeRate, FxRevaluationBatch
from apps.fx.services import FxRevaluationService


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTFX", name="Test FX Co")


# ---------- Currency ----------

@pytest.mark.django_db
def test_currency_str():
    c = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
    assert "USD" in str(c)
    assert "US Dollar" in str(c)


@pytest.mark.django_db
def test_currency_primary_key_is_code():
    Currency.objects.create(code="EUR", name="Euro")
    assert Currency.objects.get(pk="EUR").name == "Euro"


# ---------- ExchangeRate ----------

@pytest.mark.django_db
def test_exchange_rate_str(company):
    er = ExchangeRate.objects.create(
        company=company, from_currency="USD", to_currency="VND",
        rate_date=date(2026, 6, 23), rate=Decimal("24500"),
    )
    assert "USD" in str(er)
    assert "24,500" in str(er)


@pytest.mark.django_db
def test_exchange_rate_unique_per_day(company):
    ExchangeRate.objects.create(
        company=company, from_currency="USD", to_currency="VND",
        rate_date=date(2026, 6, 23), rate=Decimal("24500"),
    )
    with pytest.raises(Exception):
        ExchangeRate.objects.create(
            company=company, from_currency="USD", to_currency="VND",
            rate_date=date(2026, 6, 23), rate=Decimal("24600"),
        )


@pytest.mark.django_db
def test_get_closing_rate_returns_vnd_one(company):
    """VND rate is always 1."""
    rate = FxRevaluationService.get_closing_rate(company, "VND", date(2026, 6, 30))
    assert rate == Decimal("1")


@pytest.mark.django_db
def test_get_closing_rate_returns_latest_in_db(company):
    ExchangeRate.objects.create(
        company=company, from_currency="USD", to_currency="VND",
        rate_date=date(2026, 6, 1), rate=Decimal("24000"),
    )
    ExchangeRate.objects.create(
        company=company, from_currency="USD", to_currency="VND",
        rate_date=date(2026, 6, 15), rate=Decimal("24500"),
    )
    rate = FxRevaluationService.get_closing_rate(company, "USD", date(2026, 6, 30))
    assert rate == Decimal("24500")  # latest before valuation_date


@pytest.mark.django_db
def test_get_closing_rate_returns_none_if_no_data(company):
    rate = FxRevaluationService.get_closing_rate(company, "EUR", date(2026, 6, 30))
    assert rate is None


# ---------- Revaluation ----------

@pytest.mark.django_db
def test_run_revaluation_creates_batch_and_voucher(company):
    """Empty company → revaluation runs without error, creates empty voucher."""
    batch = FxRevaluationService.run_revaluation(company, 2026, 6)
    assert batch.period_year == 2026
    assert batch.period_month == 6
    assert batch.valuation_date == date(2026, 6, 30)
    assert batch.status == FxRevaluationBatch.Status.POSTED
    assert batch.gl_voucher is not None
    assert batch.reference_rate == {}  # no FX data


@pytest.mark.django_db
def test_run_revaluation_creates_batch_per_run(company):
    """Each run creates a new batch (unique constraint is per period so we use different periods)."""
    FxRevaluationService.run_revaluation(company, 2026, 5)
    FxRevaluationService.run_revaluation(company, 2026, 6)
    assert FxRevaluationBatch.objects.filter(period_year=2026).count() == 2


@pytest.mark.django_db
def test_run_revaluation_with_fx_balances_and_rates(company):
    """Full happy path: voucher with USD lines + closing rate → gain/loss voucher."""
    from apps.ledger.models import AccountingVoucher, VoucherLine

    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=5,
        voucher_no="V-USD-1", voucher_type="journal",
        voucher_date=date(2026, 5, 15),
        currency_code="USD", exchange_rate=Decimal("24000"),
        total_vnd=Decimal("24000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="131",
        debit_vnd=Decimal("24000000"),
    )

    ExchangeRate.objects.create(
        company=company, from_currency="USD", to_currency="VND",
        rate_date=date(2026, 6, 15), rate=Decimal("24500"),
    )

    batch = FxRevaluationService.run_revaluation(company, 2026, 6)
    assert batch.gl_voucher is not None
    assert "USD" in batch.reference_rate
    assert batch.reference_rate["USD"] == 24500.0
