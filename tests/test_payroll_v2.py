"""Task 3 tests: PayrollService v2 — insurance cap, dependents, KPCĐ, 8-line voucher."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Dependent, Employee, Position
from apps.ledger.models import VoucherLine
from apps.payroll.services.payroll_service import PayrollService


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TCO", name="T", tax_code="0101234567", accounting_regime="tt133"
    )


@pytest.fixture
def make_emp(company):
    def _make(salary=Decimal("15000000"), allowance=Decimal("0")):
        d = Department.objects.create(company=company, code="IT", name="IT")
        p = Position.objects.create(code="DEV", name="Dev", level=1)
        return Employee.objects.create(
            company=company,
            code="NV01",
            full_name="Test",
            department=d,
            position=p,
            hire_date=date(2020, 1, 1),
            base_salary=salary,
            allowance=allowance,
        )

    return _make


def test_cap_applied_to_insurance(company, make_emp):
    """Salary above 50.6M → BHXH capped, not at full salary (ND 161/2026)."""
    emp = make_emp(salary=Decimal("100000000"))
    svc = PayrollService(company=company)
    run = svc.calculate("2026-06")
    line = run.lines.get(employee=emp)
    # Employee BHXH 8% of cap (50.6M) = 4,048,000
    assert line.social_insurance_employee == Decimal("4048000")
    # NOT 8% of 100M (8,000,000)
    assert line.social_insurance_employee < Decimal("8000000")


def test_dependent_reduces_pit(company, make_emp):
    """Active dependents reduce PIT via family deduction."""
    emp = make_emp(salary=Decimal("30000000"))
    svc = PayrollService(company=company)
    # Baseline: no dependents
    run1 = svc.calculate("2026-05")
    pit_baseline = run1.lines.get(employee=emp).pit

    # Add 2 active dependents (registered, valid_from in the past)
    for i in range(2):
        Dependent.objects.create(
            employee=emp,
            full_name=f"Dep {i}",
            relationship="child",
            birth_date=date(2015, 1, 1),
            deduction_amount=Decimal("6200000"),
            valid_from=date(2024, 1, 1),
            registration_status="registered",
        )
    run2 = svc.calculate("2026-06")
    pit_with_deps = run2.lines.get(employee=emp).pit

    # PIT should be lower with 2 extra dependents (8.8M extra deduction)
    assert pit_with_deps < pit_baseline


def test_kpcd_in_voucher(company, make_emp):
    """Voucher contains KPCĐ line (TK 3382)."""
    make_emp(salary=Decimal("15000000"))
    svc = PayrollService(company=company)
    run = svc.calculate("2026-06")
    voucher = svc.post(run)
    accounts = set(
        VoucherLine.objects.filter(voucher=voucher).values_list("account_code", flat=True)
    )
    assert "3382" in accounts  # KPCĐ


def test_voucher_has_8_lines(company, make_emp):
    """Voucher has at least 8 lines: N642, C334, C3336, C3382, C3383, C3384, C3386, + BHTNLĐ."""
    # Salary must exceed 15.5M personal deduction + insurance for PIT > 0
    # (NQ 110/2025 fallback: personal deduction = 15.5M/month)
    make_emp(salary=Decimal("50000000"))
    svc = PayrollService(company=company)
    run = svc.calculate("2026-06")
    voucher = svc.post(run)
    n_lines = VoucherLine.objects.filter(voucher=voucher).count()
    assert n_lines >= 8, f"Expected >=8 lines, got {n_lines}"
    accounts = set(
        VoucherLine.objects.filter(voucher=voucher).values_list("account_code", flat=True)
    )
    expected = {"642", "334", "3336", "3382", "3383", "3384", "3386"}
    assert expected.issubset(accounts), f"Missing: {expected - accounts}"
