"""Tests for DOCX export endpoints (vouchers, contracts, trial balance)."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test Co")
    user = User.objects.create_user(username="alice", password="Secret123")
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BC0001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        total_vnd=Decimal("1000000"),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="111", debit_vnd=Decimal("1000000")
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code="5111", credit_vnd=Decimal("1000000")
    )
    client = Client()
    client.force_login(user)
    return client, v


def test_voucher_docx_export(setup):
    client, voucher = setup
    response = client.get(f"/modern/vouchers/{voucher.id}/print-docx/")
    assert response.status_code == 200
    assert "application/vnd.openxmlformats" in response["Content-Type"]
    assert len(response.content) > 1000  # non-trivial DOCX
    # DOCX files start with PK (ZIP format)
    assert response.content[:2] == b"PK"
    assert 'filename="BC0001.docx"' in response["Content-Disposition"]


def test_trial_balance_docx_export(db):
    user = User.objects.create_user(username="alice", password="Secret123")
    client = Client()
    client.force_login(user)
    response = client.get("/modern/reports/trial-balance/docx/")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert len(response.content) > 1000


def test_contract_docx_export(db):
    from apps.contracts.models import Contract

    company = Company.objects.create(code="TCO2", name="Contract Co")
    user = User.objects.create_user(username="alice2", password="Secret123")
    contract = Contract.objects.create(
        company=company,
        contract_no="HD001",
        contract_date=date(2026, 6, 1),
        contract_type="sale",
        party_name="ACME Buyer",
        party_tax_code="0309876543",
        value=Decimal("500000000"),
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
    )
    client = Client()
    client.force_login(user)
    response = client.get(f"/modern/contracts/{contract.id}/export-docx/")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"
    assert 'filename="HD001.docx"' in response["Content-Disposition"]


def test_docx_export_service_directly(db):
    """Unit-test the service without going through HTTP."""
    from apps.documents.services.docx_export_service import DocxExportService

    company = Company.objects.create(code="TCO3", name="Svc Co")
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="BC0099",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        total_vnd=Decimal("2500000"),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="111", debit_vnd=Decimal("2500000")
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code="5111", credit_vnd=Decimal("2500000")
    )

    service = DocxExportService()
    out = service.export_voucher(v)
    assert out[:2] == b"PK"
    assert len(out) > 1000
