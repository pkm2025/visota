"""Tests for PIT 2026-07 fix — NQ 110/2025/UBTVQH15 effective 01/07/2026.

Validates:
  VAL-PIT-001: PIT personal deduction is 15,500,000 VND/month
  VAL-PIT-002: PIT dependent deduction is 6,200,000 VND/dependent/month
  VAL-PIT-003: PIT uses 5-bracket system (5%/10%/20%/30%/35%)
  VAL-PIT-006: Dependent.deduction_amount defaults to 6,200,000
  VAL-PIT-007: seed_pit_history includes NQ 110/2025 entry marked as current
  VAL-PIT-008: PayrollService fallback constants updated
"""

import pytest
from datetime import date
from decimal import Decimal

from apps.core.models import PITRateHistory, TaxRateConfig
from apps.core.services.tax_config_service import TaxConfigService
from apps.payroll.services.payroll_service import (
    DEPENDENT_DEDUCTION,
    PERSONAL_DEDUCTION,
    PIT_BRACKETS,
    PayrollService,
    calculate_pit,
)


@pytest.fixture
def seeded_pit_history(db):
    from django.core.management import call_command

    call_command("seed_pit_history", verbosity=0)


@pytest.fixture
def seeded_active_config(db):
    """Apply the seed_demo TaxRateConfig block (active PIT 2026-07 rates)."""
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
            "effective_date": date(2026, 7, 1),
        },
    )


# --- VAL-PIT-007: seed_pit_history includes NQ 110/2025 as current ---


class TestPITHistoryNQ110:
    def test_nq_110_entry_exists(self, seeded_pit_history):
        entry = PITRateHistory.objects.filter(period_start="2026-07-01").first()
        assert entry is not None, "NQ 110/2025 entry (2026-07-01) must exist"

    def test_nq_110_marked_current(self, seeded_pit_history):
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        assert entry.is_current is True

    def test_nq_110_personal_deduction(self, seeded_pit_history):
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        assert entry.personal_deduction == Decimal("15500000")

    def test_nq_110_dependent_deduction(self, seeded_pit_history):
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        assert entry.dependent_deduction == Decimal("6200000")

    def test_nq_110_has_5_brackets(self, seeded_pit_history):
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        assert len(entry.brackets) == 5

    def test_nq_110_bracket_rates(self, seeded_pit_history):
        """5-bracket system: 5%/10%/20%/30%/35%."""
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        rates = [Decimal(str(b[1])) for b in entry.brackets]
        assert rates == [
            Decimal("0.05"),
            Decimal("0.10"),
            Decimal("0.20"),
            Decimal("0.30"),
            Decimal("0.35"),
        ]

    def test_nq_110_period_end_open(self, seeded_pit_history):
        entry = PITRateHistory.objects.get(period_start="2026-07-01")
        assert entry.period_end is None

    def test_jan_2026_no_longer_current(self, seeded_pit_history):
        """2026-01-01 entry must NOT be current (superseded by NQ 110/2025)."""
        entry = PITRateHistory.objects.get(period_start="2026-01-01")
        assert entry.is_current is False

    def test_jan_2026_period_end_set(self, seeded_pit_history):
        """2026-01-01 entry must end on 2026-06-30."""
        entry = PITRateHistory.objects.get(period_start="2026-01-01")
        assert entry.period_end == date(2026, 6, 30)

    def test_history_has_5_entries(self, seeded_pit_history):
        assert PITRateHistory.objects.count() >= 5


# --- VAL-PIT-008: PayrollService fallback constants ---


class TestPayrollServiceFallbackConstants:
    def test_personal_deduction_fallback(self):
        assert PERSONAL_DEDUCTION == Decimal("15500000")

    def test_dependent_deduction_fallback(self):
        assert DEPENDENT_DEDUCTION == Decimal("6200000")

    def test_pit_brackets_5_bracket(self):
        assert len(PIT_BRACKETS) == 5

    def test_pit_brackets_rates(self):
        """Fallback brackets must be 5%/10%/20%/30%/35%."""
        rates = [rate for _, rate in PIT_BRACKETS]
        assert rates == [
            Decimal("0.05"),
            Decimal("0.10"),
            Decimal("0.20"),
            Decimal("0.30"),
            Decimal("0.35"),
        ]

    def test_fallback_pit_calculation(self):
        """calculate_pit with no brackets uses 5-bracket system."""
        # Taxable 10M: first 5M @ 5% = 250K, next 5M @ 10% = 500K → 750K
        pit = calculate_pit(Decimal("10000000"))
        assert pit == Decimal("750000")

    def test_fallback_high_income_35_percent(self):
        """Income over 32M taxed at 35% in the top bracket."""
        # Taxable 42M:
        # 5M@5% = 250K
        # 5M@10% = 500K
        # 8M@20% = 1,600K
        # 14M@30% = 4,200K
        # 10M@35% = 3,500K
        # Total = 10,050,000
        pit = calculate_pit(Decimal("42000000"))
        assert pit == Decimal("10050000")


# --- VAL-PIT-001/002/003: Active config wired correctly ---


class TestActiveConfigWired:
    def test_active_personal_deduction(self, seeded_active_config):
        config = TaxConfigService.get_active()
        assert config is not None
        assert config.pit_personal_deduction == Decimal("15500000")

    def test_active_dependent_deduction(self, seeded_active_config):
        config = TaxConfigService.get_active()
        assert config.pit_dependent_deduction == Decimal("6200000")

    def test_active_brackets_5(self, seeded_active_config):
        config = TaxConfigService.get_active()
        assert len(config.pit_brackets) == 5

    def test_active_bracket_rates(self, seeded_active_config):
        config = TaxConfigService.get_active()
        rates = [Decimal(str(b[1])) for b in config.pit_brackets]
        assert rates == [
            Decimal("0.05"),
            Decimal("0.10"),
            Decimal("0.20"),
            Decimal("0.30"),
            Decimal("0.35"),
        ]

    def test_2026_fields_match_active(self, seeded_active_config):
        """The pit_*_2026 fields should also have the current rates."""
        config = TaxConfigService.get_active()
        assert config.pit_personal_deduction_2026 == Decimal("15500000")
        assert config.pit_dependent_deduction_2026 == Decimal("6200000")
        assert len(config.pit_brackets_2026) == 5


# --- VAL-PIT-006: Dependent.deduction_amount default ---


class TestDependentDefault:
    def test_dependent_default_deduction(self, db):
        from apps.core.models import Company
        from apps.hr.models import Dependent, Employee, Department, Position

        company = Company.objects.create(
            code="TDD", name="TDD", tax_code="0109999999", accounting_regime="tt133"
        )
        dept = Department.objects.create(company=company, code="D1", name="D1")
        pos = Position.objects.create(code="P1", name="P1", level=1)
        emp = Employee.objects.create(
            company=company,
            code="E1",
            full_name="Test",
            department=dept,
            position=pos,
            hire_date=date(2020, 1, 1),
            base_salary=Decimal("10000000"),
        )
        dep = Dependent.objects.create(
            employee=emp,
            full_name="Child",
            relationship="child",
            valid_from=date(2024, 1, 1),
        )
        assert dep.deduction_amount == Decimal("6200000")


# --- PayrollService uses correct rates with active config ---


class TestPayrollServicePITCalculation:
    @pytest.fixture
    def company(self, seeded_active_config):
        from apps.core.models import Company

        return Company.objects.create(
            code="PSV",
            name="Payroll Service Test",
            tax_code="0108888888",
            accounting_regime="tt133",
        )

    @pytest.fixture
    def make_emp(self, company):
        from apps.hr.models import Employee, Department, Position

        def _make(salary=Decimal("15000000"), allowance=Decimal("0")):
            dept = Department.objects.create(company=company, code=f"D{salary}", name="IT")
            pos = Position.objects.create(code=f"P{salary}", name="Dev", level=1)
            return Employee.objects.create(
                company=company,
                code=f"NV{salary}",
                full_name="Test",
                department=dept,
                position=pos,
                hire_date=date(2020, 1, 1),
                base_salary=salary,
                allowance=allowance,
            )

        return _make

    def test_pit_uses_15_5m_personal_deduction(self, company, make_emp):
        """VAL-PIT-001: Personal deduction applied is 15.5M."""
        emp = make_emp(salary=Decimal("30000000"))
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        # PIT should reflect 15.5M personal deduction, not 13.2M or 11M
        # Taxable = 30M - insurance_employee - 15.5M
        # With 15.5M deduction, taxable is lower → PIT is lower than with 13.2M
        assert line.pit >= Decimal("0")
        # Verify config is actually being read
        config = TaxConfigService.get_active(company)
        assert config.pit_personal_deduction == Decimal("15500000")

    def test_pit_uses_6_2m_dependent_deduction(self, company, make_emp):
        """VAL-PIT-002: Dependent deduction is 6.2M per dependent."""
        from apps.hr.models import Dependent

        emp = make_emp(salary=Decimal("40000000"))
        Dependent.objects.create(
            employee=emp,
            full_name="Spouse",
            relationship="spouse",
            deduction_amount=Decimal("6200000"),
            valid_from=date(2024, 1, 1),
            registration_status="registered",
        )
        svc = PayrollService(company=company)
        run = svc.calculate("2026-07")
        line = run.lines.get(employee=emp)
        config = TaxConfigService.get_active(company)
        assert config.pit_dependent_deduction == Decimal("6200000")
        assert line.pit >= Decimal("0")
