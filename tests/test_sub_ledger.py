"""Tests for sub-ledger (sổ chi tiết) view."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="SUBL", name="Sub-ledger Test Co")
    user = User.objects.create_superuser(
        username="subtest", password="Secret123", email="s@test.local"
    )
    # Create voucher with TK 131 lines for 2 customers
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="SL-001",
        voucher_type="sales_invoice",
        voucher_date=date(2026, 6, 10),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="131",
        debit_vnd=Decimal("800000"),
        object_code="KH001",
        object_name="KH A",
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="5111",
        credit_vnd=Decimal("800000"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=3,
        account_code="131",
        debit_vnd=Decimal("500000"),
        object_code="KH002",
        object_name="KH B",
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=4,
        account_code="5111",
        credit_vnd=Decimal("500000"),
    )
    return company, user


@pytest.mark.django_db
def test_sub_ledger_131_loads(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    response = c.get("/modern/reports/sub-ledger/?account_code=131&fiscal_year=2026")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "KH001" in content
    assert "KH002" in content
    assert "KH A" in content
    assert "800.000" in content or "800000" in content


@pytest.mark.django_db
def test_sub_ledger_331_empty(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    response = c.get("/modern/reports/sub-ledger/?account_code=331&fiscal_year=2026")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Không có dữ liệu" in content


@pytest.mark.django_db
def test_sub_ledger_requires_login(db):
    c = Client()
    response = c.get("/modern/reports/sub-ledger/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url
