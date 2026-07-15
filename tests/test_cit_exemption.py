"""Tests for CIT exemption per ND 141/2026 (revenue <= 1 billion VND/year = 0% CIT).

Covers VAL-CIT-001, VAL-CIT-002, VAL-CIT-003.
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
        pit_personal_deduction=Decimal("15500000"),
        pit_dependent_deduction=Decimal("6200000"),
        bhxh_cap=Decimal("50600000"),
        bhxh_base_salary=Decimal("2530000"),
        effective_date=date(2026, 7, 1),
    )


# --- VAL-CIT-003: CIT exemption threshold stored in TaxRateConfig ---


def test_cit_exemption_threshold_field_exists_with_default(db):
    """TaxRateConfig must have cit_exemption_threshold with default 1,000,000,000."""
    config = TaxRateConfig.objects.create(
        effective_date=date(2026, 1, 1),
        is_active=False,
    )
    assert config.cit_exemption_threshold == Decimal("1000000000")


def test_cit_exemption_threshold_default_value(db, tax_config):
    """Seeded config has exemption threshold = 1 billion."""
    assert tax_config.cit_exemption_threshold == Decimal("1000000000")


# --- VAL-CIT-001: CIT exemption for revenue <= 1 billion VND/year ---


def test_cit_exempt_for_revenue_at_threshold(db, tax_config):
    """Company with revenue exactly 1B VND -> CIT 0% (exempt per ND 141/2026)."""
    company = Company(sme_size="micro", annual_revenue=Decimal("1000000000"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0")


def test_cit_exempt_for_revenue_below_threshold(db, tax_config):
    """Company with revenue below 1B VND -> CIT 0%."""
    company = Company(sme_size="micro", annual_revenue=Decimal("500000000"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0")


def test_cit_exempt_for_zero_revenue(db, tax_config):
    """Company with zero revenue -> CIT 0%."""
    company = Company(sme_size="micro", annual_revenue=Decimal("0"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0")


# --- VAL-CIT-002: CIT tiered rate for revenue > 1 billion ---


def test_cit_micro_rate_for_revenue_above_threshold(db, tax_config):
    """Company with revenue > 1B and micro size -> CIT 15%."""
    company = Company(sme_size="micro", annual_revenue=Decimal("2000000000"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.15")


def test_cit_small_rate_for_revenue_above_threshold(db, tax_config):
    """Company with revenue > 1B and small size -> CIT 17%."""
    company = Company(sme_size="small", annual_revenue=Decimal("10000000000"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.17")


def test_cit_standard_rate_for_large_above_threshold(db, tax_config):
    """Company with revenue > 1B and large size -> CIT 20%."""
    company = Company(sme_size="large", annual_revenue=Decimal("100000000000"))
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.20")
