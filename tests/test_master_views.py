"""Tests for master data views (Customer/Vendor/Product)."""

import pytest
from django.test import Client

from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    from apps.core.models import Company
    company = Company.objects.create(
        code='TST', name='Test Co', tax_code='0100000000', accounting_regime='tt133'
    )
    user = User.objects.create_superuser(username="alice", password="Secret123", email="alice@test.local")
    c = Client()
    c.force_login(user)
    session = c.session
    session['current_company_id'] = company.id
    session.save()
    return c


@pytest.mark.django_db
def test_customer_list_loads(auth_client):
    response = auth_client.get("/modern/customers/")
    assert response.status_code == 200
    assert "Khách hàng" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_customer_create_form_loads(auth_client):
    response = auth_client.get("/modern/customers/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_vendor_list_loads(auth_client):
    response = auth_client.get("/modern/vendors/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_product_list_loads(auth_client):
    response = auth_client.get("/modern/products/")
    assert response.status_code == 200
