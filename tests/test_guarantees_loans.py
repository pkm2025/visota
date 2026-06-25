"""Tests for guarantees + loans modules."""

from datetime import date
from decimal import Decimal

import pytest

from apps.contracts.models import Contract
from apps.core.models import Company
from apps.guarantees.models import BankGuarantee
from apps.loans.models import (
    BankLoan,
    LoanDisbursement,
    LoanInterestAccrual,
    LoanRepayment,
)


# ---------- Guarantees ----------

@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTBL", name="Test GL Co")


@pytest.fixture
def contract(db, company):
    return Contract.objects.create(
        company=company, contract_no="C-001",
        contract_date=date(2026, 6, 1),
        party_name="Investor X",
        value=Decimal("1000000000"),
        status=Contract.Status.ACTIVE,
    )


@pytest.mark.django_db
def test_bank_guarantee_str(company, contract):
    g = BankGuarantee.objects.create(
        company=company, guarantee_no="BL-001",
        issue_date=date(2026, 6, 1), expiry_date=date(2026, 12, 1),
        guarantee_type=BankGuarantee.GuaranteeType.PERFORMANCE,
        bank_name="VCB", bank_account="007123",
        amount=Decimal("100000000"), beneficiary_name="Investor",
        contract=contract,
    )
    s = str(g)
    assert "BL-001" in s
    assert "Investor" in s


@pytest.mark.django_db
def test_guarantee_days_to_expiry(company):
    from datetime import date as d, timedelta

    future = d.today() + timedelta(days=30)
    g = BankGuarantee.objects.create(
        company=company, guarantee_no="BL-002",
        issue_date=d.today(), expiry_date=future,
        guarantee_type="performance",
        bank_name="VCB", bank_account="x",
        amount=Decimal("100"), beneficiary_name="X",
    )
    assert g.days_to_expiry is not None
    assert 29 <= g.days_to_expiry <= 31


@pytest.mark.django_db
def test_guarantee_unique_per_company(company):
    BankGuarantee.objects.create(
        company=company, guarantee_no="BL-DUP",
        issue_date=date(2026, 6, 1), expiry_date=date(2026, 12, 1),
        guarantee_type="performance",
        bank_name="VCB", bank_account="x",
        amount=Decimal("100"), beneficiary_name="X",
    )
    with pytest.raises(Exception):
        BankGuarantee.objects.create(
            company=company, guarantee_no="BL-DUP",
            issue_date=date(2026, 6, 1), expiry_date=date(2026, 12, 1),
            guarantee_type="performance",
            bank_name="VCB", bank_account="x",
            amount=Decimal("200"), beneficiary_name="Y",
        )


@pytest.mark.django_db
def test_guarantee_all_types():
    """Verify all 5 guarantee types are valid choices."""
    for t, _ in BankGuarantee.GuaranteeType.choices:
        assert t in ["bid_bond", "performance", "advance_payment", "warranty", "other"]


# ---------- Loans ----------

@pytest.mark.django_db
def test_bank_loan_str(company):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type=BankLoan.LoanType.SHORT_TERM,
        bank_name="Vietcombank",
        contract_date=date(2026, 1, 1),
        principal_amount=Decimal("2000000000"),
        interest_rate_pa=Decimal("8.5"),
        disbursement_date=date(2026, 1, 5),
        maturity_date=date(2027, 1, 5),
    )
    s = str(loan)
    assert "L-001" in s
    assert "Vietcombank" in s


@pytest.mark.django_db
def test_loan_outstanding_principal_zero_initially(company):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type="short_term", bank_name="x",
        contract_date=date(2026, 1, 1), principal_amount=Decimal("1000000000"),
        interest_rate_pa=Decimal("8"),
        disbursement_date=date(2026, 1, 1), maturity_date=date(2027, 1, 1),
    )
    assert loan.outstanding_principal == 0  # no disbursements yet


@pytest.mark.django_db
def test_loan_outstanding_principal_after_disbursement(company):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type="short_term", bank_name="x",
        contract_date=date(2026, 1, 1), principal_amount=Decimal("1000000000"),
        interest_rate_pa=Decimal("8"),
        disbursement_date=date(2026, 1, 1), maturity_date=date(2027, 1, 1),
    )
    LoanDisbursement.objects.create(
        loan=loan, disbursement_date=date(2026, 1, 5), amount=Decimal("500000000"),
    )
    assert loan.outstanding_principal == Decimal("500000000")


@pytest.mark.django_db
def test_loan_outstanding_principal_after_repayment(company):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type="short_term", bank_name="x",
        contract_date=date(2026, 1, 1), principal_amount=Decimal("1000000000"),
        interest_rate_pa=Decimal("8"),
        disbursement_date=date(2026, 1, 1), maturity_date=date(2027, 1, 1),
    )
    LoanDisbursement.objects.create(
        loan=loan, disbursement_date=date(2026, 1, 5), amount=Decimal("1000000000"),
    )
    LoanRepayment.objects.create(
        loan=loan, payment_date=date(2026, 3, 1),
        principal=Decimal("200000000"),
        interest=Decimal("10000000"),
    )
    assert loan.outstanding_principal == Decimal("800000000")


@pytest.mark.django_db
def test_loan_interest_accrual_unique_per_period(company):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type="short_term", bank_name="x",
        contract_date=date(2026, 1, 1), principal_amount=Decimal("1000000000"),
        interest_rate_pa=Decimal("8"),
        disbursement_date=date(2026, 1, 1), maturity_date=date(2027, 1, 1),
    )
    LoanInterestAccrual.objects.create(
        loan=loan, period_year=2026, period_month=1,
        days=31, principal_base=Decimal("1000000000"),
        interest_amount=Decimal("6800000"),
    )
    with pytest.raises(Exception):
        LoanInterestAccrual.objects.create(
            loan=loan, period_year=2026, period_month=1,
            days=31, principal_base=Decimal("1000000000"),
            interest_amount=Decimal("6800000"),
        )


@pytest.mark.django_db
def test_loan_link_to_contract(company, contract):
    loan = BankLoan.objects.create(
        company=company, loan_no="L-001",
        loan_type="long_term", bank_name="x",
        contract_date=date(2026, 6, 1), principal_amount=Decimal("2000000000"),
        interest_rate_pa=Decimal("8"),
        disbursement_date=date(2026, 6, 5), maturity_date=date(2031, 6, 5),
        contract=contract,
    )
    assert loan.contract == contract
