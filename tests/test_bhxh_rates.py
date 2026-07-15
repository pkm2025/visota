"""Tests for BHXH rate compliance per ND 161/2026 (effective 01/07/2026).

Verifies:
- VAL-BHXH-001: Insurance cap is 50,600,000 VND
- VAL-BHXH-002: BHXH base salary is 2,530,000 VND
- VAL-BHXH-003: No hardcoded INSURANCE_CAP constant in apps/hr/
"""

import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from apps.core.models import Company, TaxRateConfig
from apps.hr.models import Department, Employee, Position
from apps.hr.services import InsuranceService


@pytest.fixture
def tax_config(db):
    TaxRateConfig.objects.filter(is_active=True).delete()
    return TaxRateConfig.objects.create(
        is_active=True,
        bhxh_cap=Decimal("50600000"),
        bhxh_base_salary=Decimal("2530000"),
        effective_date=date(2026, 7, 1),
    )


@pytest.fixture
def emp(db):
    c = Company.objects.create(code="BHXH", name="BHXH Test Co")
    d = Department.objects.create(company=c, code="IT", name="IT")
    p = Position.objects.create(code="DEV", name="Dev", level=1)
    return Employee.objects.create(
        company=c,
        code="BHXH01",
        full_name="Test BHXH",
        department=d,
        position=p,
        hire_date=date(2020, 1, 1),
        base_salary=Decimal("15000000"),
    )


# --- VAL-BHXH-001: Insurance cap is 50,600,000 VND ---


class TestBhxhCap:
    """VAL-BHXH-001: Insurance cap is 50,600,000 VND (20 x base salary 2,530,000)."""

    def test_cap_value_from_config(self, db, tax_config):
        """TaxRateConfig.bhxh_cap is 50,600,000."""
        assert tax_config.bhxh_cap == Decimal("50600000")

    def test_cap_applied_to_high_salary(self, db, tax_config, emp):
        """Salary above cap is capped at 50,600,000."""
        emp.base_salary = Decimal("100000000")  # 100M > 50.6M
        emp.save()
        svc = InsuranceService(company=emp.company)
        ic = svc.calculate_monthly(emp, "2026-07")
        assert ic.salary_base == Decimal("50600000")

    def test_cap_is_20x_base_salary(self, db, tax_config):
        """Cap should be exactly 20 × base salary."""
        assert tax_config.bhxh_cap == tax_config.bhxh_base_salary * 20


# --- VAL-BHXH-002: BHXH base salary is 2,530,000 VND ---


class TestBhxhBaseSalary:
    """VAL-BHXH-002: BHXH base salary is 2,530,000 VND."""

    def test_base_salary_value(self, db, tax_config):
        """TaxRateConfig.bhxh_base_salary is 2,530,000."""
        assert tax_config.bhxh_base_salary == Decimal("2530000")

    def test_model_default_bhxh_base_salary(self, db):
        """Model default for bhxh_base_salary is 2,530,000."""
        field = TaxRateConfig._meta.get_field("bhxh_base_salary")
        assert field.default == Decimal("2530000") or field.default == 2530000

    def test_model_default_bhxh_cap(self, db):
        """Model default for bhxh_cap is 50,600,000."""
        field = TaxRateConfig._meta.get_field("bhxh_cap")
        assert field.default == Decimal("50600000") or field.default == 50600000


# --- VAL-BHXH-003: No hardcoded INSURANCE_CAP constant ---


class TestNoHardcodedCap:
    """VAL-BHXH-003: No hardcoded INSURANCE_CAP constant in apps/hr/."""

    def test_no_insurance_cap_constant_in_hr(self):
        """Grep apps/hr/ for INSURANCE_CAP constant — should find nothing."""
        hr_dir = Path(__file__).resolve().parent.parent / "apps" / "hr"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"""
import pathlib, re
hr = pathlib.Path(r'{hr_dir}')
found = []
for f in hr.rglob('*.py'):
    text = f.read_text(encoding='utf-8')
    # Look for INSURANCE_CAP as an assignment (not in a comment or string)
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if re.search(r'\\bINSURANCE_CAP\\s*=', stripped):
            found.append(f'{{f.relative_to(hr)}}:{{i}}: {{stripped}}')
if found:
    print('FOUND:' + '\\n'.join(found))
else:
    print('NONE')
""",
            ],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        assert "NONE" in output, f"Hardcoded INSURANCE_CAP found:\n{output}"

    def test_insurance_service_reads_from_config(self, db, tax_config, emp):
        """InsuranceService reads cap from TaxRateConfig, not a constant."""
        emp.base_salary = Decimal("100000000")  # above cap
        emp.save()
        svc = InsuranceService(company=emp.company)
        # The cap should match what's in TaxRateConfig
        cap = svc._get_cap()
        assert cap == Decimal("50600000")
        assert cap == tax_config.bhxh_cap

    def test_insurance_service_uses_custom_cap(self, db, emp):
        """If TaxRateConfig has a different cap, InsuranceService uses it."""
        TaxRateConfig.objects.filter(is_active=True).delete()
        TaxRateConfig.objects.create(
            is_active=True,
            bhxh_cap=Decimal("30000000"),  # custom cap
            bhxh_base_salary=Decimal("1500000"),
            effective_date=date(2026, 7, 1),
        )
        emp.base_salary = Decimal("50000000")
        emp.save()
        svc = InsuranceService(company=emp.company)
        ic = svc.calculate_monthly(emp, "2026-07")
        assert ic.salary_base == Decimal("30000000")  # uses config cap, not hardcoded

    def test_insurance_service_fallback_when_no_config(self, db, emp):
        """When no TaxRateConfig exists, falls back to ND 161/2026 default (50.6M)."""
        TaxRateConfig.objects.filter(is_active=True).delete()
        emp.base_salary = Decimal("100000000")
        emp.save()
        svc = InsuranceService(company=emp.company)
        ic = svc.calculate_monthly(emp, "2026-07")
        assert ic.salary_base == Decimal("50600000")


# --- Seed verification ---


class TestSeedValues:
    """Verify seed_demo produces correct BHXH values."""

    def test_seed_creates_correct_bhxh_values(self, db):
        """seed_demo should create TaxRateConfig with correct BHXH rates."""
        from django.core.management import call_command

        TaxRateConfig.objects.all().delete()
        call_command("seed_demo", verbosity=0)
        config = TaxRateConfig.objects.filter(is_active=True).first()
        assert config is not None
        assert config.bhxh_cap == Decimal("50600000")
        assert config.bhxh_base_salary == Decimal("2530000")
