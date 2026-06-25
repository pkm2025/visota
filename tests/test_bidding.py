"""Tests for bidding module: opportunity + convert_to_contract."""

from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

import pytest

from apps.bidding.models import (
    BidOpportunity,
    BidResult,
    ContractorProfile,
)
from apps.bidding.services import BidConverterService
from apps.contracts.models import Contract
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTBID", name="Test Bid Co")


@pytest.fixture
def contractor(db, company):
    return ContractorProfile.objects.create(
        company=company, code="MAIN",
        name=company.name, tax_code="0101234567",
        capability_level=ContractorProfile.CapabilityLevel.LEVEL_I,
        years_in_business=10,
        financial_capacity=Decimal("5000000000"),
        staff_count=50,
    )


@pytest.fixture
def opportunity(db, company):
    return BidOpportunity.objects.create(
        company=company, bid_no="BID-001",
        bid_name="Gói thầu test",
        investor_name="Bệnh viện Test",
        investor_tax_code="0109999999",
        bid_method="open",
        bid_form="1s2e",
        bid_type="goods",
        bid_package_price=Decimal("1000000000"),
        duration_days=120,
        published_at=date(2026, 6, 1),
        bid_submission_deadline=datetime(2026, 6, 30, 14, 0, tzinfo=dt_timezone.utc),
        bid_opening_at=datetime(2026, 6, 30, 15, 0, tzinfo=dt_timezone.utc),
    )


# ---------- Model ----------

@pytest.mark.django_db
def test_bid_opportunity_str(opportunity):
    assert "BID-001" in str(opportunity)
    assert "Gói thầu test" in str(opportunity)


@pytest.mark.django_db
def test_contractor_str(contractor):
    s = str(contractor)
    assert contractor.name in s
    assert "I" in s


@pytest.mark.django_db
def test_unique_bid_no_per_company(opportunity, company):
    with pytest.raises(Exception):
        BidOpportunity.objects.create(
            company=company, bid_no="BID-001",
            bid_name="dup", investor_name="x",
        )


# ---------- Service ----------

@pytest.mark.django_db
def test_mark_won_creates_result(opportunity, contractor):
    result = BidConverterService.mark_won(
        opportunity,
        final_value=Decimal("950000000"),
        awarded_at=date(2026, 7, 1),
        contractor_profile=contractor,
    )
    assert result.outcome == BidResult.Outcome.WON
    assert result.final_contract_value == Decimal("950000000")
    assert result.winner_name == contractor.name
    opportunity.refresh_from_db()
    assert opportunity.status == "won"


@pytest.mark.django_db
def test_mark_won_uses_package_price_if_no_value(opportunity):
    result = BidConverterService.mark_won(opportunity)
    assert result.final_contract_value == opportunity.bid_package_price


@pytest.mark.django_db
def test_convert_to_contract_creates_contract(opportunity):
    contract = BidConverterService.convert_to_contract(opportunity)
    assert contract.pk is not None
    assert contract.value == opportunity.bid_package_price
    assert contract.party_name == opportunity.investor_name
    assert contract.party_tax_code == opportunity.investor_tax_code
    assert opportunity.bid_no in contract.contract_no

    # BidResult should be linked
    opportunity.refresh_from_db()
    assert opportunity.result is not None
    assert opportunity.result.contract == contract


@pytest.mark.django_db
def test_convert_to_contract_is_idempotent(opportunity):
    """Calling convert_to_contract twice doesn't create 2 contracts."""
    c1 = BidConverterService.convert_to_contract(opportunity)
    c2 = BidConverterService.convert_to_contract(opportunity)
    # get_or_create returns same contract_no
    assert Contract.objects.filter(contract_no=c1.contract_no).count() == 1


@pytest.mark.django_db
def test_convert_to_contract_with_overrides(opportunity):
    contract = BidConverterService.convert_to_contract(
        opportunity,
        contract_no="CUSTOM-CONTRACT-001",
        value=Decimal("800000000"),
    )
    assert contract.contract_no == "CUSTOM-CONTRACT-001"
    assert contract.value == Decimal("800000000")


@pytest.mark.django_db
def test_convert_to_contract_detects_bid_type_for_contract_type(opportunity, company):
    """Goods bid → service contract (because 'construction' not in type)."""
    contract = BidConverterService.convert_to_contract(opportunity)
    # bid_type='goods' doesn't contain 'construction' → service
    assert contract.contract_type == Contract.ContractType.SERVICE


@pytest.mark.django_db
def test_convert_to_contract_construction_bid(company):
    """Construction bid → construction contract."""
    opp = BidOpportunity.objects.create(
        company=company, bid_no="BID-CON",
        bid_name="Thi công", investor_name="X",
        bid_type="construction", bid_package_price=Decimal("100"),
    )
    contract = BidConverterService.convert_to_contract(opp)
    assert contract.contract_type == Contract.ContractType.CONSTRUCTION


@pytest.mark.django_db
def test_convert_fires_notification(opportunity, db):
    """Convert should notify superusers."""
    from django.contrib.auth import get_user_model
    from apps.notifications.models import Notification

    User = get_user_model()
    admin = User.objects.create_superuser(
        username="bid_admin", password="Secret123!", email="b@test.local"
    )
    BidConverterService.convert_to_contract(opportunity)
    assert Notification.objects.filter(user=admin).count() == 1
    n = Notification.objects.filter(user=admin).first()
    assert "trúng thầu" in n.title.lower() or "Hợp đồng" in n.title
