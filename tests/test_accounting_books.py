"""Tests for accounting books: Sổ nhật ký chung (S03a-DN) and Sổ cái (S03b-DN)."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test Company")
    user = User.objects.create_user(username="alice", password="Secret123")
    return company, user


@pytest.fixture
def auth_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_general_journal_requires_login(db):
    c = Client()
    response = c.get("/modern/reports/general-journal/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_general_journal_loads_empty(auth_client):
    response = auth_client.get("/modern/reports/general-journal/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_general_journal_shows_voucher_with_lines(setup, auth_client):
    company, _ = setup
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="NKC0001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        description="Bán hàng cho KH",
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="131",
        debit_vnd=Decimal("1000000"),
        credit_vnd=Decimal("0"),
        description="KH nợ tiền",
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="5111",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("1000000"),
        description="DT bán hàng",
    )

    response = auth_client.get("/modern/reports/general-journal/?fiscal_year=2026&period=6")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "NKC0001" in content
    # Line descriptions appear because NKC expands each line per spec
    assert "KH nợ tiền" in content
    assert "DT bán hàng" in content
    assert "131" in content
    assert "5111" in content


@pytest.mark.django_db
def test_general_ledger_shows_lines_for_specific_account(setup, auth_client):
    """Sổ cái cho TK 131 chỉ hiện bút toán của TK 131."""
    company, _ = setup
    v1 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="PT0001",
        voucher_type="cash_receipt",
        voucher_date=date(2026, 6, 10),
        description="Thu tiền KH",
    )
    VoucherLine.objects.create(
        voucher=v1,
        line_no=1,
        account_code="111",
        debit_vnd=Decimal("500000"),
        credit_vnd=Decimal("0"),
    )
    VoucherLine.objects.create(
        voucher=v1,
        line_no=2,
        account_code="131",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("500000"),
    )

    v2 = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BH0001",
        voucher_type="sales_invoice",
        voucher_date=date(2026, 6, 12),
        description="Bán hàng cho KH",
    )
    VoucherLine.objects.create(
        voucher=v2,
        line_no=1,
        account_code="131",
        debit_vnd=Decimal("800000"),
        credit_vnd=Decimal("0"),
    )
    VoucherLine.objects.create(
        voucher=v2,
        line_no=2,
        account_code="5111",
        debit_vnd=Decimal("0"),
        credit_vnd=Decimal("800000"),
    )

    response = auth_client.get("/modern/reports/general-ledger/?account_code=131")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # TK 131 bút toán phải có trong sổ cái
    assert "PT0001" in content
    assert "BH0001" in content
    # Số dư chạy (running balance)
    assert "300.000" in content or "300000" in content or "300,000" in content  # 800000 - 500000
