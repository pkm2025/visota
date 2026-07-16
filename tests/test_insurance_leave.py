from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import Department, Employee, LeaveBalance, LeaveRecord, Position
from apps.hr.services import InsuranceService


@pytest.fixture
def emp(db):
    c = Company.objects.create(code="TCO", name="T")
    d = Department.objects.create(company=c, code="IT", name="IT")
    p = Position.objects.create(code="DEV", name="Dev", level=1)
    return Employee.objects.create(
        company=c,
        code="NV01",
        full_name="Test",
        department=d,
        position=p,
        hire_date=date(2020, 1, 1),
        base_salary=Decimal("15000000"),
    )


def test_insurance_calculation(emp):
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, "2026-06")
    # NV 10.5%: 8% + 1.5% + 1%
    assert ic.bhxh_employee == Decimal("1200000")  # 15M * 8%
    assert ic.bhyt_employee == Decimal("225000")  # 15M * 1.5%
    assert ic.bhtn_employee == Decimal("150000")  # 15M * 1%
    # DN 23.5%: 17% + 3% + 1% + 0.5% + 2% (KPCĐ)
    assert ic.bhxh_employer == Decimal("2550000")  # 15M * 17%
    assert ic.bhyt_employer == Decimal("450000")  # 15M * 3%
    assert ic.bhtn_employer == Decimal("150000")  # 15M * 1%
    assert ic.bhtnld_employer == Decimal("75000")  # 15M * 0.5%


def test_insurance_cap(emp):
    """Salary above cap -> capped at 50.6M (ND 161/2026)."""
    from apps.core.models import TaxRateConfig

    TaxRateConfig.objects.filter(is_active=True).delete()
    TaxRateConfig.objects.create(
        is_active=True,
        bhxh_cap=Decimal("50600000"),
        bhxh_base_salary=Decimal("2530000"),
        effective_date=date(2026, 7, 1),
    )
    emp.base_salary = Decimal("100000000")  # 100M > 50.6M
    emp.save()
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, "2026-07")
    assert ic.salary_base == Decimal("50600000")  # capped


def test_insurance_kpcd(emp):
    """Kinh phí công đoàn 2%."""
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, "2026-06")
    assert ic.kpcd_employer == Decimal("300000")  # 15M * 2%


def test_total_employer_includes_kpcd(emp):
    """VAL-BHXH-001: total_employer includes all 5 employer components (23.5%).

    BHXH 17% + BHYT 3% + BHTN 1% + BHTNLĐBNN 0.5% + KPCĐ 2% = 23.5%.
    For 15,000,000 VND base: 2,550,000 + 450,000 + 150,000 + 75,000 + 300,000 = 3,525,000.
    """
    svc = InsuranceService(company=emp.company)
    ic = svc.calculate_monthly(emp, "2026-06")
    # Sum of all 5 individual components
    expected_total = (
        ic.bhxh_employer
        + ic.bhyt_employer
        + ic.bhtn_employer
        + ic.bhtnld_employer
        + ic.kpcd_employer
    )
    assert ic.total_employer == expected_total
    # Exact value: 15,000,000 * 23.5% = 3,525,000
    assert ic.total_employer == Decimal("3525000")
    # Verify each component is present and non-zero
    assert ic.bhxh_employer == Decimal("2550000")  # 17%
    assert ic.bhyt_employer == Decimal("450000")  # 3%
    assert ic.bhtn_employer == Decimal("150000")  # 1%
    assert ic.bhtnld_employer == Decimal("75000")  # 0.5%
    assert ic.kpcd_employer == Decimal("300000")  # 2%


def test_annual_leave_balance(emp):
    lb = LeaveBalance.objects.create(
        employee=emp,
        fiscal_year=2026,
        standard_days=Decimal("12"),
        carried_forward=Decimal("3"),
    )
    assert lb.remaining_days == Decimal("15")  # 12 + 3 - 0


def test_leave_request(emp):
    lr = LeaveRecord.objects.create(
        employee=emp,
        leave_type="annual",
        start_date=date(2026, 6, 10),
        end_date=date(2026, 6, 12),
        days=Decimal("3"),
        reason="Nghỉ phép",
        status="approved",
    )
    assert lr.pk is not None
    assert lr.days == Decimal("3")


def test_maternity_leave(emp):
    lr = LeaveRecord.objects.create(
        employee=emp,
        leave_type="maternity",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        days=Decimal("180"),
        maternity_months=Decimal("6"),
        reason="Thai sản",
        status="approved",
    )
    assert lr.maternity_months == Decimal("6")
