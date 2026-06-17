"""Tests for invoice views (Sales/Purchase/Stock)."""

import pytest
from django.test import Client

from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="alice", password="Secret123")
    c = Client()
    c.force_login(user)
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
