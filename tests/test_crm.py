"""Tests for the CRM module — leads, accounts, opportunities, converter, tickets, campaigns."""

from datetime import date
from decimal import Decimal

import pytest

from apps.contracts.models import Contract
from apps.core.models import Company
from apps.crm.models import (
    Activity,
    Campaign,
    CampaignMember,
    CRMContact,
    CRMAccount,
    CRMLead,
    Opportunity,
    OpportunityLine,
    Ticket,
)
from apps.crm.services import OpportunityConverter
from apps.master_data.models import Customer, Product
from apps.projects.models import Project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="CRMTC",
        name="CRM Test Co",
        tax_code="0109998877",
        accounting_regime="tt133",
    )


@pytest.fixture
def product(company):
    return Product.objects.create(
        company=company,
        code="SP001",
        name="License",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lead_creation(company):
    lead = CRMLead.objects.create(
        company=company,
        full_name="Nguyen Van A",
        company_name="ACME",
        email="a@acme.com",
        phone="0901",
        source=CRMLead.LeadSource.WEBSITE,
        status=CRMLead.LeadStatus.NEW,
    )
    assert lead.pk is not None
    assert lead.status == "new"
    assert "Nguyen Van A" in str(lead)


@pytest.mark.django_db
def test_lead_status_change(company):
    lead = CRMLead.objects.create(company=company, full_name="X", company_name="Y")
    lead.status = CRMLead.LeadStatus.QUALIFIED
    lead.save()
    lead.refresh_from_db()
    assert lead.status == "qualified"


# ---------------------------------------------------------------------------
# Accounts & Contacts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_account_contact_creation(company):
    account = CRMAccount.objects.create(company=company, code="AC1", name="ACME Co")
    contact = CRMContact.objects.create(
        company=account.company,
        account=account,
        full_name="Director",
        is_primary=True,
        is_decision_maker=True,
    )
    assert account.customer is None
    assert account.code == "AC1"
    assert contact.account_id == account.id
    assert contact.is_decision_maker is True


# ---------------------------------------------------------------------------
# Opportunity + weighted value
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_opportunity_with_lines_and_weighted_value(company, product):
    account = CRMAccount.objects.create(company=company, code="AC2", name="Buyer")
    opp = Opportunity.objects.create(
        company=company,
        code="OPP001",
        name="SaaS deal",
        account=account,
        stage=Opportunity.Stage.PROPOSAL,
        probability=Decimal("50"),
        estimated_value=Decimal("100000000"),
    )
    # amount auto-computed on save
    line = OpportunityLine.objects.create(
        opportunity=opp,
        line_no=1,
        product=product,
        quantity=Decimal("10"),
        unit_price=Decimal("1000000"),
        vat_rate=Decimal("0.08"),
    )
    assert line.amount == Decimal("10000000")
    assert opp.weighted_value == Decimal("50000000")  # 100M * 50%


# ---------------------------------------------------------------------------
# OpportunityConverter — full flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_opportunity_converter_creates_customer_contract_project_invoice(company, product):
    account = CRMAccount.objects.create(
        company=company,
        code="AC3",
        name="BigCorp",
        tax_code="87654321",
        address="123 St",
    )
    opp = Opportunity.objects.create(
        company=company,
        code="OPP002",
        name="Implementation",
        account=account,
        stage=Opportunity.Stage.NEGOTIATION,
        probability=Decimal("75"),
        estimated_value=Decimal("200000000"),
    )
    OpportunityLine.objects.create(
        opportunity=opp,
        line_no=1,
        product=product,
        quantity=Decimal("1"),
        unit_price=Decimal("200000000"),
        vat_rate=Decimal("0.08"),
    )

    # Mark as won before convert
    opp.stage = Opportunity.Stage.WON
    opp.save()

    results = OpportunityConverter(company=company).convert(opp)

    # Customer created + linked to account
    customer = results["customer"]
    assert isinstance(customer, Customer)
    assert customer.code == "CRMAC3"
    assert customer.tax_code == "87654321"
    account.refresh_from_db()
    assert account.customer_id == customer.id

    # Contract created with service type
    contract = results["contract"]
    assert isinstance(contract, Contract)
    assert contract.contract_no == "HĐOPP002"
    assert contract.contract_type == Contract.ContractType.SERVICE
    assert contract.value == Decimal("200000000")

    # Project created
    project = results["project"]
    assert isinstance(project, Project)
    assert project.code == "PRJOPP002"
    assert project.contract_id == contract.id
    assert project.budget_revenue == Decimal("200000000")

    # Draft invoice created (not posted)
    invoice = results["invoice"]
    assert invoice is not None
    assert invoice.status == 0  # draft

    # Opportunity updated with links
    opp.refresh_from_db()
    assert opp.created_contract_id == contract.id
    assert opp.created_project_id == project.id
    assert opp.created_invoice_id == invoice.id
    assert opp.actual_close_date == date.today()


@pytest.mark.django_db
def test_opportunity_converter_rejects_non_won(company):
    account = CRMAccount.objects.create(company=company, code="AC4", name="X")
    opp = Opportunity.objects.create(company=company, code="OPP003", name="Y", account=account)
    with pytest.raises(ValueError, match="Only WON"):
        OpportunityConverter(company=company).convert(opp)


@pytest.mark.django_db
def test_opportunity_converter_reuses_existing_customer_by_tax_code(company):
    existing = Customer.objects.create(
        company=company, code="KH999", name="Existing", tax_code="1234567"
    )
    account = CRMAccount.objects.create(
        company=company, code="AC5", name="Whatever", tax_code="1234567"
    )
    opp = Opportunity.objects.create(
        company=company,
        code="OPP004",
        name="Deal",
        account=account,
        stage=Opportunity.Stage.WON,
    )
    results = OpportunityConverter(company=company).convert(opp)
    assert results["customer"].id == existing.id


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_activity_linked_to_opportunity(company):
    account = CRMAccount.objects.create(company=company, code="AC6", name="Z")
    opp = Opportunity.objects.create(company=company, code="OPP005", name="D", account=account)
    act = Activity.objects.create(
        company=company,
        activity_type=Activity.ActivityType.CALL,
        subject="Intro call",
        opportunity=opp,
    )
    assert act in list(opp.activities.all())


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ticket_creation(company):
    t = Ticket.objects.create(
        company=company,
        code="TK001",
        subject="Bug report",
        priority=Ticket.Priority.URGENT,
    )
    assert t.status == "open"
    assert t.priority == "urgent"
    assert "TK001" in str(t)


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_creation_with_member(company):
    lead = CRMLead.objects.create(company=company, full_name="M", company_name="C")
    campaign = Campaign.objects.create(
        company=company,
        code="CMP1",
        name="Email Blast",
        campaign_type=Campaign.CampaignType.EMAIL,
        status=Campaign.Status.ACTIVE,
    )
    member = CampaignMember.objects.create(
        campaign=campaign, lead=lead, response_status=CampaignMember.Response.SENT
    )
    assert member in list(campaign.members.all())
    assert lead in [m.lead for m in campaign.members.all()]


# ---------------------------------------------------------------------------
# Simplified CRM mode (hide Ticket/Campaign for micro/small companies)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_simple_crm_hides_ticket_campaign_for_micro(db):
    """Micro company sidebar should NOT show Chăm sóc KH or Chiến dịch."""
    from django.test import Client
    from apps.identity.models import User

    company = Company.objects.create(
        code="MICRO1", name="Micro Co", sme_size="micro", accounting_regime="tt133"
    )
    user = User.objects.create_superuser(
        username="microadmin", password="Secret123", email="m@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "Chăm sóc KH" not in content
    assert "Chiến dịch" not in content
    # Lead + Opportunity should still be visible
    assert "Khách tiềm năng" in content
    assert "Cơ hội bán hàng" in content


@pytest.mark.django_db
def test_full_crm_shows_ticket_campaign_for_medium(db):
    """Medium company sidebar should show all CRM items."""
    from django.test import Client
    from apps.identity.models import User

    company = Company.objects.create(
        code="MED1", name="Medium Co", sme_size="medium", accounting_regime="tt133"
    )
    user = User.objects.create_superuser(
        username="medadmin", password="Secret123", email="med@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "Chăm sóc KH" in content
    assert "Chiến dịch" in content
    assert "Khách tiềm năng" in content
    assert "Cơ hội bán hàng" in content
