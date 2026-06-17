"""Tests for contract UI views."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.contracts.models import Contract
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test Co")
    user = User.objects.create_user(username="alice", password="Secret123")
    return company, user


@pytest.fixture
def auth_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_contract_list_loads(auth_client):
    response = auth_client.get("/modern/contracts/")
    assert response.status_code == 200
    assert "Hợp đồng" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_contract_list_shows_contract(setup, auth_client):
    company, _ = setup
    Contract.objects.create(
        company=company,
        contract_no="HD-001",
        contract_date=date(2026, 1, 15),
        contract_type=Contract.ContractType.SALE,
        party_name="Cty ABC",
        value=Decimal("100000000"),
        status="active",
    )
    response = auth_client.get("/modern/contracts/")
    content = response.content.decode("utf-8")
    assert "HD-001" in content
    assert "Cty ABC" in content


@pytest.mark.django_db
def test_contract_create_form_loads(auth_client):
    response = auth_client.get("/modern/contracts/new/")
    assert response.status_code == 200
    assert "Tạo hợp đồng" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_contract_create_submits(setup, auth_client):
    response = auth_client.post(
        "/modern/contracts/new/",
        {
            "contract_no": "HD-NEW-001",
            "contract_date": "2026-03-10",
            "contract_type": "service",
            "party_name": "Cty XYZ",
            "value": "50000000",
            "status": "active",
        },
    )
    assert response.status_code in (200, 302)
    c = Contract.objects.filter(contract_no="HD-NEW-001").first()
    assert c is not None
    assert c.party_name == "Cty XYZ"
    assert c.value == Decimal("50000000")
