import pytest
from decimal import Decimal
from datetime import date
from apps.hr.models import (
    Employee,
    Department,
    Position,
    InsuranceContribution,
    LeaveRecord,
    LeaveBalance,
)
from apps.hr.services import InsuranceService
from apps.core.models import Company


@pytest.fixture
def emp(db):
    c = Company.objects.create(code='TCO', name='T')
    d = Department.objects.create(company=c, code='IT', name='IT')
    p = Position.objects.create(code='DEV', name='Dev', level=1)
    return Employee.objects.create(
        company=c, code='NV01', full_name='Test', department=d, position=p,
        hire_date=date(2020,1,1), base_salary=Decimal('15000000'),
    )


def test_insurance_calculation(emp):
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, '2026-06')
    # NV 10.5%: 8% + 1.5% + 1%
    assert ic.bhxh_employee == Decimal('1200000')   # 15M * 8%
    assert ic.bhyt_employee == Decimal('225000')     # 15M * 1.5%
    assert ic.bhtn_employee == Decimal('150000')     # 15M * 1%
    # DN 21.5%: 17% + 3% + 1% + 0.5%
    assert ic.bhxh_employer == Decimal('2550000')   # 15M * 17%
    assert ic.bhyt_employer == Decimal('450000')     # 15M * 3%
    assert ic.bhtn_employer == Decimal('150000')     # 15M * 1%
    assert ic.bhtnld_employer == Decimal('75000')    # 15M * 0.5%


def test_insurance_cap(emp):
    """Salary above cap -> capped at 46.8M."""
    emp.base_salary = Decimal('100000000')  # 100M > 46.8M
    emp.save()
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, '2026-06')
    assert ic.salary_base == Decimal('46800000')  # capped


def test_insurance_kpcd(emp):
    """Kinh phí công đoàn 2%."""
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, '2026-06')
    assert ic.kpcd_employer == Decimal('300000')  # 15M * 2%


def test_annual_leave_balance(emp):
    lb = LeaveBalance.objects.create(
        employee=emp, fiscal_year=2026,
        standard_days=Decimal('12'), carried_forward=Decimal('3'),
    )
    assert lb.remaining_days == Decimal('15')  # 12 + 3 - 0


def test_leave_request(emp):
    lr = LeaveRecord.objects.create(
        employee=emp, leave_type='annual',
        start_date=date(2026,6,10), end_date=date(2026,6,12),
        days=Decimal('3'), reason='Nghỉ phép',
        status='approved',
    )
    assert lr.pk is not None
    assert lr.days == Decimal('3')


def test_maternity_leave(emp):
    lr = LeaveRecord.objects.create(
        employee=emp, leave_type='maternity',
        start_date=date(2026,1,1), end_date=date(2026,6,30),
        days=Decimal('180'), maternity_months=Decimal('6'),
        reason='Thai sản', status='approved',
    )
    assert lr.maternity_months == Decimal('6')
