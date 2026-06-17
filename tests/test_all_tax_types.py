"""Tests for comprehensive Vietnamese tax types and TaxRateConfig extensions.

Covers Task 1/2/3 of the v1.4.0 tax system overhaul:
- TaxType master model (14 active tax types)
- TaxRateConfig: TTĐB rates, lệ phí môn bài, trước bạ, nhà thầu, PIT 2026
- LegalReference counts (>=30 active)
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.core.models import LegalReference, TaxRateConfig, TaxType
from apps.core.services.tax_config_service import TaxConfigService

# ---------------------------------------------------------------------------
# TaxType model
# ---------------------------------------------------------------------------


@pytest.fixture
def cleanup_tax_types(db):
    TaxType.objects.all().delete()


def test_tax_type_basic_create(db, cleanup_tax_types):
    """A TaxType can be created with all key fields."""
    t = TaxType.objects.create(
        code='VAT',
        name='Thuế Giá trị gia tăng (GTGT)',
        name_en='Value Added Tax',
        category='indirect',
        current_rate_text='10% (đang giảm 8% đến 31/12/2026)',
        legal_basis='Luật GTGT 2026 + ND 174/2025',
        effective_date='2026-01-01',
    )
    assert t.pk is not None
    assert t.code == 'VAT'
    assert t.category == 'indirect'
    assert t.is_active is True


def test_tax_type_code_unique(db, cleanup_tax_types):
    """TaxType.code must be unique."""
    TaxType.objects.create(
        code='VAT', name='VAT', category='indirect',
        current_rate_text='10%', effective_date='2026-01-01',
    )
    with pytest.raises(IntegrityError):
        TaxType.objects.create(
            code='VAT', name='VAT2', category='indirect',
            current_rate_text='10%', effective_date='2026-01-01',
        )


def test_tax_type_count(db, cleanup_tax_types):
    """Seed produces >=14 active tax types."""
    from django.core.management import call_command
    call_command('seed_tax_types', verbosity=0)
    assert TaxType.objects.filter(is_active=True).count() >= 14


def test_vat_type_exists(db, cleanup_tax_types):
    """VAT tax type exists with 8% in its rate text."""
    from django.core.management import call_command
    call_command('seed_tax_types', verbosity=0)
    t = TaxType.objects.get(code='VAT')
    assert '8%' in t.current_rate_text


def test_ttdb_type_exists(db, cleanup_tax_types):
    """TTĐB (SCT) tax type exists."""
    from django.core.management import call_command
    call_command('seed_tax_types', verbosity=0)
    t = TaxType.objects.get(code='SCT')
    assert t.category == 'indirect'
    assert 'rượu' in t.current_rate_text.lower() or 'bia' in t.current_rate_text.lower()


# ---------------------------------------------------------------------------
# TaxRateConfig: TTĐB / môn bài / trước bạ / nhà thầu / PIT 2026
# ---------------------------------------------------------------------------


@pytest.fixture
def tax_config(db):
    """Provide an active TaxRateConfig with new defaults."""
    TaxRateConfig.objects.filter(is_active=True).delete()
    return TaxRateConfig.objects.create(
        effective_date='2026-01-01',
        is_active=True,
        ttdb_alcohol_high=Decimal('0.65'),
        ttdb_beer=Decimal('0.65'),
        ttdb_tobacco_absolute=5000,
        fee_monbai_over_10b=3000000,
        pit_personal_deduction_2026=15500000,
        pit_dependent_deduction_2026=6200000,
        fct_cit_rate=Decimal('0.05'),
        pit_brackets_2026=[
            [5000000, 0.05],
            [10000000, 0.10],
            [18000000, 0.15],
            [32000000, 0.20],
            [999999999, 0.25],
        ],
    )


def test_ttdb_rate_in_config(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.ttdb_alcohol_high == Decimal('0.65')
    assert config.ttdb_beer == Decimal('0.65')
    assert config.ttdb_tobacco_absolute == 5000


def test_monbai_in_config(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.fee_monbai_over_10b == 3000000
    assert config.fee_monbai_under_10b == 2000000


def test_truoc_ba_in_config(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.fee_truoc_ba_real_estate == Decimal('0.005')
    assert config.fee_truoc_ba_other == Decimal('0.01')


def test_pit_2026_deductions(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.pit_personal_deduction_2026 == 15500000
    assert config.pit_dependent_deduction_2026 == 6200000


def test_pit_2026_brackets(db, tax_config):
    config = TaxConfigService.get_active()
    assert isinstance(config.pit_brackets_2026, list)
    assert len(config.pit_brackets_2026) == 5
    assert config.pit_brackets_2026[0] == [5000000, 0.05]
    assert config.pit_brackets_2026[-1][1] == 0.25


def test_fct_rate(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.fct_cit_rate == Decimal('0.05')
    assert config.fct_vat_rate == Decimal('0.05')


def test_ttdb_tobacco_rate_percent(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.ttdb_tobacco_rate == Decimal('0.75')


def test_ttdb_car_hybrid_discount(db, tax_config):
    config = TaxConfigService.get_active()
    assert config.ttdb_car_hybrid_discount == Decimal('0.70')


# ---------------------------------------------------------------------------
# LegalReference — comprehensive counts
# ---------------------------------------------------------------------------


@pytest.fixture
def cleanup_legal(db):
    LegalReference.objects.all().delete()


def test_legal_ref_count(db, cleanup_legal):
    """Seed produces >=30 active legal references."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    assert LegalReference.objects.filter(status='active').count() >= 30


def test_legal_ref_ttdb_present(db, cleanup_legal):
    """Luật TTĐB 2025 is seeded."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    ref = LegalReference.objects.get(code='LuatTTDB2025')
    lowered = ref.full_name.lower()
    assert 'tieu thu dac biet' in lowered or '65' in ref.summary


def test_legal_ref_monbai_present(db, cleanup_legal):
    """ND 22/2020 môn bài is seeded."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    LegalReference.objects.get(code='ND22')


def test_legal_ref_truoc_ba_present(db, cleanup_legal):
    """Luật trước bạ is seeded."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    LegalReference.objects.get(code='LuatTruocBa')


def test_legal_ref_fct_present(db, cleanup_legal):
    """TT 20/2026 nhà thầu is seeded."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    LegalReference.objects.get(code='TT20')


def test_legal_ref_luat_gtgt_2026_present(db, cleanup_legal):
    """Luật GTGT 2026 is seeded."""
    from django.core.management import call_command
    call_command('seed_legal_references', verbosity=0)
    LegalReference.objects.get(code='LuatGTGT2026')
