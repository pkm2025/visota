"""Tests for banking module: import CSV, auto-reconcile."""

from datetime import date
from decimal import Decimal

import pytest

from apps.banking.models import (
    BankAccount,
    BankStatementImport,
    BankTransaction,
    ReconciliationMatch,
)
from apps.banking.services import (
    BankImportError,
    BankReconciliationService,
)
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTBANK", name="Test Bank Co")


@pytest.fixture
def bank_account(db, company):
    return BankAccount.objects.create(
        company=company, code="VCB", bank_name="Vietcombank",
        account_number="0071001234567", account_holder=company.name,
        gl_account="1121", opening_balance=Decimal("100000000"),
    )


@pytest.fixture
def import_session(db, company, bank_account):
    return BankStatementImport.objects.create(
        company=company, bank_account=bank_account,
        file_name="test.csv", period_from=date(2026, 6, 1),
        period_to=date(2026, 6, 30),
    )


# ---------- Model ----------

@pytest.mark.django_db
def test_bank_account_str(bank_account):
    s = str(bank_account)
    assert "Vietcombank" in s
    assert "0071001234567" in s


@pytest.mark.django_db
def test_bank_transaction_str(import_session, bank_account, company):
    txn = BankTransaction.objects.create(
        company=company, bank_account=bank_account, import_session=import_session,
        txn_date=date(2026, 6, 23), direction="credit",
        amount=Decimal("1000000"), description="Test",
    )
    s = str(txn)
    assert "credit" in s.lower() or "thu" in s.lower() or "1,000,000" in s


@pytest.mark.django_db
def test_unique_account_number_per_company(company):
    BankAccount.objects.create(
        company=company, code="VCB", bank_name="VCB",
        account_number="0071001234567", account_holder="X",
        gl_account="1121",
    )
    with pytest.raises(Exception):
        BankAccount.objects.create(
            company=company, code="VCB2", bank_name="VCB",
            account_number="0071001234567", account_holder="Y",
            gl_account="1122",
        )


# ---------- Service: parse_date ----------

@pytest.mark.django_db
def test_parse_date_multiple_formats():
    svc = BankReconciliationService
    assert svc._parse_date("2026-06-23") == date(2026, 6, 23)
    assert svc._parse_date("23/06/2026") == date(2026, 6, 23)
    assert svc._parse_date("23-06-2026") == date(2026, 6, 23)


@pytest.mark.django_db
def test_parse_date_invalid_raises():
    with pytest.raises(BankImportError):
        BankReconciliationService._parse_date("invalid")


# ---------- Service: parse_csv ----------

@pytest.mark.django_db
def test_parse_csv_imports_transactions(import_session, bank_account, company):
    csv_content = """date,amount,description,counterparty,reference
2026-06-23,1000000,Khach tra tien,CUST001,REF001
2026-06-23,-500000,Tra ncc,VENDOR001,REF002
2026-06-24,2000000,Khach tra tien 2,CUST002,REF003
"""
    count = BankReconciliationService.parse_csv(import_session, csv_content)
    assert count == 3
    assert BankTransaction.objects.count() == 3

    # Find by reference since ordering is -txn_date
    txn1 = BankTransaction.objects.get(reference="REF001")
    assert txn1.direction == "credit"
    assert txn1.amount == Decimal("1000000")
    assert txn1.counterparty_name == "CUST001"

    import_session.refresh_from_db()
    assert import_session.status == "parsed"


@pytest.mark.django_db
def test_parse_csv_missing_columns_raises(import_session):
    csv_content = """foo,bar
1,2
"""
    with pytest.raises(BankImportError):
        BankReconciliationService.parse_csv(import_session, csv_content)


@pytest.mark.django_db
def test_parse_csv_handles_comma_in_amount(import_session):
    csv_content = """date,amount,description,counterparty
2026-06-23,"1,000,000",Test,C1
"""
    count = BankReconciliationService.parse_csv(import_session, csv_content)
    assert count == 1
    txn = BankTransaction.objects.first()
    assert txn.amount == Decimal("1000000")


# ---------- Service: auto_reconcile ----------

@pytest.mark.django_db
def test_auto_reconcile_matches_voucher_lines(bank_account, company, import_session):
    """Voucher N1121 = 1M, BankTransaction credit 1M → match."""
    from apps.ledger.models import AccountingVoucher, VoucherLine

    target_date = date(2026, 6, 23)
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no="R-001", voucher_type="receipt",
        voucher_date=target_date, currency_code="VND",
        exchange_rate=Decimal("1"), total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="1121",
        debit_vnd=Decimal("1000000"),
    )
    VoucherLine.objects.create(
        voucher=v, line_no=2, account_code="131",
        credit_vnd=Decimal("1000000"),
    )

    BankTransaction.objects.create(
        company=company, bank_account=bank_account, import_session=import_session,
        txn_date=target_date, direction="credit",
        amount=Decimal("1000000"), description="Money in",
    )

    matched = BankReconciliationService.auto_reconcile(company)
    assert matched == 1
    txn = BankTransaction.objects.first()
    assert txn.is_reconciled is True
    assert ReconciliationMatch.objects.count() == 1


@pytest.mark.django_db
def test_auto_reconcile_skips_already_matched(bank_account, company, import_session):
    """Don't double-match the same voucher."""
    from apps.ledger.models import AccountingVoucher, VoucherLine

    target_date = date(2026, 6, 23)
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no="R-001", voucher_type="receipt",
        voucher_date=target_date, currency_code="VND",
        exchange_rate=Decimal("1"), total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="1121",
        debit_vnd=Decimal("1000000"),
    )

    BankTransaction.objects.create(
        company=company, bank_account=bank_account, import_session=import_session,
        txn_date=target_date, direction="credit",
        amount=Decimal("1000000"), description="In",
    )
    BankTransaction.objects.create(
        company=company, bank_account=bank_account, import_session=import_session,
        txn_date=target_date, direction="credit",
        amount=Decimal("1000000"), description="In 2",
    )

    matched1 = BankReconciliationService.auto_reconcile(company)
    assert matched1 == 1
    matched2 = BankReconciliationService.auto_reconcile(company)
    assert matched2 == 0  # voucher already matched


@pytest.mark.django_db
def test_auto_reconcile_window_date(bank_account, company, import_session):
    """Auto-reconcile looks ±3 days from txn date."""
    from apps.ledger.models import AccountingVoucher, VoucherLine

    txn_date = date(2026, 6, 23)
    voucher_date = date(2026, 6, 25)  # 2 days later

    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no="R-001", voucher_type="receipt",
        voucher_date=voucher_date, currency_code="VND",
        exchange_rate=Decimal("1"), total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="1121",
        debit_vnd=Decimal("1000000"),
    )
    BankTransaction.objects.create(
        company=company, bank_account=bank_account, import_session=import_session,
        txn_date=txn_date, direction="credit",
        amount=Decimal("1000000"), description="In",
    )

    matched = BankReconciliationService.auto_reconcile(company)
    assert matched == 1  # within 3 days window
