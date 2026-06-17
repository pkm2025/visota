"""Tests for PIT 2026 fix — Luật 09/2026/QH16 effective 01/01/2026."""

import pytest

from apps.contracts.models import ContractTemplate
from apps.core.models import PITRateHistory, TaxRateConfig
from apps.core.services.tax_config_service import TaxConfigService


@pytest.fixture
def seeded_pit(db):
    from django.core.management import call_command

    call_command("seed_pit_history", verbosity=0)


@pytest.fixture
def seeded_templates(db):
    from django.core.management import call_command

    call_command("seed_contract_templates", verbosity=0)


@pytest.fixture
def seeded_config(db):
    """Apply the seed_demo TaxRateConfig block (PIT 2026 rates)."""
    from datetime import date as _date
    from decimal import Decimal as _Decimal

    TaxRateConfig.objects.update_or_create(
        is_active=True,
        defaults={
            "pit_personal_deduction": _Decimal("13200000"),
            "pit_dependent_deduction": _Decimal("5200000"),
            "pit_brackets": [
                [5000000, "0.05"],
                [10000000, "0.10"],
                [18000000, "0.15"],
                [32000000, "0.20"],
                [999999999, "0.25"],
            ],
            "effective_date": _date(2026, 1, 1),
        },
    )


def test_pit_2026_current(seeded_pit):
    current = PITRateHistory.objects.filter(is_current=True).first()
    assert current is not None
    assert str(current.period_start) == "2026-01-01"
    assert current.personal_deduction == 13200000
    assert current.dependent_deduction == 5200000
    assert len(current.brackets) == 5


def test_pit_2020_period_end_extended(seeded_pit):
    """2020-07-01 entry must now end 2025-12-31 (was 2025-06-30)."""
    h = PITRateHistory.objects.get(period_start="2020-07-01")
    assert str(h.period_end) == "2025-12-31"


def test_tax_config_uses_2026_rates(seeded_config):
    config = TaxConfigService.get_active()
    assert config is not None
    assert config.pit_personal_deduction == 13200000
    assert config.pit_dependent_deduction == 5200000
    assert len(config.pit_brackets) == 5
    # Top bracket rate is now 25%% (was 35%%)
    assert config.pit_brackets[-1][1] in ("0.25", 0.25)


def test_new_contract_templates(seeded_templates):
    for code in ["it_service", "lease", "agency", "processing", "labor_dispatch"]:
        assert ContractTemplate.objects.filter(code=code).exists(), f"Missing: {code}"


def test_total_contract_templates(seeded_templates):
    assert ContractTemplate.objects.count() >= 13  # 8 existing + 5 new


def test_new_templates_have_articles_and_signatures(seeded_templates):
    """Each new template has 7+ articles and a signature block."""
    for code in ["it_service", "lease", "agency", "processing", "labor_dispatch"]:
        tpl = ContractTemplate.objects.get(code=code)
        # At least 7 Điều references
        count = tpl.template_html.count("Điều ")
        assert count >= 7, f"{code} has only {count} articles"
        assert "(Ký, ghi rõ họ tên, đóng dấu)" in tpl.template_html, f"{code} missing signature block"
        assert "Cộng hòa" in tpl.template_html or "CỘNG HÒA" in tpl.template_html
