"""Regression tests for PIT allowance gross integration (fix-pit-allowances-gross).

Validates:
  VAL-PIT-001: Meal allowance added to gross, then excluded from taxable, included in net.
  VAL-PIT-002: Pension allowance added to gross, then excluded from taxable, included in net.

Before the fix, meal/pension allowances were excluded from taxable income but never
added to gross or net pay, causing a "double-deduct" (PIT reduced without the
allowance actually being paid to the employee).
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company, TaxRateConfig
from apps.hr.models import Department, Employee, Position
from apps.payroll.services.payroll_service import PayrollService


@pytest.fixture
def seeded_active_config(db):
    """Apply the seed_demo TaxRateConfig block with PIT 2026-07 rates + allowances."""
    TaxRateConfig.objects.update_or_create(
        is_active=True,
        defaults={
            "pit_personal_deduction": Decimal("15500000"),
            "pit_dependent_deduction": Decimal("6200000"),
            "pit_brackets": [
                [5000000, "0.05"],
                [10000000, "0.10"],
                [18000000, "0.20"],
                [32000000, "0.30"],
                [999999999, "0.35"],
            ],
            "pit_personal_deduction_2026": Decimal("15500000"),
            "pit_dependent_deduction_2026": Decimal("6200000"),
            "pit_brackets_2026": [
                [5000000, "0.05"],
                [10000000, "0.10"],
                [18000000, "0.20"],
                [32000000, "0.30"],
                [999999999, "0.35"],
            ],
            # Non-taxable allowances (ND 253/2026 + TT 87/2026)
            "pit_meal_allowance": Decimal("1200000"),
            "pit_pension_allowance": Decimal("3000000"),
            "effective_date": date(2026, 7, 1),
        },
    )


@pytest.fixture
def company(seeded_active_config):
    return Company.objects.create(
        code="PAG",
        name="PIT Allowance Gross Test",
        tax_code="0105554444",
        accounting_regime="tt133",
    )


@pytest.fixture
def make_emp(company):
    """Factory for employees with full allowance control."""
    counter = [0]

    def _make(
        salary=Decimal("30000000"),
        allowance=Decimal("0"),
        meal=Decimal("0"),
        pension=Decimal("0"),
    ):
        counter[0] += 1
        dept = Department.objects.create(company=company, code=f"D{counter[0]}", name="IT")
        pos = Position.objects.create(code=f"P{counter[0]}", name="Dev", level=1)
        return Employee.objects.create(
            company=company,
            code=f"NV{counter[0]}",
            full_name="Test",
            department=dept,
            position=pos,
            hire_date=date(2020, 1, 1),
            base_salary=salary,
            allowance=allowance,
            meal_allowance=meal,
            pension_allowance=pension,
        )

    return _make


# --- VAL-PIT-001: Meal allowance added to gross, excluded from taxable, in net ---


class TestMealAllowanceGrossIntegration:
    """VAL-PIT-001: Meal allowance added to gross then excluded from taxable.

    Scenario: employee with meal_allowance=1,200,000.
    Before fix: allowance excluded from taxable but not added to gross -> net pay
    did not include the allowance (a "double-deduct" of nonexistent gross income).
    After fix: gross includes meal_allowance, taxable excludes up to the cap,
    and net pay includes the full allowance.
    """

    def test_meal_allowance_included_in_gross(self, company, make_emp):
        emp = make_emp(
            salary=Decimal("30000000"),
            meal=Decimal("1200000"),
        )
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        # gross = base_salary + allowance + meal + pension = 30M + 0 + 1.2M + 0
        assert line.gross_salary == Decimal("31200000"), (
            f"Expected gross 31,200,000 to include meal allowance, got {line.gross_salary}"
        )

    def test_meal_allowance_included_in_net(self, company, make_emp):
        """Net pay must include the meal allowance (it is non-taxable income)."""
        emp_no_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("0"))
        emp_with_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("1200000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_no = run.lines.get(employee=emp_no_meal)
        line_with = run.lines.get(employee=emp_with_meal)

        # The non-taxable allowance flows fully to net (PIT is unaffected by
        # the allowance since it is excluded from taxable, but gross is higher).
        # Therefore net_with - net_no must equal the allowance amount.
        net_diff = line_with.net_salary - line_no.net_salary
        assert net_diff == Decimal("1200000"), (
            f"Net pay difference ({net_diff}) should equal meal allowance "
            f"1,200,000 — allowance must reach net pay"
        )

    def test_meal_allowance_taxable_exclusion_capped(self, company, make_emp):
        """Meal allowance above 1.2M cap: only 1.2M excluded; excess is taxable."""
        emp_at_cap = make_emp(salary=Decimal("30000000"), meal=Decimal("1200000"))
        emp_above_cap = make_emp(salary=Decimal("30000000"), meal=Decimal("2000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_cap = run.lines.get(employee=emp_at_cap)
        line_above = run.lines.get(employee=emp_above_cap)

        # PIT with 2M meal > PIT with 1.2M meal because the extra 800K is taxable
        assert line_above.pit > line_cap.pit, (
            f"PIT with 2M meal ({line_above.pit}) should exceed PIT with 1.2M meal "
            f"({line_cap.pit}) — only 1.2M is excluded from taxable"
        )

    def test_meal_allowance_does_not_double_deduct(self, company, make_emp):
        """Regression: non-taxable meal allowance is PIT-neutral.

        Before the fix, the meal allowance was excluded from taxable income but
        never added to gross, so it artificially reduced PIT for income that was
        never paid (a "double-deduct" of nonexistent gross). After the fix, the
        allowance is added to gross and then excluded from taxable, so PIT is
        unchanged relative to the same employee without the allowance, while the
        allowance flows fully to net pay.
        """
        emp_no_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("0"))
        emp_1_2m_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("1200000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_no = run.lines.get(employee=emp_no_meal)
        line_1_2 = run.lines.get(employee=emp_1_2m_meal)

        # PIT must be identical: the allowance is added to gross then excluded
        # from taxable, so it has no net effect on PIT.
        assert line_no.pit == line_1_2.pit, (
            f"PIT without meal ({line_no.pit}) should equal PIT with non-taxable "
            f"meal allowance ({line_1_2.pit}) — the allowance is PIT-neutral"
        )
        # And the allowance must reach net pay (this is the fix).
        assert line_1_2.net_salary - line_no.net_salary == Decimal("1200000")


# --- VAL-PIT-002: Pension allowance added to gross, excluded from taxable, in net ---


class TestPensionAllowanceGrossIntegration:
    """VAL-PIT-002: Pension allowance added to gross then excluded from taxable.

    Scenario: employee with pension_allowance=3,000,000.
    """

    def test_pension_allowance_included_in_gross(self, company, make_emp):
        emp = make_emp(
            salary=Decimal("30000000"),
            pension=Decimal("3000000"),
        )
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        # gross = 30M + 0 + 0 + 3M = 33M
        assert line.gross_salary == Decimal("33000000"), (
            f"Expected gross 33,000,000 to include pension allowance, got {line.gross_salary}"
        )

    def test_pension_allowance_included_in_net(self, company, make_emp):
        emp_no = make_emp(salary=Decimal("30000000"), pension=Decimal("0"))
        emp_with = make_emp(salary=Decimal("30000000"), pension=Decimal("3000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_no = run.lines.get(employee=emp_no)
        line_with = run.lines.get(employee=emp_with)

        net_diff = line_with.net_salary - line_no.net_salary
        assert net_diff == Decimal("3000000"), (
            f"Net pay difference ({net_diff}) should equal pension allowance "
            f"3,000,000 — allowance must reach net pay"
        )

    def test_pension_allowance_capped_at_3m(self, company, make_emp):
        """Pension allowance above 3M cap: only 3M excluded from taxable."""
        emp_3m = make_emp(salary=Decimal("30000000"), pension=Decimal("3000000"))
        emp_5m = make_emp(salary=Decimal("30000000"), pension=Decimal("5000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_3m = run.lines.get(employee=emp_3m)
        line_5m = run.lines.get(employee=emp_5m)

        # PIT with 5M pension > PIT with 3M pension because extra 2M is taxable
        assert line_5m.pit > line_3m.pit, (
            f"PIT with 5M pension ({line_5m.pit}) should exceed PIT with 3M pension "
            f"({line_3m.pit}) — only 3M is excluded from taxable"
        )


# --- Combined: both allowances together ---


class TestCombinedAllowancesGrossIntegration:
    """Both meal and pension allowances in gross, excluded from taxable, in net."""

    def test_both_allowances_in_gross(self, company, make_emp):
        emp = make_emp(
            salary=Decimal("30000000"),
            meal=Decimal("1200000"),
            pension=Decimal("3000000"),
        )
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        # gross = 30M + 0 + 1.2M + 3M = 34.2M
        assert line.gross_salary == Decimal("34200000"), (
            f"Expected gross 34,200,000 with both allowances, got {line.gross_salary}"
        )

    def test_both_allowances_in_net(self, company, make_emp):
        emp_none = make_emp(
            salary=Decimal("30000000"),
            meal=Decimal("0"),
            pension=Decimal("0"),
        )
        emp_both = make_emp(
            salary=Decimal("30000000"),
            meal=Decimal("1200000"),
            pension=Decimal("3000000"),
        )

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_none = run.lines.get(employee=emp_none)
        line_both = run.lines.get(employee=emp_both)

        # Both allowances are non-taxable, so they flow 100% to net.
        net_diff = line_both.net_salary - line_none.net_salary
        assert net_diff == Decimal("4200000"), (
            f"Net difference ({net_diff}) should equal 4,200,000 (1.2M + 3M) — "
            f"both non-taxable allowances must reach net pay"
        )

    def test_zero_allowances_unchanged(self, company, make_emp):
        """Employee with no allowances: gross equals base_salary + allowance."""
        emp = make_emp(
            salary=Decimal("30000000"),
            allowance=Decimal("2000000"),
            meal=Decimal("0"),
            pension=Decimal("0"),
        )
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        assert line.gross_salary == Decimal("32000000")
