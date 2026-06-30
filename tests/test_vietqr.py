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
