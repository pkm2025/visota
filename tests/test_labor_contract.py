import pytest
from decimal import Decimal
from datetime import date
from apps.hr.models import Employee, Department, Position, LaborContract, Dependent
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


def test_contract_creation(emp):
    c = LaborContract.objects.create(
        company=emp.company, employee=emp, contract_no='HDL001',
        contract_type='fixed_term', start_date=date(2024,1,1),
        end_date=date(2026,12,31), salary_base=Decimal('15000000'),
        salary_gross=Decimal('17000000'), allowance_amount=Decimal('2000000'),
        insurance_salary_base=Decimal('15000000'), position_title='Dev',
        department=emp.department, status='active',
    )
    assert c.pk is not None
    assert c.join_insurance is True


def test_probation_contract(emp):
    c = LaborContract.objects.create(
        company=emp.company, employee=emp, contract_no='HDTV01',
        contract_type='probation', start_date=date(2026,6,1),
        probation_end_date=date(2026,7,1),
        salary_base=Decimal('12000000'), salary_gross=Decimal('12000000'),
        insurance_salary_base=Decimal('12000000'),
        position_title='Dev', department=emp.department, status='active',
    )
    assert c.contract_type == 'probation'


def test_dependent_creation(emp):
    dep = Dependent.objects.create(
        employee=emp, full_name='Nguyễn B', relationship='child',
        birth_date=date(2015,3,10), deduction_amount=Decimal('4400000'),
        valid_from=date(2024,1,1),
    )
    assert dep.pk is not None
    assert dep.deduction_amount == Decimal('4400000')
    assert dep.registration_status == 'pending'


def test_multiple_dependents(emp):
    for i in range(3):
        Dependent.objects.create(
            employee=emp, full_name=f'Dep {i}', relationship='child',
            birth_date=date(2015,1,1), deduction_amount=Decimal('4400000'),
            valid_from=date(2024,1,1),
        )
    assert emp.dependents.count() == 3
