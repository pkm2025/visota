from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Employee, Position
from apps.payroll.services import PayrollService


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    dept = Department.objects.create(company=company, code='BH', name='BH')
    pos = Position.objects.create(code='NV', name='NV', level=1)
    # 2 employees with different salaries
    emp1 = Employee.objects.create(
        company=company, code='NV001', full_name='A',
        department=dept, position=pos, hire_date=date(2020, 1, 1),
        base_salary=Decimal('15000000'),
    )
    emp2 = Employee.objects.create(
        company=company, code='NV002', full_name='B',
        department=dept, position=pos, hire_date=date(2021, 1, 1),
        base_salary=Decimal('20000000'),
    )
    return company, [emp1, emp2]


def test_calculate_payroll(setup):
    company, employees = setup
    service = PayrollService(company=company)

    run = service.calculate(period='2026-06', standard_work_days=22)

    assert run.lines.count() == 2
    assert run.status == 'calculated'

    # Employee 1: base 15M, 22/22 days → gross = 15M
    line1 = run.lines.get(employee=employees[0])
    assert line1.gross_salary == Decimal('15000000')
    # BHXH employee = 8%, BHYT = 1.5%, BHTN = 1%
    assert line1.social_insurance_employee == Decimal('1200000')  # 15M * 8%
    assert line1.health_insurance_employee == Decimal('225000')    # 15M * 1.5%
    assert line1.unemployment_insurance_employee == Decimal('150000')  # 15M * 1%
    # PIT is simplified (gross - insurance - deduction 11M) * rate
    # Taxable = 15M - 1.575M - 11M = 2.425M → 5% = 121250
    assert line1.pit > 0
    assert line1.net_salary < line1.gross_salary


def test_post_payroll_generates_voucher(setup):
    company, employees = setup
    service = PayrollService(company=company)

    run = service.calculate(period='2026-06', standard_work_days=22)
    service.post(run)

    run.refresh_from_db()
    assert run.status == 'posted'
    assert run.gl_voucher is not None

    voucher = run.gl_voucher
    assert voucher.is_posted
    assert voucher.voucher_type == 'payroll'

    # Should have N642 (expense), C334 (payable), C3336 (PIT), C3383/3384/3386 (insurance)
    codes = {ln.account_code for ln in voucher.lines.all()}
    assert '642' in codes  # salary expense
    assert '334' in codes  # payable to employees
    assert '3336' in codes  # PIT payable
    assert '3383' in codes  # BHXH payable


def test_payroll_idempotent(setup):
    """Calculating same period twice does not duplicate."""
    company, employees = setup
    service = PayrollService(company=company)

    run1 = service.calculate(period='2026-06', standard_work_days=22)
    run2 = service.calculate(period='2026-06', standard_work_days=22)
    assert run1.id == run2.id  # same run
    assert run2.lines.count() == 2  # not doubled
