"""Tests for input invoice UI views."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.input_docs.models import InputInvoice
from apps.master_data.models import Product


@pytest.fixture
def auth_client(db):
    user = User.objects.create_superuser(username="alice", password="Secret123", email="alice@test.local")
    c = Client()
    c.force_login(user)
    return c, user


@pytest.fixture
def setup_data(db):
    company = Company.objects.create(code="TCO", name="Test Co")
    product = Product.objects.create(
        company=company,
        code="SP001",
        name="Pin",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )
    InputInvoice.objects.create(
        company=company,
        invoice_no="HD001",
        seller_tax_code="0101234567",
        seller_name="XYZ",
        amount_before_vat=Decimal("100000"),
        vat_rate=Decimal("0.10"),
        vat_amount=Decimal("10000"),
        total_amount=Decimal("110000"),
        extraction_status=InputInvoice.ExtractionStatus.EXTRACTED,
    )
    return company, product


@pytest.mark.django_db
def test_input_invoice_list_loads(auth_client, setup_data):
    c, _ = auth_client
    response = c.get("/modern/input-invoices/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_input_invoice_upload_form_loads(auth_client, setup_data):
    c, _ = auth_client
    response = c.get("/modern/input-invoices/upload/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_input_invoice_process_creates_pi(auth_client, setup_data):
    company, product = setup_data
    inv = InputInvoice.objects.get(invoice_no="HD001")
    inv.invoice_date = date(2026, 6, 15)
    inv.save()

    c, user = auth_client
    response = c.post(
        f"/modern/input-invoices/{inv.id}/process/",
        {"product_id": product.id},
    )
    assert response.status_code in (200, 302)

    inv.refresh_from_db()
    assert inv.extraction_status == InputInvoice.ExtractionStatus.MATCHED
    assert inv.purchase_invoice_id is not None
