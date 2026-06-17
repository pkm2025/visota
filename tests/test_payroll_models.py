from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Employee, Position
from apps.payroll.models import AttendanceRecord, PayrollLine, PayrollRun


@pytest.fixture
def employee(db):
    company = Company.objects.create(code='TCO', name='Test')
    dept = Department.objects.create(company=company, code='BH', name='BH')
    pos = Position.objects.create(code='NV', name='NV', level=1)
    return Employee.objects.create(
        company=company, code='NV001', full_name='Test',
        department=dept, position=pos, hire_date=date(2020, 1, 1),
        base_salary=Decimal('15000000'),
    )


def test_attendance_creation(employee):
    att = AttendanceRecord.objects.create(
        company=employee.company, employee=employee,
        attendance_date=date(2026, 6, 15),
        status='present', work_days=Decimal('1.0'),
    )
    assert att.pk is not None
    assert att.status == 'present'


def test_payroll_run_creation(employee):
    company = employee.company
    run = PayrollRun.objects.create(
        company=company, period='2026-06',
        fiscal_year=2026, period_num=6,
        status='draft',
    )
    assert run.pk is not None
    assert str(run) == 'Payroll 2026-06'


def test_payroll_line_creation(employee):
    company = employee.company
    run = PayrollRun.objects.create(
        company=company, period='2026-06',
        fiscal_year=2026, period_num=6,
    )
    line = PayrollLine.objects.create(
        run=run, employee=employee,
        work_days=Decimal('22'),
        gross_salary=Decimal('15000000'),
        social_insurance_employee=Decimal('1500000'),
        health_insurance_employee=Decimal('300000'),
        unemployment_insurance_employee=Decimal('300000'),
        pit=Decimal('500000'),
        net_salary=Decimal('12400000'),
    )
    assert line.pk is not None
    assert line.net_salary == Decimal('12400000')
