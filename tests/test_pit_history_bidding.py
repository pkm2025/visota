"""Tests for PIT rate history (2009→2026) and Bidding Law additions."""

import pytest

from apps.core.models import PITRateHistory, LegalReference
from apps.contracts.models import Contract, ContractTemplate


@pytest.fixture
def seeded_pit_history(db):
    from django.core.management import call_command

    call_command("seed_pit_history", verbosity=0)


@pytest.fixture
def seeded_legal_refs(db):
    from django.core.management import call_command

    call_command("seed_legal_references", verbosity=0)


@pytest.fixture
def seeded_contract_templates(db):
    from django.core.management import call_command

    call_command("seed_contract_templates", verbosity=0)


# --- PIT history model ---

def test_pit_history_model_can_be_created(db):
    from datetime import date
    from decimal import Decimal

    h = PITRateHistory.objects.create(
        period_start=date(2020, 7, 1),
        personal_deduction=Decimal("11000000"),
        dependent_deduction=Decimal("4400000"),
        brackets=[[5000000, 0.05]],
        legal_basis="NQ 954/2020",
        is_current=True,
    )
    assert h.pk is not None
    assert h.personal_deduction == Decimal("11000000")


def test_pit_history_count(seeded_pit_history):
    assert PITRateHistory.objects.count() >= 5


def test_pit_2009_deduction(seeded_pit_history):
    h = PITRateHistory.objects.get(period_start="2009-01-01")
    assert h.personal_deduction == 4000000
    assert h.dependent_deduction == 1600000
    assert len(h.brackets) == 7  # 7 bậc


def test_pit_2013_deduction(seeded_pit_history):
    h = PITRateHistory.objects.get(period_start="2013-07-01")
    assert h.personal_deduction == 9000000
    assert h.dependent_deduction == 3600000


def test_pit_2020_deduction(seeded_pit_history):
    h = PITRateHistory.objects.get(period_start="2020-07-01")
    assert h.personal_deduction == 11000000


def test_pit_2026_deduction(seeded_pit_history):
    h = PITRateHistory.objects.get(period_start="2026-07-01")
    assert h.personal_deduction == 15500000
    assert h.dependent_deduction == 6200000
    assert len(h.brackets) == 5  # 5 bậc


def test_pit_2025_current_marked(seeded_pit_history):
    """The 2025-07-01 entry should be marked is_current."""
    h = PITRateHistory.objects.get(period_start="2025-07-01")
    assert h.is_current is True


# --- Legal references ---

def test_legal_ref_pit_history(seeded_legal_refs):
    """PIT history legal refs seeded."""
    assert LegalReference.objects.filter(code="LuatTNCN2007").exists()
    assert LegalReference.objects.filter(code="LuatTNCN2012").exists()
    assert LegalReference.objects.filter(code="NQ954").exists()
    assert LegalReference.objects.filter(code="NQ110").exists()


def test_legal_ref_bidding(seeded_legal_refs):
    assert LegalReference.objects.filter(code="LuatDauThau2023").exists()
    assert LegalReference.objects.filter(code="ND24").exists()
    assert LegalReference.objects.filter(code="TT02BXD").exists()


def test_legal_ref_bidding_summary_contains_clauses(seeded_legal_refs):
    ref = LegalReference.objects.get(code="LuatDauThau2023")
    assert "8 loại" in ref.summary or "8 loại HĐ" in ref.summary
    assert "contracts" in ref.applicable_to


# --- Bidding contract types ---

def test_contract_type_bidding_choices_exist():
    assert hasattr(Contract.ContractType, "BIDDING_LUMP_SUM")
    assert hasattr(Contract.ContractType, "BIDDING_UNIT_PRICE")
    assert hasattr(Contract.ContractType, "BIDDING_CONSULTING")
    assert Contract.ContractType.BIDDING_LUMP_SUM.value == "bidding_lump_sum"


def test_contract_can_use_bidding_type(db, seeded_contract_templates):
    """A Contract with bidding_lump_sum type can be saved."""
    from datetime import date
    from decimal import Decimal

    from apps.core.models import Company

    company = Company.objects.create(
        code="BID",
        name="Công ty Đấu thầu",
        tax_code="0109876543",
        accounting_regime="tt133",
    )
    contract = Contract.objects.create(
        company=company,
        contract_no="HD-BID-001",
        contract_date=date(2026, 6, 18),
        contract_type=Contract.ContractType.BIDDING_LUMP_SUM.value,
        party_name="Nhà thầu X",
        value=Decimal("5000000000"),
        currency_code="VND",
        status="draft",
    )
    assert contract.contract_type == "bidding_lump_sum"
    assert "đấu thầu trọn gói" in contract.get_contract_type_display()


# --- Bidding contract template ---

def test_bidding_contract_template(seeded_contract_templates):
    t = ContractTemplate.objects.get(code="bidding_construction")
    assert "Luật Đấu thầu" in t.legal_basis
    assert t.contract_type == "bidding_lump_sum"
    # Required fields include key bidding items
    assert "performance_guarantee" in t.required_fields
    assert "advance_payment" in t.required_fields
    # Template HTML references key bidding clauses
    assert "Bảo lãnh thực hiện" in t.template_html
    assert "Tạm ứng" in t.template_html


def test_bidding_template_has_8_articles(seeded_contract_templates):
    """Bidding template covers 8 Điều per Luật Đấu thầu."""
    t = ContractTemplate.objects.get(code="bidding_construction")
    # Articles 1-8
    for i in range(1, 9):
        assert f"Điều {i}." in t.template_html
