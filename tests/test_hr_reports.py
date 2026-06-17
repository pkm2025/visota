"""Task 4 tests: HR report services — D62, labor usage, salary fund, PIT monthly."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.hr.models import (
    Department,
    Dependent,
    Employee,
    InsuranceContribution,
    Position,
)
from apps.payroll.models import PayrollLine, PayrollRun
from apps.reporting.services.hr_reports import (
    D62ReportService,
    LaborUsageReportService,
    PITMonthlyReportService,
    SalaryFundReportService,
)


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="TCO",
        name="Test Co",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.fixture
def make_emp(company):
    def _make(code, name, status="active", hire_date=date(2020, 1, 1)):
        dept, _ = Department.objects.get_or_create(
            company=company, code="IT", defaults={"name": "IT"}
        )
        pos, _ = Position.objects.get_or_create(
            code="DEV", defaults={"name": "Dev", "level": 1}
        )
        return Employee.objects.create(
            company=company,
            code=code,
            full_name=name,
            department=dept,
            position=pos,
            hire_date=hire_date,
            base_salary=Decimal("15000000"),
            status=status,
        )

    return _make


def _create_insurance(company, emp, period="2026-06"):
    """Create an InsuranceContribution row mirroring payroll calc (15M base)."""
    base = Decimal("15000000")
    return InsuranceContribution.objects.create(
        company=company,
        employee=emp,
        period=period,
        salary_base=base,
        bhxh_employee=base * Decimal("0.08"),
        bhyt_employee=base * Decimal("0.015"),
        bhtn_employee=base * Decimal("0.01"),
        total_employee=base * Decimal("0.105"),
        bhxh_employer=base * Decimal("0.175"),
        bhyt_employer=base * Decimal("0.03"),
        bhtn_employer=base * Decimal("0.01"),
        bhtnld_employer=base * Decimal("0.005"),
        kpcd_employer=base * Decimal("0.02"),
        total_employer=base * Decimal("0.22"),
    )


def _create_payroll_line(company, emp, period="2026-06", gross=None):
    run, _ = PayrollRun.objects.get_or_create(
        company=company,
        period=period,
        defaults={"fiscal_year": 2026, "period_num": 6, "status": "calculated"},
    )
    if gross is None:
        gross = Decimal("15000000")
    ins_emp = Decimal("1575000")  # 10.5% of 15M
    pit = Decimal("121250")
    line = PayrollLine.objects.create(
        run=run,
        employee=emp,
        line_no=1,
        gross_salary=gross,
        social_insurance_employee=Decimal("1200000"),
        health_insurance_employee=Decimal("225000"),
        unemployment_insurance_employee=Decimal("150000"),
        pit=pit,
        net_salary=gross - ins_emp - pit,
    )
    # Aggregate line totals into run
    run.total_gross = gross
    run.total_insurance_employee = ins_emp
    run.total_pit = pit
    run.total_net = gross - ins_emp - pit
    run.save()
    return run, line


# --- D62 Report ---


def test_d62_report_loads(company, make_emp):
    emp = make_emp("NV001", "Nguyễn Thị Mai")
    _create_insurance(company, emp, period="2026-06")

    report = D62ReportService(company=company).generate(fiscal_year=2026, period=6)

    assert "rows" in report
    assert len(report["rows"]) == 1
    row = report["rows"][0]
    assert row["employee_code"] == "NV001"
    assert row["name"] == "Nguyễn Thị Mai"
    assert row["salary_base"] == Decimal("15000000")
    assert row["bhxh_emp"] == Decimal("1200000")  # 8%
    assert row["bhyt_emp"] == Decimal("225000")  # 1.5%
    assert row["bhtn_emp"] == Decimal("150000")  # 1%
    assert row["total_emp"] == Decimal("1575000")  # 10.5%
    assert row["bhxh_er"] == Decimal("2625000")  # 17.5%
    # Grand totals
    assert report["grand_total_emp"] == Decimal("1575000")
    assert report["grand_total_er"] == Decimal("3300000")  # 22% of 15M
    assert report["grand_salary_base"] == Decimal("15000000")


def test_labor_usage_report(company, make_emp):
    # Active + new hire + resigned
    make_emp("NV001", "A", status="active", hire_date=date(2020, 1, 1))
    make_emp("NV002", "B", status="active", hire_date=date(2026, 3, 1))
    make_emp("NV003", "C", status="resigned", hire_date=date(2018, 1, 1))

    report = LaborUsageReportService(company=company).generate(fiscal_year=2026)

    assert report["total_employees"] == 3
    assert report["active_count"] == 2
    assert report["resigned_count"] == 1
    # New hires in 2026
    assert report["new_hires"] == 1
    # Per-department breakdown
    dept_codes = [d["department_code"] for d in report["by_department"]]
    assert "IT" in dept_codes


def test_salary_fund_report(company, make_emp):
    emp = make_emp("NV001", "A")
    run, _line = _create_payroll_line(company, emp, period="2026-06")

    report = SalaryFundReportService(company=company).generate(
        fiscal_year=2026, period=6
    )

    assert report["period"] == "2026-06"
    assert report["total_gross"] == Decimal("15000000")
    assert report["total_pit"] == Decimal("121250")
    assert report["total_net"] == Decimal("15000000") - Decimal(
        "1575000"
    ) - Decimal("121250")
    assert report["total_insurance_employee"] == Decimal("1575000")


def test_pit_monthly_report(company, make_emp):
    emp = make_emp("NV001", "A")
    # Salary high enough that gross - insurance - family deduction > 0
    emp.base_salary = Decimal("30000000")
    emp.save()
    # Add dependent for deduction context
    Dependent.objects.create(
        employee=emp,
        full_name="Nguyễn B",
        relationship="child",
        birth_date=date(2015, 1, 1),
        deduction_amount=Decimal("4400000"),
        valid_from=date(2024, 1, 1),
        registration_status="registered",
    )
    _create_payroll_line(company, emp, period="2026-06", gross=Decimal("30000000"))

    report = PITMonthlyReportService(company=company).generate(
        fiscal_year=2026, period=6
    )

    assert "rows" in report
    assert len(report["rows"]) == 1
    row = report["rows"][0]
    assert row["employee_code"] == "NV001"
    assert row["gross"] == Decimal("30000000")
    assert row["insurance_deduction"] == Decimal("1575000")
    assert row["dependents"] == 1
    assert row["pit"] == Decimal("121250")
    # taxable = 30M - 1.575M - 11M personal - 4.4M dependent = 13.025M
    assert row["taxable"] == Decimal("13025000")
