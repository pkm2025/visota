"""Tests for PIT non-taxable allowances per ND 253/2026 + TT 87/2026.

Validates:
  VAL-PIT-004: PIT meal allowance is non-taxable up to 1,200,000 VND/month
  VAL-PIT-005: PIT pension/insurance allowance is non-taxable up to 3,000,000 VND/month
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
            "pit_medical_deduction": Decimal("23000000"),
            "pit_education_deduction": Decimal("24000000"),
            "pit_dependent_income_threshold": Decimal("3000000"),
            "pit_withholding_threshold": Decimal("5000000"),
            "effective_date": date(2026, 7, 1),
        },
    )


# --- TaxRateConfig field existence + defaults ---


class TestTaxRateConfigAllowanceFields:
    """All new allowance fields exist in TaxRateConfig with correct defaults."""

    def test_meal_allowance_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_meal_allowance == Decimal("1200000")

    def test_pension_allowance_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_pension_allowance == Decimal("3000000")

    def test_medical_deduction_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_medical_deduction == Decimal("23000000")

    def test_education_deduction_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_education_deduction == Decimal("24000000")

    def test_dependent_income_threshold_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_dependent_income_threshold == Decimal("3000000")

    def test_withholding_threshold_default(self, db):
        config = TaxRateConfig.objects.create(effective_date=date(2026, 7, 1))
        assert config.pit_withholding_threshold == Decimal("5000000")


# --- VAL-PIT-004: Meal allowance is non-taxable up to 1.2M/month ---


class TestMealAllowanceNonTaxable:
    """VAL-PIT-004: PIT meal allowance is non-taxable up to 1,200,000 VND/month."""

    @pytest.fixture
    def company(self, seeded_active_config):
        return Company.objects.create(
            code="MA",
            name="Meal Allowance Test",
            tax_code="0107777777",
            accounting_regime="tt133",
        )

    @pytest.fixture
    def make_emp(self, company):
        def _make(
            salary=Decimal("30000000"),
            meal=Decimal("0"),
            pension=Decimal("0"),
        ):
            dept = Department.objects.create(company=company, code=f"D{meal}{pension}", name="IT")
            pos = Position.objects.create(code=f"P{meal}{pension}", name="Dev", level=1)
            return Employee.objects.create(
                company=company,
                code=f"NV{meal}{pension}",
                full_name="Test",
                department=dept,
                position=pos,
                hire_date=date(2020, 1, 1),
                base_salary=salary,
                allowance=Decimal("0"),
                meal_allowance=meal,
                pension_allowance=pension,
            )

        return _make

    def test_meal_allowance_reduces_taxable_income(self, company, make_emp):
        """Employee with non-taxable meal allowance has PIT neutral to base salary.

        Per ND 253/2026 + TT 87/2026, meal allowance up to the cap is non-taxable:
        it is added to gross then excluded from taxable income. Compared to an
        employee with the same base salary and no meal allowance, PIT is equal
        (the allowance is PIT-neutral), but net pay is higher by the allowance.
        """
        emp_no_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("0"))
        emp_with_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("1000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_no_meal = run.lines.get(employee=emp_no_meal)
        line_with_meal = run.lines.get(employee=emp_with_meal)

        # PIT is identical: the allowance is added to gross then excluded, so it
        # does not change taxable income relative to the no-allowance baseline.
        assert line_with_meal.pit == line_no_meal.pit, (
            f"PIT with non-taxable meal allowance ({line_with_meal.pit}) should equal "
            f"without ({line_no_meal.pit}) — the allowance is PIT-neutral"
        )
        # And the allowance flows fully to net pay.
        assert line_with_meal.net_salary - line_no_meal.net_salary == Decimal("1000000"), (
            "Non-taxable meal allowance must reach net pay"
        )

    def test_meal_allowance_capped_at_1_2m(self, company, make_emp):
        """Meal allowance above 1.2M cap: only 1.2M is non-taxable; excess is taxable.

        An employee with 2M meal allowance pays more PIT than one with 1.2M,
        because the extra 800K (above the 1.2M cap) is taxable.
        """
        emp_meal_cap = make_emp(salary=Decimal("30000000"), meal=Decimal("1200000"))
        emp_meal_above = make_emp(salary=Decimal("30000000"), meal=Decimal("2000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_cap = run.lines.get(employee=emp_meal_cap)
        line_above = run.lines.get(employee=emp_meal_above)

        # PIT with 2M meal > PIT with 1.2M meal because the excess 800K is taxable.
        assert line_above.pit > line_cap.pit, (
            f"PIT with 2M meal ({line_above.pit}) should exceed PIT with 1.2M meal "
            f"({line_cap.pit}) — only 1.2M is non-taxable"
        )

    def test_meal_allowance_exact_cap_excluded(self, company, make_emp):
        """Verify the non-taxable portion is correctly capped at 1.2M.

        Compare an employee with 1.2M meal allowance (fully non-taxable) against
        an employee with the same total gross achieved via taxable allowance.
        The employee with non-taxable meal allowance pays less PIT.
        """
        # Employee A: 30M base + 1.2M non-taxable meal = 31.2M gross,
        #             taxable excludes the 1.2M meal.
        emp_meal = make_emp(salary=Decimal("30000000"), meal=Decimal("1200000"))
        # Employee B: 31.2M gross achieved with no meal allowance but higher
        #             base salary — the entire 31.2M minus standard deductions
        #             is taxable. We bump base by 1.2M to match gross.
        emp_taxable = make_emp(salary=Decimal("31200000"), meal=Decimal("0"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_meal = run.lines.get(employee=emp_meal)
        line_taxable = run.lines.get(employee=emp_taxable)

        # Both have the same gross (31.2M) but the meal-allowance employee has
        # 1.2M less taxable income, so their PIT must be lower.
        assert line_meal.gross_salary == line_taxable.gross_salary, (
            "Gross must match for the comparison to be meaningful"
        )
        assert line_meal.pit < line_taxable.pit, (
            f"Employee with non-taxable meal allowance ({line_meal.pit}) should pay "
            f"less PIT than one with the same gross as taxable salary ({line_taxable.pit})"
        )


# --- VAL-PIT-005: Pension/insurance allowance is non-taxable up to 3M/month ---


class TestPensionAllowanceNonTaxable:
    """VAL-PIT-005: PIT pension/insurance allowance is non-taxable up to 3,000,000 VND/month."""

    @pytest.fixture
    def company(self, seeded_active_config):
        return Company.objects.create(
            code="PA",
            name="Pension Allowance Test",
            tax_code="0106666666",
            accounting_regime="tt133",
        )

    @pytest.fixture
    def make_emp(self, company):
        counter = [0]

        def _make(
            salary=Decimal("30000000"),
            pension=Decimal("0"),
            meal=Decimal("0"),
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
                allowance=Decimal("0"),
                pension_allowance=pension,
                meal_allowance=meal,
            )

        return _make

    def test_pension_allowance_reduces_taxable_income(self, company, make_emp):
        """Employee with non-taxable pension allowance has PIT neutral to base salary.

        Per ND 253/2026 + TT 87/2026, pension allowance up to the cap is
        non-taxable: added to gross then excluded from taxable income. PIT is
        equal to an employee with the same base salary and no pension allowance,
        but net pay is higher by the allowance amount.
        """
        emp_no_pension = make_emp(salary=Decimal("30000000"), pension=Decimal("0"))
        emp_with_pension = make_emp(salary=Decimal("30000000"), pension=Decimal("2000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_no = run.lines.get(employee=emp_no_pension)
        line_with = run.lines.get(employee=emp_with_pension)

        assert line_with.pit == line_no.pit, (
            f"PIT with non-taxable pension allowance ({line_with.pit}) should equal "
            f"without ({line_no.pit}) — the allowance is PIT-neutral"
        )
        assert line_with.net_salary - line_no.net_salary == Decimal("2000000"), (
            "Non-taxable pension allowance must reach net pay"
        )

    def test_pension_allowance_capped_at_3m(self, company, make_emp):
        """Pension allowance above 3M cap: only 3M non-taxable; excess is taxable.

        An employee with 5M pension pays more PIT than one with 3M, because the
        extra 2M above the cap is taxable.
        """
        emp_3m = make_emp(salary=Decimal("30000000"), pension=Decimal("3000000"))
        emp_5m = make_emp(salary=Decimal("30000000"), pension=Decimal("5000000"))

        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")

        line_3m = run.lines.get(employee=emp_3m)
        line_5m = run.lines.get(employee=emp_5m)

        assert line_5m.pit > line_3m.pit, (
            f"PIT with 5M pension ({line_5m.pit}) should exceed PIT with 3M pension "
            f"({line_3m.pit}) — only 3M is non-taxable"
        )

    def test_combined_meal_and_pension_exclusion(self, company, make_emp):
        """Both meal (1.2M) and pension (3M) non-taxable simultaneously.

        Both allowances are PIT-neutral relative to the no-allowance baseline
        (each is added to gross then excluded from taxable), and both flow
        fully to net pay (total 4.2M).
        """
        emp_no_allowance = make_emp(
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

        line_no = run.lines.get(employee=emp_no_allowance)
        line_both = run.lines.get(employee=emp_both)

        # PIT is identical: both allowances are non-taxable (within caps).
        assert line_both.pit == line_no.pit, (
            f"PIT with both non-taxable allowances ({line_both.pit}) should equal "
            f"without ({line_no.pit}) — both are PIT-neutral"
        )
        # And the combined 4.2M of allowances reaches net pay.
        assert line_both.net_salary - line_no.net_salary == Decimal("4200000"), (
            "Both non-taxable allowances must reach net pay (1.2M + 3M = 4.2M)"
        )


# --- Seed verification ---


class TestSeedAllowanceValues:
    """Verify seed_demo produces correct allowance values."""

    def test_seed_demo_includes_allowance_fields(self, db):
        from django.core.management import call_command

        # seed_demo creates many models; we just need TaxRateConfig
        # which is update_or_create(is_active=True)
        call_command("seed_demo", verbosity=0)

        from apps.core.services.tax_config_service import TaxConfigService

        config = TaxConfigService.get_active()
        assert config is not None
        assert config.pit_meal_allowance == Decimal("1200000")
        assert config.pit_pension_allowance == Decimal("3000000")
        assert config.pit_medical_deduction == Decimal("23000000")
        assert config.pit_education_deduction == Decimal("24000000")
        assert config.pit_dependent_income_threshold == Decimal("3000000")
        assert config.pit_withholding_threshold == Decimal("5000000")
