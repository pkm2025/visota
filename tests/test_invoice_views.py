"""Tests for invoice views (Sales/Purchase/Stock)."""

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
def test_sales_invoice_list_loads(auth_client):
    response = auth_client.get("/modern/sales-invoices/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_sales_invoice_create_form_loads(auth_client):
    response = auth_client.get("/modern/sales-invoices/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_purchase_invoice_list_loads(auth_client):
    response = auth_client.get("/modern/purchase-invoices/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_stock_voucher_list_loads(auth_client):
    response = auth_client.get("/modern/stock-vouchers/")
    assert response.status_code == 200
