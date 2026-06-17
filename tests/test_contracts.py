"""Tests for Contract and Minutes models."""

from datetime import date
from decimal import Decimal

import pytest

from apps.contracts.models import Contract, Minutes
from apps.core.models import Company
from apps.ledger.models import AccountingVoucher


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TCO",
        name="Test Company",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.mark.django_db
def test_create_contract(company):
    c = Contract.objects.create(
        company=company,
        contract_no="HD-2026-001",
        contract_date=date(2026, 1, 15),
        contract_type=Contract.ContractType.SALE,
        party_code="KH001",
        party_name="Công ty ABC",
        party_tax_code="0301234567",
        party_address="123 Lê Lợi, Q1, TP.HCM",
        description="Hợp đồng cung cấp hàng hóa",
        value=Decimal("100000000"),
        currency_code="VND",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 12, 31),
        status="active",
    )
    assert c.pk is not None
    assert c.contract_no == "HD-2026-001"
    assert c.contract_type == "sale"
    assert c.value == Decimal("100000000")
    assert c.status == "active"


@pytest.mark.django_db
def test_create_minutes(company):
    contract = Contract.objects.create(
        company=company,
        contract_no="HD-2026-002",
        contract_date=date(2026, 2, 1),
        contract_type=Contract.ContractType.SERVICE,
        party_code="KH002",
        party_name="Cty XYZ",
        value=Decimal("50000000"),
        start_date=date(2026, 2, 1),
        end_date=date(2026, 6, 30),
        status="active",
    )
    m = Minutes.objects.create(
        company=company,
        minutes_no="BB-2026-001",
        minutes_date=date(2026, 3, 1),
        minutes_type=Minutes.MinutesType.ACCEPTANCE,
        contract=contract,
        description="Nghiệm thu đợt 1",
    )
    assert m.pk is not None
    assert m.minutes_type == "acceptance"
    assert m.contract_id == contract.pk
    assert m.description == "Nghiệm thu đợt 1"


@pytest.mark.django_db
def test_contract_linked_to_voucher(company):
    """Contract can be linked to an AccountingVoucher."""
    voucher = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=3,
        voucher_no="PT0001",
        voucher_type="cash_receipt",
        voucher_date=date(2026, 3, 1),
    )
    c = Contract.objects.create(
        company=company,
        contract_no="HD-2026-003",
        contract_date=date(2026, 1, 20),
        contract_type=Contract.ContractType.PURCHASE,
        party_code="NCC001",
        party_name="Nhà cung cấp A",
        value=Decimal("20000000"),
        start_date=date(2026, 1, 20),
        end_date=date(2026, 6, 30),
        status="active",
        linked_voucher=voucher,
    )
    c.refresh_from_db()
    assert c.linked_voucher_id == voucher.pk
    assert c.linked_voucher.voucher_no == "PT0001"


@pytest.mark.django_db
def test_minutes_linked_to_contract(company):
    """Minutes can be linked to a Contract via FK."""
    contract = Contract.objects.create(
        company=company,
        contract_no="HD-2026-004",
        contract_date=date(2026, 4, 1),
        contract_type=Contract.ContractType.CONSTRUCTION,
        party_code="KH003",
        party_name="Cty Xây dựng 123",
        value=Decimal("500000000"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        status="active",
    )
    m1 = Minutes.objects.create(
        company=company,
        minutes_no="BB-2026-002",
        minutes_date=date(2026, 4, 5),
        minutes_type=Minutes.MinutesType.HANDOVER,
        contract=contract,
        description="Bàn giao mặt bằng",
    )
    m2 = Minutes.objects.create(
        company=company,
        minutes_no="BB-2026-003",
        minutes_date=date(2026, 5, 10),
        minutes_type=Minutes.MinutesType.LIQUIDATION,
        contract=contract,
        description="Thanh lý giai đoạn 1",
    )
    # Reverse relation
    minutes_list = list(contract.minutes_set.all().order_by("minutes_no"))
    assert len(minutes_list) == 2
    assert minutes_list[0].minutes_no == "BB-2026-002"
    assert minutes_list[1].minutes_type == "liquidation"
