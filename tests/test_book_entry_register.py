"""Tests for book entry register (Sổ đăng ký CTGS, S02a-DN)."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="CTGS", name="CTGS Test Co")
    user = User.objects.create_superuser(
        username="ctgsadmin", password="Secret123", email="ctgs@test.local"
    )
    v1 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="CTGS-001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 10),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
        description="Giao dịch 1",
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=1, account_code="111", debit_vnd=Decimal("500000")
    )
    VoucherLine.objects.create(
        voucher=v1, line_no=2, account_code="5111", credit_vnd=Decimal("500000")
    )

    v2 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="CTGS-002",
        voucher_type="cash_receipt",
        voucher_date=date(2026, 6, 15),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("800000"),
        status=AccountingVoucher.Status.LEDGER,
        description="Thu tiền KH",
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=1, account_code="111", debit_vnd=Decimal("800000")
    )
    VoucherLine.objects.create(
        voucher=v2, line_no=2, account_code="131", credit_vnd=Decimal("800000")
    )
    return company, user


@pytest.mark.django_db
def test_book_entry_register_loads(setup):
    company, user = setup
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get("/modern/reports/book-entry-register/?fiscal_year=2026&period=6")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "CTGS-001" in content
    assert "CTGS-002" in content
    assert "Giao dịch 1" in content


@pytest.mark.django_db
def test_book_entry_register_balanced(setup):
    company, user = setup
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get("/modern/reports/book-entry-register/?fiscal_year=2026&period=6")
    assert response.status_code == 200
    assert response.context["is_balanced"] is True
    assert response.context["total_debit"] == Decimal("1300000")


@pytest.mark.django_db
def test_book_entry_register_empty(db):
    company = Company.objects.create(code="CTGS_E", name="Empty Co")
    user = User.objects.create_superuser(
        username="ctgsempty", password="Secret123", email="e@test.local"
    )
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get("/modern/reports/book-entry-register/?fiscal_year=2026&period=3")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Không có" in content


@pytest.mark.django_db
def test_book_entry_register_requires_login(db):
    c = Client()
    response = c.get("/modern/reports/book-entry-register/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url
