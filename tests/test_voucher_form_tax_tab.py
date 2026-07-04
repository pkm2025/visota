"""Tests for voucher form rendering the 'Thuế' tab (VAL-M1-001, VAL-M1-002)."""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def setup_data(db):
    from django.core.management import call_command

    company = Company.objects.create(code="TCO", name="Test Co", fiscal_year_start_month=1)
    call_command("seed_tax_rates")
    call_command("seed_invoice_groups")
    user = User.objects.create_superuser(username="admin", email="a@b.c", password="pass")
    return company, user


def test_voucher_create_form_has_tax_tab(setup_data):
    """VAL-M1-001: voucher form has both 'Chi tiết' and 'Thuế' tabs."""
    _, user = setup_data
    client = Client()
    client.force_login(user)
    resp = client.get("/modern/vouchers/new/")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Chi tiết" in html
    assert "Thuế" in html
    assert 'id="tax-pane"' in html
    assert 'id="detail-pane"' in html


def test_voucher_form_has_tax_fields(setup_data):
    """VAL-M1-002: tax-line subform has all required fields."""
    _, user = setup_data
    client = Client()
    client.force_login(user)
    resp = client.get("/modern/vouchers/new/")
    html = resp.content.decode()
    expected_fields = [
        "invoice_no",
        "invoice_date",
        "invoice_form",
        "invoice_symbol",
        "tax_code",
        "tax_rate",
        "goods_amount_vnd",
        "tax_amount_vnd",
        "offset_account_code",
        "invoice_group_code",
    ]
    for f in expected_fields:
        assert f in html, f"Field {f} not found in form HTML"
