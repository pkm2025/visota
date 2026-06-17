from datetime import date

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Employee, Position


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_department_creation(company):
    d = Department.objects.create(
        company=company, code='BH', name='Bán hàng',
    )
    assert d.pk is not None
    assert str(d) == 'BH - Bán hàng'


@pytest.mark.django_db
def test_position_creation():
    p = Position.objects.create(code='NV', name='Nhân viên', level=1)
    assert p.pk is not None
    assert str(p) == 'NV - Nhân viên'


def test_employee_creation(company):
    dept = Department.objects.create(company=company, code='BH', name='BH')
    pos = Position.objects.create(code='NV', name='NV', level=1)
    emp = Employee.objects.create(
        company=company, code='NV001',
        full_name='Nguyễn Văn A',
        birth_date=date(1990, 5, 15),
        gender='male',
        id_card_no='001123456789',
        personal_tax_code='037123456789',
        social_insurance_no='1234567890',
        department=dept, position=pos,
        hire_date=date(2020, 1, 1),
        base_salary=15000000,
        bank_account_no='1234567890',
        bank_id='VCB',
        status='active',
    )
    assert emp.pk is not None
    assert str(emp) == 'NV001 - Nguyễn Văn A'
    assert emp.status == 'active'


def test_employee_defaults(company):
    dept = Department.objects.create(company=company, code='X', name='X')
    pos = Position.objects.create(code='X', name='X', level=1)
    emp = Employee(
        company=company, code='NV001', full_name='Test',
        department=dept, position=pos, hire_date=date(2020, 1, 1),
        base_salary=0,
    )
    assert emp.gender == 'male'
    assert emp.status == 'active'
    assert emp.is_active is True
