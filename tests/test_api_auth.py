"""Tests for API authentication enforcement (VAL-API-001).

Verifies that all endpoints in apps/core/api.py require authentication.
An unauthenticated request must receive 401, not 200 with data.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.core.models import Company
from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice, SalesInvoiceLine

User = get_user_model()


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TESTAUTH",
        name="Auth Test Co",
        tax_code="0101234567",
    )


@pytest.fixture
def customer(db, company):
    return Customer.objects.create(
        company=company,
        code="CUST-AUTH",
        name="Auth Customer",
        tax_code="0109876543",
        address="123 Auth St",
    )


@pytest.fixture
def product(db, company):
    return Product.objects.create(
        company=company,
        code="PROD-AUTH",
        name="Auth Product",
        default_unit_price=Decimal("1000000"),
        product_type="goods",
        unit_id="cai",
        default_vat_rate=Decimal("10"),
    )


@pytest.fixture
def sales_invoice(db, company, customer, product):
    si = SalesInvoice.objects.create(
        company=company,
        invoice_no="SI-AUTH-001",
        invoice_date="2026-06-23",
        customer=customer,
        currency_code="VND",
        exchange_rate=Decimal("1"),
        subtotal=Decimal("1000000"),
        vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"),
        status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si,
        line_no=1,
        product=product,
        description="Auth line",
        quantity=Decimal("1"),
        unit_id="cai",
        unit_price=Decimal("1000000"),
        amount_before_vat=Decimal("1000000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"),
        amount=Decimal("1100000"),
    )
    return si


@pytest.mark.django_db
def test_get_sales_invoice_requires_auth(db, sales_invoice):
    """VAL-API-001: unauthenticated request to get_sales_invoice returns 401."""
    client = Client()
    # Use NinjaAPI's urls - the api is mounted at /api/v1/
    response = client.get(f"/api/v1/sales/invoices/{sales_invoice.id}")
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated request, got {response.status_code}"
    )


@pytest.mark.django_db
def test_get_sales_invoice_authenticated_succeeds(db, sales_invoice, company):
    """Authenticated request to get_sales_invoice returns 200 with data."""
    user = User.objects.create_superuser(
        username="apiauthadmin", password="Secret123!", email="apiauth@test.local"
    )
    client = Client()
    client.force_login(user)
    # Set current_company in session (mimic middleware)
    session = client.session
    session["current_company_id"] = company.id
    session.save()

    response = client.get(f"/api/v1/sales/invoices/{sales_invoice.id}")
    assert response.status_code == 200, (
        f"Expected 200 for authenticated request, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_list_vouchers_requires_auth(db):
    """Other endpoints also require auth - list_vouchers returns 401."""
    client = Client()
    response = client.get("/api/v1/vouchers/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_list_customers_requires_auth(db):
    """list_customers returns 401 for unauthenticated requests."""
    client = Client()
    response = client.get("/api/v1/customers/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_trial_balance_requires_auth(db):
    """trial_balance returns 401 for unauthenticated requests."""
    client = Client()
    response = client.get("/api/v1/reports/trial-balance?fiscal_year=2026&period=6")
    assert response.status_code == 401


@pytest.mark.django_db
def test_issue_einvoice_requires_auth(db, sales_invoice):
    """E-invoice issue endpoint returns 401 for unauthenticated requests."""
    client = Client()
    response = client.post(f"/api/v1/einvoice/issue/{sales_invoice.id}")
    assert response.status_code == 401
