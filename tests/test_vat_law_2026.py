"""Tests for VAT law 09/2026 provisions (exemption + refund thresholds).

Covers VAL-VAT-001, VAL-VAT-002, VAL-VAT-003.

Luật GTGT 09/2026:
- Revenue < 1 billion VND/year = VAT exempt
- Input VAT >= 300 million VND = eligible for VAT refund
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company, TaxRateConfig
from apps.core.services.tax_config_service import TaxConfigService


@pytest.fixture
def tax_config(db):
    TaxRateConfig.objects.filter(is_active=True).delete()
    return TaxRateConfig.objects.create(
        is_active=True,
        cit_rate_standard=Decimal("0.20"),
        cit_rate_small=Decimal("0.17"),
        cit_rate_micro=Decimal("0.15"),
        cit_exemption_threshold=Decimal("1000000000"),
        vat_rate_standard=Decimal("0.10"),
        vat_rate_reduced=Decimal("0.08"),
        vat_rate_reduced_active=True,
        vat_exemption_threshold=Decimal("1000000000"),
        vat_refund_threshold=Decimal("300000000"),
        pit_personal_deduction=Decimal("15500000"),
        pit_dependent_deduction=Decimal("6200000"),
        bhxh_cap=Decimal("50600000"),
        bhxh_base_salary=Decimal("2530000"),
        effective_date=date(2026, 7, 1),
    )


# --- VAL-VAT-003: VAT exemption threshold stored in TaxRateConfig ---


def test_vat_exemption_threshold_field_exists_with_default(db):
    """TaxRateConfig must have vat_exemption_threshold with default 1,000,000,000."""
    config = TaxRateConfig.objects.create(
        effective_date=date(2026, 1, 1),
        is_active=False,
    )
    assert config.vat_exemption_threshold == Decimal("1000000000")


def test_vat_refund_threshold_field_exists_with_default(db):
    """TaxRateConfig must have vat_refund_threshold with default 300,000,000."""
    config = TaxRateConfig.objects.create(
        effective_date=date(2026, 1, 1),
        is_active=False,
    )
    assert config.vat_refund_threshold == Decimal("300000000")


def test_vat_exemption_threshold_value_in_seeded_config(db, tax_config):
    """Seeded config has VAT exemption threshold = 1 billion."""
    assert tax_config.vat_exemption_threshold == Decimal("1000000000")


def test_vat_refund_threshold_value_in_seeded_config(db, tax_config):
    """Seeded config has VAT refund threshold = 300 million."""
    assert tax_config.vat_refund_threshold == Decimal("300000000")


# --- VAL-VAT-001: VAT exemption threshold is 1 billion VND/year ---


def test_is_vat_exempt_for_revenue_below_threshold(db, tax_config):
    """Company with revenue < 1B VND/year qualifies for VAT exemption."""
    company = Company(annual_revenue=Decimal("500000000"))
    assert TaxConfigService.is_vat_exempt(company) is True


def test_is_vat_exempt_for_zero_revenue(db, tax_config):
    """Company with zero revenue qualifies for VAT exemption."""
    company = Company(annual_revenue=Decimal("0"))
    assert TaxConfigService.is_vat_exempt(company) is True


def test_is_vat_exempt_for_revenue_at_threshold(db, tax_config):
    """Company with revenue exactly at 1B VND/year qualifies for VAT exemption (<=)."""
    company = Company(annual_revenue=Decimal("1000000000"))
    assert TaxConfigService.is_vat_exempt(company) is True


def test_not_vat_exempt_for_revenue_above_threshold(db, tax_config):
    """Company with revenue > 1B VND/year does NOT qualify for VAT exemption."""
    company = Company(annual_revenue=Decimal("1000000001"))
    assert TaxConfigService.is_vat_exempt(company) is False


def test_not_vat_exempt_for_large_revenue(db, tax_config):
    """Large company with high revenue does NOT qualify for VAT exemption."""
    company = Company(annual_revenue=Decimal("50000000000"))
    assert TaxConfigService.is_vat_exempt(company) is False


# --- VAL-VAT-002: VAT refund threshold is 300 million VND ---


def test_is_vat_refund_eligible_at_threshold(db, tax_config):
    """Company with input VAT exactly 300M qualifies for VAT refund."""
    company = Company(annual_revenue=Decimal("5000000000"))
    assert TaxConfigService.is_vat_refund_eligible(company, input_vat=Decimal("300000000")) is True


def test_is_vat_refund_eligible_above_threshold(db, tax_config):
    """Company with input VAT > 300M qualifies for VAT refund."""
    company = Company(annual_revenue=Decimal("5000000000"))
    assert TaxConfigService.is_vat_refund_eligible(company, input_vat=Decimal("500000000")) is True


def test_not_vat_refund_eligible_below_threshold(db, tax_config):
    """Company with input VAT < 300M does NOT qualify for VAT refund."""
    company = Company(annual_revenue=Decimal("5000000000"))
    assert TaxConfigService.is_vat_refund_eligible(company, input_vat=Decimal("299999999")) is False


def test_not_vat_refund_eligible_zero_input_vat(db, tax_config):
    """Company with zero input VAT does NOT qualify for VAT refund."""
    company = Company(annual_revenue=Decimal("5000000000"))
    assert TaxConfigService.is_vat_refund_eligible(company, input_vat=Decimal("0")) is False


def test_not_vat_refund_eligible_exempt_company(db, tax_config):
    """VAT-exempt company (revenue < 1B) does NOT qualify for VAT refund."""
    company = Company(annual_revenue=Decimal("500000000"))
    assert TaxConfigService.is_vat_refund_eligible(company, input_vat=Decimal("500000000")) is False
