"""Tests for VietQR dynamic payment QR code generation."""

from decimal import Decimal

import pytest

from apps.banking.models import BankAccount
from apps.banking.services.vietqr_service import VietQRService


@pytest.fixture
def bank_account(db, company):
    return BankAccount.objects.create(
        company=company,
        code="VCB-001",
        bank_name="Vietcombank",
        account_number="0123456789",
        account_holder="CONG TY ABC",
    )


def test_build_url_includes_bin_and_account(bank_account):
    """URL contains Vietcombank BIN (970436) and the account number."""
    url = VietQRService().build_url(bank_account, Decimal("1100000"), "INV AB-001")
    assert "970436" in url
    assert "0123456789" in url


def test_build_url_includes_amount(bank_account):
    """Amount is converted to int and passed as query param."""
    url = VietQRService().build_url(bank_account, Decimal("1100000"), "INV")
    assert "amount=1100000" in url


def test_build_url_url_encodes_memo(bank_account):
    """Memo with spaces and special chars is URL-encoded."""
    url = VietQRService().build_url(bank_account, Decimal("100"), "INV AB-001 #123")
    # spaces become %20, # becomes %23
    assert "addInfo=INV%20AB-001%20%23123" in url


def test_build_url_unknown_bank_raises(company):
    """Bank name not in BIN mapping raises UnsupportedBankError."""
    from apps.banking.services.vietqr_service import VietQRService
    bank = BankAccount.objects.create(
        company=company, code="X", bank_name="Random Unknown Bank XYZ",
        account_number="123", account_holder="X",
    )
    with pytest.raises(VietQRService.UnsupportedBankError):
        VietQRService().build_url(bank, Decimal("100"), "")


def test_resolve_bin_case_insensitive_partial():
    """BIN lookup matches case-insensitive partial bank name."""
    svc = VietQRService()
    # 'vcb' shouldn't match, but 'vietcombank' (any case) should
    assert svc._resolve_bin("Vietcombank") == "970436"
    assert svc._resolve_bin("Ngân hàng VCB - Vietcombank") == "970436"
    assert svc._resolve_bin("ACB") == "970416"


def test_build_memo_includes_invoice_and_customer():
    """Memo format: 'INV <invoice_no> <customer_code>'."""
    memo = VietQRService().build_memo("AB-001", "CUST42")
    assert memo == "INV AB-001 CUST42"


def test_build_memo_without_customer():
    """Memo without customer code: 'INV <invoice_no>'."""
    memo = VietQRService().build_memo("AB-001")
    assert memo == "INV AB-001"


def test_build_memo_truncates_to_34_chars():
    """VietQR addInfo max is 34 chars."""
    memo = VietQRService().build_memo("A" * 100, "B" * 50)
    assert len(memo) <= 34


import json  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402


@pytest.fixture
def admin(db, company):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", password="Secret123!", email="admin@test.local"
    )


@pytest.fixture
def auth_client(admin):
    c = Client()
    c.force_login(admin)
    return c


@pytest.fixture
def company_with_bank(company, bank_account):
    """Company that already has a bank_account."""
    return company


def test_modal_view_returns_json_for_einvoice(auth_client, company_with_bank, admin):
    """GET einvoice QR endpoint returns 200 + JSON with qr_url."""
    from apps.einvoice.models import EInvoice
    from decimal import Decimal
    ei = EInvoice.objects.create(
        company=admin.current_company if hasattr(admin, "current_company") else company_with_bank,
        invoice_no="AA/26E-0000001", status="issued",
        subtotal=Decimal("1000000"), vat_rate=Decimal("0.10"),
        vat_amount=Decimal("100000"), total_amount=Decimal("1100000"),
    )
    url = reverse("ui_modern:vietqr_modal", kwargs={"invoice_type": "einvoice", "pk": ei.pk})
    response = auth_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "qr_url" in data
    assert data["qr_url"].startswith("https://api.vietqr.io/img/")
    assert "970436" in data["qr_url"]  # VCB BIN
    assert data["account_no"] == "0123456789"
    assert data["amount"] == "1100000"


def test_modal_view_requires_login(db, company_with_bank):
    """Anonymous user -> redirect (302) or 403."""
    from apps.einvoice.models import EInvoice
    from decimal import Decimal
    company = company_with_bank
    ei = EInvoice.objects.create(
        company=company, invoice_no="AA/26E-0000001", status="issued",
        subtotal=Decimal("1000"), vat_amount=Decimal("100"),
        vat_rate=Decimal("0.10"), total_amount=Decimal("1100"),
    )
    url = reverse("ui_modern:vietqr_modal", kwargs={"invoice_type": "einvoice", "pk": ei.pk})
    response = Client().get(url)
    assert response.status_code in (302, 403)


def test_modal_view_404_no_bank_account(db, company, admin):
    """Company without BankAccount -> 404 with error message."""
    from apps.einvoice.models import EInvoice
    from decimal import Decimal
    ei = EInvoice.objects.create(
        company=company, invoice_no="AA-X", status="issued",
        subtotal=Decimal("1000"), vat_amount=Decimal("100"),
        vat_rate=Decimal("0.10"), total_amount=Decimal("1100"),
    )
    c = Client()
    c.force_login(admin)
    url = reverse("ui_modern:vietqr_modal", kwargs={"invoice_type": "einvoice", "pk": ei.pk})
    response = c.get(url)
    assert response.status_code == 404
    data = response.json()
    assert "chưa có" in data["error"].lower() or "no bank" in data["error"].lower()


def test_modal_view_404_invalid_invoice_type(auth_client, company_with_bank):
    """Invalid invoice_type -> 404."""
    url = reverse("ui_modern:vietqr_modal", kwargs={"invoice_type": "invalid", "pk": 1})
    response = auth_client.get(url)
    assert response.status_code == 404


def test_modal_view_returns_json_for_sales(auth_client, company_with_bank, admin):
    """GET sales invoice QR endpoint returns 200 + JSON."""
    from apps.sales.models import SalesInvoice
    from apps.master_data.models.party import Customer
    from decimal import Decimal
    from datetime import date
    company = admin.current_company if hasattr(admin, "current_company") else company_with_bank
    cust = Customer.objects.create(
        company=company, code="CUST-1", name="Test Customer",
    )
    si = SalesInvoice.objects.create(
        company=company, invoice_no="SI-001", invoice_date=date(2026, 6, 30),
        customer=cust, currency_code="VND", exchange_rate=Decimal("1"),
        subtotal=Decimal("1000000"), vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"), status=2,
    )
    url = reverse("ui_modern:vietqr_modal", kwargs={"invoice_type": "sales", "pk": si.pk})
    response = auth_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "qr_url" in data
    assert "CUST-1" in data["memo"]  # memo includes customer code
