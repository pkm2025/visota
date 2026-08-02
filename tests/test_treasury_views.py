"""Tests for treasury views — phiếu thu / phiếu chi."""

from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher


@pytest.fixture
def setup(db):
    company = Company.objects.create(
        code="TCO",
        name="Test Co",
        tax_code="0101234567",
        accounting_regime="tt133",
    )
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local"
    )
    return company, user


@pytest.fixture
def auth_client(setup):
    _, user = setup
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_cash_receipt_form_loads(auth_client):
    response = auth_client.get("/modern/treasury/receipt/new/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Phiếu thu" in content or "phiếu thu" in content
    assert "Người nộp" in content


@pytest.mark.django_db
def test_cash_payment_form_loads(auth_client):
    response = auth_client.get("/modern/treasury/payment/new/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Phiếu chi" in content or "phiếu chi" in content
    assert "Người nhận" in content


@pytest.mark.django_db
def test_cash_receipt_creates_voucher(setup, auth_client):
    """Submit phiếu thu form → creates voucher_type=cash_receipt, N111/C{account}."""
    response = auth_client.post(
        "/modern/treasury/receipt/new/",
        {
            "voucher_no": "PT-2026-001",
            "voucher_date": "2026-06-15",
            "payer": "Nguyễn Văn A",
            "amount": "1000000",
            "reason": "Thu tiền khách hàng",
            "credit_account": "131",
        },
    )
    # Should redirect after success
    assert response.status_code in (200, 302)
    v = AccountingVoucher.objects.filter(voucher_no="PT-2026-001").first()
    assert v is not None
    assert v.voucher_type == "cash_receipt"
    lines = list(v.lines.all().order_by("line_no"))
    # Should have 2 lines: N111 (debit), C{account} (credit)
    assert len(lines) == 2
    debit_line = lines[0]
    credit_line = lines[1]
    assert debit_line.account_code == "111"
    assert debit_line.debit_vnd == Decimal("1000000")
    assert credit_line.account_code == "131"
    assert credit_line.credit_vnd == Decimal("1000000")


@pytest.mark.django_db
def test_cash_receipt_sets_object_code_on_counterpart(setup, auth_client):
    """#10 root-cause fix: phiếu thu must set object_code on TK 131 line.

    Without object_code, payment rows in AccountPeriodBalance land on a
    different (account_code, object_code) bucket than invoice rows,
    causing B01 to double-count gross activity.
    """
    auth_client.post(
        "/modern/treasury/receipt/new/",
        {
            "voucher_no": "PT-OC-001",
            "voucher_date": "2026-06-15",
            "payer": "Khách hàng P&T",
            "amount": "500000",
            "reason": "Thu tiền",
            "credit_account": "131",
            "object_code": "PT001",
        },
    )
    v = AccountingVoucher.objects.get(voucher_no="PT-OC-001")
    credit_line = v.lines.get(line_no=2)
    assert credit_line.object_code == "PT001", (
        "Counterpart line (TK 131) should carry object_code=PT001"
    )
    # Cash line (111) should NOT carry object_code (cash has no object)
    cash_line = v.lines.get(line_no=1)
    assert cash_line.object_code in ("", None)


@pytest.mark.django_db
def test_cash_payment_sets_object_code_on_counterpart(setup, auth_client):
    """#10 root-cause fix: phiếu chi must set object_code on TK 331 line."""
    auth_client.post(
        "/modern/treasury/payment/new/",
        {
            "voucher_no": "PC-OC-001",
            "voucher_date": "2026-06-16",
            "payee": "Nhà cung cấp ABC",
            "amount": "300000",
            "reason": "Thanh toán NCC",
            "debit_account": "331",
            "object_code": "ABC001",
        },
    )
    v = AccountingVoucher.objects.get(voucher_no="PC-OC-001")
    debit_line = v.lines.get(line_no=1)
    assert debit_line.object_code == "ABC001", (
        "Counterpart line (TK 331) should carry object_code=ABC001"
    )
    cash_line = v.lines.get(line_no=2)
    assert cash_line.object_code in ("", None)


@pytest.mark.django_db
def test_cash_receipt_without_object_code_still_works(setup, auth_client):
    """Backward compat: form without object_code field still creates voucher."""
    response = auth_client.post(
        "/modern/treasury/receipt/new/",
        {
            "voucher_no": "PT-NOOC-001",
            "voucher_date": "2026-06-17",
            "payer": "Khách vãng lai",
            "amount": "100000",
            "reason": "Bán lẻ",
            "credit_account": "511",
            # no object_code field — should default to ""
        },
    )
    assert response.status_code in (200, 302)
    v = AccountingVoucher.objects.get(voucher_no="PT-NOOC-001")
    credit_line = v.lines.get(line_no=2)
    assert credit_line.object_code == ""
