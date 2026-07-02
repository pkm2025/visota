"""Tests for django-ninja REST API (/api/v1/)."""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountPeriodBalance, AccountingVoucher, VoucherLine
from apps.master_data.models import Customer, Product, Vendor
from apps.sales.models import SalesInvoice


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="APIT", name="API Test Co")
    user = User.objects.create_superuser(
        username="apiadmin", password="Secret123", email="api@test.local"
    )
    Customer.objects.create(company=company, code="C001", name="API Customer")
    Vendor.objects.create(company=company, code="V001", name="API Vendor")
    Product.objects.create(company=company, code="P001", name="API Product", product_type="goods")
    return company, user


@pytest.fixture
def api_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


# ---------- Customers ----------


@pytest.mark.django_db
def test_api_customers_list(api_client, setup):
    response = api_client.get("/api/v1/customers/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(c["code"] == "C001" for c in data["items"])


@pytest.mark.django_db
def test_api_customers_search(api_client, setup):
    response = api_client.get("/api/v1/customers/?search=API")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


# ---------- Vendors ----------


@pytest.mark.django_db
def test_api_vendors_list(api_client, setup):
    response = api_client.get("/api/v1/vendors/")
    assert response.status_code == 200
    data = response.json()
    assert any(v["code"] == "V001" for v in data["items"])


# ---------- Products ----------


@pytest.mark.django_db
def test_api_products_list(api_client, setup):
    response = api_client.get("/api/v1/products/")
    assert response.status_code == 200
    data = response.json()
    assert any(p["code"] == "P001" for p in data["items"])


# ---------- Vouchers ----------


@pytest.mark.django_db
def test_api_vouchers_list_empty(api_client, setup):
    response = api_client.get("/api/v1/vouchers/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0


@pytest.mark.django_db
def test_api_voucher_detail(api_client, setup):
    company, _ = setup
    from datetime import date
    from decimal import Decimal

    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="API-001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        description="Test voucher",
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="111", debit_vnd=Decimal("500000")
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code="5111", credit_vnd=Decimal("500000")
    )
    response = api_client.get(f"/api/v1/vouchers/{v.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["voucher_no"] == "API-001"
    assert len(data["lines"]) == 2


# ---------- Reports ----------


@pytest.mark.django_db
def test_api_trial_balance(api_client, setup):
    company, _ = setup
    from decimal import Decimal

    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="111",
        period_debit=Decimal("1000000"),
        closing_debit=Decimal("1000000"),
    )
    response = api_client.get("/api/v1/reports/trial-balance?fiscal_year=2026&period=6")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(d["account_code"] == "111" for d in data)


@pytest.mark.django_db
def test_api_cash_position(api_client, setup):
    company, _ = setup
    from decimal import Decimal

    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="1111",
        closing_debit=Decimal("5000000"),
    )
    response = api_client.get("/api/v1/reports/cash-position?fiscal_year=2026&period=6")
    assert response.status_code == 200
    data = response.json()
    assert data["cash"] == 5000000


@pytest.mark.django_db
def test_api_ar_aging_empty(api_client, setup):
    response = api_client.get("/api/v1/reports/ar-aging")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# ---------- Auth ----------


@pytest.mark.django_db
def test_api_requires_auth(db):
    """Unauthenticated request returns 401."""
    c = Client()
    response = c.get("/api/v1/customers/")
    assert response.status_code == 401


# ---------- OpenAPI docs ----------


@pytest.mark.django_db
def test_api_openapi_schema(api_client, setup):
    """OpenAPI schema is accessible."""
    response = api_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    # Paths may include namespace prefix
    assert any("customers" in p for p in data["paths"])
