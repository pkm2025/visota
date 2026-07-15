"""Tests for TaxRateConfig + TaxConfigService (ND 80/2021, ND 174/2025, Luật TNDN 2025)."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company, LegalReference, TaxRateConfig
from apps.core.services.tax_config_service import TaxConfigService


@pytest.fixture
def tax_config(db):
    TaxRateConfig.objects.filter(is_active=True).delete()
    return TaxRateConfig.objects.create(
        is_active=True,
        cit_rate_standard=Decimal("0.20"),
        cit_rate_small=Decimal("0.17"),
        cit_rate_micro=Decimal("0.15"),
        vat_rate_standard=Decimal("0.10"),
        vat_rate_reduced=Decimal("0.08"),
        vat_rate_reduced_active=True,
        pit_personal_deduction=Decimal("11000000"),
        pit_dependent_deduction=Decimal("4400000"),
        bhxh_cap=Decimal("50600000"),
        bhxh_base_salary=Decimal("2530000"),
        effective_date=date(2025, 7, 1),
    )


def test_default_vat_rate_8_percent(db, tax_config):
    """VAT should be 8% during reduced period (ND 174/2025)."""
    rate = TaxConfigService.get_vat_rate(is_reduced=True)
    assert rate == Decimal("0.08")


def test_vat_rate_10_when_not_reduced(db, tax_config):
    """VAT should be 10% when not in reduced scope."""
    rate = TaxConfigService.get_vat_rate(is_reduced=False)
    assert rate == Decimal("0.10")


def test_vat_rate_10_when_reduced_disabled(db, tax_config):
    """VAT should be 10% when reduced period inactive."""
    tax_config.vat_rate_reduced_active = False
    tax_config.save()
    rate = TaxConfigService.get_vat_rate(is_reduced=True)
    assert rate == Decimal("0.10")


def test_cit_rate_micro(db, tax_config):
    """Micro enterprise (DT <=3 tỷ) -> CIT 15%."""
    company = Company(sme_size="micro")
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.15")


def test_cit_rate_small(db, tax_config):
    """Small enterprise (DT 3-50 tỷ) -> CIT 17%."""
    company = Company(sme_size="small")
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.17")


def test_cit_rate_large(db, tax_config):
    """Large enterprise -> CIT 20%."""
    company = Company(sme_size="large")
    rate = TaxConfigService.get_cit_rate(company)
    assert rate == Decimal("0.20")


def test_sme_classification_micro(db):
    """Revenue <= 3 tỷ -> micro."""
    size = TaxConfigService.classify_sme(
        annual_revenue=Decimal("2000000000"),
        total_capital=Decimal("1000000000"),
        employee_count=5,
        sector="service",
    )
    assert size == "micro"


def test_sme_classification_small(db):
    """Revenue 10 tỷ (service) -> small."""
    size = TaxConfigService.classify_sme(
        annual_revenue=Decimal("10000000000"),
        total_capital=Decimal("5000000000"),
        employee_count=30,
        sector="service",
    )
    assert size == "small"


def test_sme_classification_medium(db):
    """Revenue 100 tỷ -> medium."""
    size = TaxConfigService.classify_sme(
        annual_revenue=Decimal("100000000000"),
        total_capital=Decimal("50000000000"),
        employee_count=150,
        sector="commerce",
    )
    assert size == "medium"


def test_sme_classification_large(db):
    """Revenue > 200 tỷ -> large."""
    size = TaxConfigService.classify_sme(
        annual_revenue=Decimal("500000000000"),
        total_capital=Decimal("200000000000"),
        employee_count=400,
        sector="commerce",
    )
    assert size == "large"


def test_company_default_sme_size(db):
    """Company defaults to 'small'."""
    c = Company(code="TS1", name="TS1", tax_code="0101234567", accounting_regime="tt133")
    assert c.sme_size == "small"
    assert c.annual_revenue == Decimal("0")


def test_legal_ref_count(db):
    """Should have 20+ legal references after seeding."""
    from django.core.management import call_command

    LegalReference.objects.all().delete()
    call_command("seed_legal_references", verbosity=0)
    assert LegalReference.objects.filter(status="active").count() >= 20


def test_legal_ref_has_vat_reduction_entry(db):
    """ND 174/2025 (VAT 8%) must be seeded."""
    from django.core.management import call_command

    LegalReference.objects.all().delete()
    call_command("seed_legal_references", verbosity=0)
    assert LegalReference.objects.filter(code="ND174").exists()
    assert LegalReference.objects.filter(code="ND80").exists()
    assert LegalReference.objects.filter(code="LuatTNDN2025").exists()
