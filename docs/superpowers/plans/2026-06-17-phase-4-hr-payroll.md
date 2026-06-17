# Phase 4: HR + Payroll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Build the HR + Payroll module. Employee master data, monthly attendance, payroll calculation with Vietnamese BHXH/BHYT/BHTN + PIT, auto-voucher generation (N641/642 / C334, C3336, C3383, C3384, C3386).

**Architecture:** `apps/hr` app owns Employee/Department/Position models. `apps/payroll` app owns Attendance/PayrollRun/PayrollLine models + PayrollService. PayrollService generates accounting voucher per pay period.

**Tech Stack:** Django 5.2, MariaDB 11.4, pytest.

---

## Task 1: HR app — Department + Position + Employee models

**Files:**
- Create: `apps/hr/` (apps.py, models/{__init__.py, employee.py}, migrations/)
- Modify: `config/settings/base.py`
- Test: `tests/test_employee.py`

- [ ] **Step 1: Write tests**

`tests/test_employee.py`:
```python
import pytest
from datetime import date
from apps.hr.models import Department, Position, Employee
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_department_creation(company):
    d = Department.objects.create(
        company=company, code='BH', name='Bán hàng',
    )
    assert d.pk is not None
    assert str(d) == 'BH - Bán hàng'


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
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/hr/apps.py**

```python
from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr'
    verbose_name = 'Human Resources'
```

- [ ] **Step 4: Create apps/hr/models/employee.py**

```python
"""HR models: Department, Position, Employee."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class Department(CompanyOwnedModel):
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='departments', db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children',
    )
    manager_code = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'hr_department'
        unique_together = [('company', 'code')]
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Position(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    level = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    objects = models.Manager()

    class Meta:
        db_table = 'hr_position'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Employee(CompanyOwnedModel):
    class Gender(models.TextChoices):
        MALE = 'male', 'Nam'
        FEMALE = 'female', 'Nữ'
        OTHER = 'other', 'Khác'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Đang làm việc'
        ON_LEAVE = 'on_leave', 'Nghỉ phép'
        RESIGNED = 'resigned', 'Đã nghỉ việc'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='employees', db_index=True,
    )
    code = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=Gender.choices, default=Gender.MALE,
    )
    id_card_no = models.CharField(max_length=20, blank=True, default='')
    id_card_date = models.DateField(null=True, blank=True)
    id_card_place = models.CharField(max_length=255, blank=True, default='')
    personal_tax_code = models.CharField(max_length=20, blank=True, default='')
    social_insurance_no = models.CharField(max_length=20, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')

    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='employees',
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='employees',
    )

    hire_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    official_date = models.DateField(null=True, blank=True)
    leave_date = models.DateField(null=True, blank=True)

    base_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    allowance = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bank_account_no = models.CharField(max_length=50, blank=True, default='')
    bank_id = models.CharField(max_length=20, blank=True, default='')

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'hr_employee'
        unique_together = [('company', 'code')]
        ordering = ['code']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f'{self.code} - {self.full_name}'
```

- [ ] **Step 5: Create __init__.py, add to INSTALLED_APPS, migration, tests, commit**

```python
# apps/hr/models/__init__.py
from .employee import Department, Position, Employee
__all__ = ['Department', 'Position', 'Employee']
```

Add `'apps.hr',` after `'apps.assets',` in `config/settings/base.py`.

```bash
.venv/bin/python manage.py makemigrations hr
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_employee.py -v
.venv/bin/pytest -v
git add apps/hr/ config/settings/base.py tests/test_employee.py
git commit -m "feat(hr): Department + Position + Employee models

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Payroll app — Attendance + PayrollRun + PayrollLine

**Files:**
- Create: `apps/payroll/` (apps.py, models.py, migrations/)
- Modify: `config/settings/base.py`
- Test: `tests/test_payroll_models.py`

- [ ] **Step 1: Write tests**

`tests/test_payroll_models.py`:
```python
import pytest
from datetime import date
from decimal import Decimal
from apps.payroll.models import AttendanceRecord, PayrollRun, PayrollLine
from apps.hr.models import Department, Position, Employee
from apps.core.models import Company


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
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/payroll/apps.py**

```python
from django.apps import AppConfig


class PayrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payroll'
    verbose_name = 'Payroll'
```

- [ ] **Step 4: Create apps/payroll/models.py**

```python
"""Payroll models: AttendanceRecord, PayrollRun, PayrollLine."""
from django.db import models


class AttendanceRecord(models.Model):
    """Daily attendance for an employee."""

    class Status(models.TextChoices):
        PRESENT = 'present', 'Có mặt'
        LATE = 'late', 'Đi trễ'
        EARLY_LEAVE = 'early_leave', 'Về sớm'
        ABSENT = 'absent', 'Vắng'
        LEAVE = 'leave', 'Nghỉ phép'
        HOLIDAY = 'holiday', 'Nghỉ lễ'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='attendance_records', db_index=True,
    )
    employee = models.ForeignKey(
        'hr.Employee', on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    attendance_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PRESENT,
    )
    work_days = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.CharField(max_length=500, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'attendance_record'
        unique_together = [('employee', 'attendance_date')]
        ordering = ['-attendance_date']
        indexes = [
            models.Index(fields=['company', 'attendance_date']),
        ]

    def __str__(self):
        return f'{self.employee.code} {self.attendance_date}: {self.status}'


class PayrollRun(models.Model):
    """Monthly payroll run for a company."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Lưu tạm'
        CALCULATED = 'calculated', 'Đã tính'
        POSTED = 'posted', 'Đã ghi sổ'
        PAID = 'paid', 'Đã trả lương'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='payroll_runs', db_index=True,
    )
    period = models.CharField(max_length=7, help_text='YYYY-MM')
    fiscal_year = models.SmallIntegerField()
    period_num = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )

    total_gross = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_pit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_net = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    gl_voucher = models.ForeignKey(
        'ledger.AccountingVoucher', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payroll_runs',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'payroll_run'
        unique_together = [('company', 'period')]
        ordering = ['-period']

    def __str__(self):
        return f'Payroll {self.period}'


class PayrollLine(models.Model):
    """Per-employee payroll calculation."""

    run = models.ForeignKey(
        PayrollRun, on_delete=models.CASCADE, related_name='lines',
    )
    employee = models.ForeignKey(
        'hr.Employee', on_delete=models.PROTECT, related_name='payroll_lines',
    )
    line_no = models.PositiveSmallIntegerField()

    work_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    base_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    allowance_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    overtime_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    gross_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Insurance — employee portion (deducted from gross)
    social_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    health_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    unemployment_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Insurance — employer portion (additional cost)
    social_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    health_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    unemployment_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    pit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    net_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    objects = models.Manager()

    class Meta:
        db_table = 'payroll_line'
        unique_together = [('run', 'employee')]
        ordering = ['line_no']

    def __str__(self):
        return f'{self.employee.code}: gross={self.gross_salary} net={self.net_salary}'
```

- [ ] **Step 5: Migration + tests + commit**

Add `'apps.payroll',` after `'apps.hr',` in INSTALLED_APPS.

```bash
.venv/bin/python manage.py makemigrations payroll
.venv/bin/python manage.py migrate
.venv/bin/pytest tests/test_payroll_models.py -v
.venv/bin/pytest -v
git add apps/payroll/ config/settings/base.py tests/test_payroll_models.py
git commit -m "feat(payroll): AttendanceRecord + PayrollRun + PayrollLine models

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: PayrollService — BHXH + PIT calculation + auto-voucher

**Files:**
- Create: `apps/payroll/services/__init__.py`, `apps/payroll/services/payroll_service.py`
- Test: `tests/test_payroll_service.py`

- [ ] **Step 1: Write tests**

`tests/test_payroll_service.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from apps.payroll.services import PayrollService
from apps.payroll.models import PayrollRun, PayrollLine
from apps.hr.models import Department, Position, Employee
from apps.ledger.models import AccountingVoucher
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    dept = Department.objects.create(company=company, code='BH', name='BH')
    pos = Position.objects.create(code='NV', name='NV', level=1)
    # 2 employees with different salaries
    emp1 = Employee.objects.create(
        company=company, code='NV001', full_name='A',
        department=dept, position=pos, hire_date=date(2020, 1, 1),
        base_salary=Decimal('15000000'),
    )
    emp2 = Employee.objects.create(
        company=company, code='NV002', full_name='B',
        department=dept, position=pos, hire_date=date(2021, 1, 1),
        base_salary=Decimal('20000000'),
    )
    return company, [emp1, emp2]


def test_calculate_payroll(setup):
    company, employees = setup
    service = PayrollService(company=company)

    run = service.calculate(period='2026-06', standard_work_days=22)

    assert run.lines.count() == 2
    assert run.status == 'calculated'

    # Employee 1: base 15M, 22/22 days → gross = 15M
    line1 = run.lines.get(employee=employees[0])
    assert line1.gross_salary == Decimal('15000000')
    # BHXH employee = 8%, BHYT = 1.5%, BHTN = 1%
    assert line1.social_insurance_employee == Decimal('1200000')  # 15M * 8%
    assert line1.health_insurance_employee == Decimal('225000')    # 15M * 1.5%
    assert line1.unemployment_insurance_employee == Decimal('150000')  # 15M * 1%
    # PIT is simplified (gross - insurance - deduction 11M) * rate
    # Taxable = 15M - 1.575M - 11M = 2.425M → 5% = 121250
    assert line1.pit > 0
    assert line1.net_salary < line1.gross_salary


def test_post_payroll_generates_voucher(setup):
    company, employees = setup
    service = PayrollService(company=company)

    run = service.calculate(period='2026-06', standard_work_days=22)
    service.post(run)

    run.refresh_from_db()
    assert run.status == 'posted'
    assert run.gl_voucher is not None

    voucher = run.gl_voucher
    assert voucher.is_posted
    assert voucher.voucher_type == 'payroll'

    # Should have N642 (expense), C334 (payable), C3336 (PIT), C3383/3384/3386 (insurance)
    codes = {l.account_code for l in voucher.lines.all()}
    assert '642' in codes  # salary expense
    assert '334' in codes  # payable to employees
    assert '3336' in codes  # PIT payable
    assert '3383' in codes  # BHXH payable


def test_payroll_idempotent(setup):
    """Calculating same period twice does not duplicate."""
    company, employees = setup
    service = PayrollService(company=company)

    run1 = service.calculate(period='2026-06', standard_work_days=22)
    run2 = service.calculate(period='2026-06', standard_work_days=22)
    assert run1.id == run2.id  # same run
    assert run2.lines.count() == 2  # not doubled
```

- [ ] **Step 2: Run to fail**

- [ ] **Step 3: Create apps/payroll/services/payroll_service.py**

```python
"""PayrollService — calculate salary + BHXH + PIT + post voucher."""
from decimal import Decimal
from datetime import date
from django.db import transaction

from apps.payroll.models import PayrollRun, PayrollLine
from apps.hr.models import Employee
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService


# 2024-2026 Vietnamese insurance rates
INSURANCE_RATES = {
    'social_employee': Decimal('0.08'),       # BHXH NV đóng 8%
    'social_employer': Decimal('0.175'),      # BHXH DN đóng 17.5%
    'health_employee': Decimal('0.015'),      # BHYT NV 1.5%
    'health_employer': Decimal('0.03'),       # BHYT DN 3%
    'unemployment_employee': Decimal('0.01'),  # BHTN NV 1%
    'unemployment_employer': Decimal('0.01'),  # BHTN DN 1%
}

# PIT brackets (monthly taxable income, VND)
PIT_BRACKETS = [
    (Decimal('5000000'), Decimal('0.05')),
    (Decimal('10000000'), Decimal('0.10')),
    (Decimal('18000000'), Decimal('0.15')),
    (Decimal('32000000'), Decimal('0.20')),
    (Decimal('52000000'), Decimal('0.25')),
    (Decimal('80000000'), Decimal('0.30')),
    (Decimal('999999999'), Decimal('0.35')),
]

PERSONAL_DEDUCTION = Decimal('11000000')  # Giảm trừ gia cảnh bản thân
DEPENDENT_DEDUCTION = Decimal('4400000')   # Mỗi người phụ thuộc


def calculate_pit(taxable_income: Decimal) -> Decimal:
    """Progressive PIT calculation based on brackets."""
    if taxable_income <= 0:
        return Decimal('0')
    pit = Decimal('0')
    remaining = taxable_income
    prev_cap = Decimal('0')
    for cap, rate in PIT_BRACKETS:
        if remaining <= 0:
            break
        slab = min(remaining, cap - prev_cap)
        pit += slab * rate
        remaining -= slab
        prev_cap = cap
    return pit.quantize(Decimal('1'))  # round to VND


class PayrollService:
    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def calculate(self, period: str, standard_work_days: int = 22) -> PayrollRun:
        """Calculate payroll for all active employees in given period (YYYY-MM).

        Idempotent: returns existing PayrollRun if already calculated.
        """
        fiscal_year = int(period.split('-')[0])
        period_num = int(period.split('-')[1])

        run, created = PayrollRun.objects.get_or_create(
            company=self.company, period=period,
            defaults={
                'fiscal_year': fiscal_year,
                'period_num': period_num,
                'status': 'draft',
            },
        )

        if run.status in ('posted', 'paid'):
            return run  # don't recalculate posted payroll

        # Clear existing lines (in case of recalculation)
        run.lines.all().delete()

        employees = Employee.objects.filter(
            company=self.company, status='active',
        ).select_related('department', 'position')

        std_days = Decimal(str(standard_work_days))
        total_gross = Decimal('0')
        total_ins_emp = Decimal('0')
        total_ins_er = Decimal('0')
        total_pit = Decimal('0')
        total_net = Decimal('0')

        for idx, emp in enumerate(employees, start=1):
            # Prorated base salary by work days (simplified — assume full month)
            gross = emp.base_salary + emp.allowance

            # Insurance — employee portion
            si_emp = (gross * INSURANCE_RATES['social_employee']).quantize(Decimal('1'))
            hi_emp = (gross * INSURANCE_RATES['health_employee']).quantize(Decimal('1'))
            ui_emp = (gross * INSURANCE_RATES['unemployment_employee']).quantize(Decimal('1'))
            ins_emp_total = si_emp + hi_emp + ui_emp

            # Insurance — employer portion
            si_er = (gross * INSURANCE_RATES['social_employer']).quantize(Decimal('1'))
            hi_er = (gross * INSURANCE_RATES['health_employer']).quantize(Decimal('1'))
            ui_er = (gross * INSURANCE_RATES['unemployment_employer']).quantize(Decimal('1'))

            # PIT: taxable = gross - insurance_employee - personal deduction
            taxable = gross - ins_emp_total - PERSONAL_DEDUCTION
            pit = calculate_pit(taxable) if taxable > 0 else Decimal('0')

            net = gross - ins_emp_total - pit

            PayrollLine.objects.create(
                run=run, employee=emp, line_no=idx,
                work_days=std_days,
                base_salary=emp.base_salary,
                allowance_amount=emp.allowance,
                gross_salary=gross,
                social_insurance_employee=si_emp,
                health_insurance_employee=hi_emp,
                unemployment_insurance_employee=ui_emp,
                social_insurance_employer=si_er,
                health_insurance_employer=hi_er,
                unemployment_insurance_employer=ui_er,
                pit=pit,
                net_salary=net,
            )

            total_gross += gross
            total_ins_emp += ins_emp_total
            total_ins_er += (si_er + hi_er + ui_er)
            total_pit += pit
            total_net += net

        run.total_gross = total_gross
        run.total_insurance_employee = total_ins_emp
        run.total_insurance_employer = total_ins_er
        run.total_pit = total_pit
        run.total_net = total_net
        run.status = 'calculated'
        run.save()

        return run

    @transaction.atomic
    def post(self, run: PayrollRun) -> AccountingVoucher:
        """Post payroll → generate accounting voucher.

        Bút toán (simplified — all employees in one dept):
        N642 (total gross + employer insurance) — salary expense
        C334 (net payable to employees)
        C3336 (PIT payable)
        C3383 (BHXH payable — employee + employer)
        C3384 (BHYT payable)
        C3386 (BHTN payable)
        """
        if run.status == 'posted':
            return run.gl_voucher

        voucher_date = date(run.fiscal_year, run.period_num, 1)

        voucher = AccountingVoucher.objects.create(
            company=run.company,
            fiscal_year=run.fiscal_year,
            period=run.period_num,
            voucher_no=f'PAY-{run.period}',
            voucher_type='payroll',
            voucher_date=voucher_date,
            currency_code='VND',
            total_vnd=run.total_gross + run.total_insurance_employer,
            status=AccountingVoucher.Status.DRAFT,
            source='payroll',
            source_reference_id=run.id,
            description=f'Tiền lương kỳ {run.period}',
        )

        line_no = 1
        # N642 — total cost = gross + employer insurance
        VoucherLine.objects.create(
            voucher=voucher, line_no=line_no,
            account_code='642',
            debit_vnd=run.total_gross + run.total_insurance_employer,
            description=f'CP lương + BHXH DN kỳ {run.period}',
        )
        line_no += 1

        # C334 — net payable to employees
        VoucherLine.objects.create(
            voucher=voucher, line_no=line_no,
            account_code='334',
            credit_vnd=run.total_net,
            description=f'Phải trả NLĐ (net) {run.period}',
        )
        line_no += 1

        # C3336 — PIT payable
        if run.total_pit > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code='3336',
                credit_vnd=run.total_pit,
                description=f'Thuế TNCN kỳ {run.period}',
            )
            line_no += 1

        # C3383 — BHXH payable (employee + employer)
        total_bhxh = sum(
            (l.social_insurance_employee + l.social_insurance_employer)
            for l in run.lines.all()
        )
        if total_bhxh > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code='3383',
                credit_vnd=total_bhxh,
                description=f'BHXH kỳ {run.period}',
            )
            line_no += 1

        # C3384 — BHYT payable
        total_bhyt = sum(
            (l.health_insurance_employee + l.health_insurance_employer)
            for l in run.lines.all()
        )
        if total_bhyt > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code='3384',
                credit_vnd=total_bhyt,
                description=f'BHYT kỳ {run.period}',
            )
            line_no += 1

        # C3386 — BHTN payable
        total_bhtn = sum(
            (l.unemployment_insurance_employee + l.unemployment_insurance_employer)
            for l in run.lines.all()
        )
        if total_bhtn > 0:
            VoucherLine.objects.create(
                voucher=voucher, line_no=line_no,
                account_code='3386',
                credit_vnd=total_bhtn,
                description=f'BHTN kỳ {run.period}',
            )
            line_no += 1

        # Post voucher
        VoucherPostingService().post(voucher)

        run.gl_voucher = voucher
        run.status = 'posted'
        run.save()

        return voucher
```

- [ ] **Step 4: Create __init__.py**

```python
from .payroll_service import PayrollService, calculate_pit, PIT_BRACKETS

__all__ = ['PayrollService', 'calculate_pit', 'PIT_BRACKETS']
```

- [ ] **Step 5: Run tests + commit**

```bash
.venv/bin/pytest tests/test_payroll_service.py -v
.venv/bin/pytest -v
git add apps/payroll/services/ tests/test_payroll_service.py
git commit -m "feat(payroll): PayrollService with BHXH/BHYT/BHTN + PIT + auto-voucher

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Modern UI — Employee list/create + Payroll run view

**Files:**
- Create: `apps/ui_modern/views/hr_views.py`, `apps/ui_modern/views/payroll_views.py`
- Modify: `apps/ui_modern/views/__init__.py`, `apps/ui_modern/urls.py`
- Create: templates under `templates/modern/hr/` and `templates/modern/payroll/`
- Test: `tests/test_hr_views.py`

- [ ] **Step 1: Write tests**

`tests/test_hr_views.py`:
```python
import pytest
from django.test import Client
from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='alice', password='Secret123')
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_employee_list_loads(auth_client):
    response = auth_client.get('/modern/employees/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_employee_create_form_loads(auth_client):
    response = auth_client.get('/modern/employees/new/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_payroll_run_form_loads(auth_client):
    response = auth_client.get('/modern/payroll/run/')
    assert response.status_code == 200
```

- [ ] **Step 2: Create views**

`apps/ui_modern/views/hr_views.py`:
```python
"""Employee views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from apps.hr.models import Employee, Department, Position
from apps.core.models import Company


class EmployeeListView(LoginRequiredMixin, ListView):
    template_name = 'modern/hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 25
    login_url = '/auth/login/'

    def get_queryset(self):
        return Employee.objects.select_related(
            'department', 'position',
        ).order_by('code')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Nhân viên'
        return ctx


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    template_name = 'modern/hr/employee_form.html'
    fields = ['code', 'full_name', 'birth_date', 'gender', 'id_card_no',
              'personal_tax_code', 'social_insurance_no', 'phone', 'email',
              'address', 'department', 'position', 'hire_date',
              'base_salary', 'allowance', 'bank_account_no', 'bank_id',
              'status', 'notes']
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Thêm nhân viên'
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('ui_modern:employee_list')
```

`apps/ui_modern/views/payroll_views.py`:
```python
"""Payroll views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from apps.payroll.models import PayrollRun
from apps.payroll.services import PayrollService
from apps.core.models import Company


class PayrollRunView(LoginRequiredMixin, TemplateView):
    template_name = 'modern/payroll/run.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tính lương định kỳ'
        from datetime import date
        today = date.today()
        ctx['default_year'] = today.year
        ctx['default_month'] = today.month
        ctx['runs'] = PayrollRun.objects.order_by('-period')[:10]
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, 'No company')
            return redirect('ui_modern:payroll_run')

        year = int(request.POST.get('fiscal_year'))
        month = int(request.POST.get('period'))
        period = f'{year:04d}-{month:02d}'

        action = request.POST.get('action', 'calculate')
        service = PayrollService(company=company)

        if action == 'calculate':
            run = service.calculate(period=period, standard_work_days=22)
            messages.success(
                request,
                f'Đã tính lương {period}: {run.lines.count()} NV, '
                f'gross={run.total_gross:,.0f} net={run.total_net:,.0f}'
            )
        elif action == 'post':
            run = service.calculate(period=period, standard_work_days=22)
            service.post(run)
            messages.success(request, f'Đã ghi sổ lương {period}')

        return redirect('ui_modern:payroll_run')
```

- [ ] **Step 3: Update views/__init__.py + urls.py**

Add exports and routes:
- `/employees/` → `employee_list`
- `/employees/new/` → `employee_create`
- `/payroll/run/` → `payroll_run`

- [ ] **Step 4: Create templates** under `templates/modern/hr/` and `templates/modern/payroll/`

- [ ] **Step 5: Run tests + commit**

---

## Task 5: Update sidebar + seed sample employees + final verify

- [ ] **Step 1: Update sidebar**

Add "Nhân sự" section with:
- Nhân viên → `employee_list`
- Tính lương → `payroll_run`

- [ ] **Step 2: Update seed_demo**

Create sample Department + Position + 2 Employees (one 15M, one 20M base salary).

- [ ] **Step 3: Re-seed + verify routes + tests + lint + commit + tag `v0.5.0-phase4`**

---

## Phase 4 Acceptance Criteria

- [ ] All tests pass (target: 175+ tests)
- [ ] Employee CRUD works
- [ ] Payroll calculation: gross → BHXH deductions → PIT → net
- [ ] PIT progressive calculation correct
- [ ] Payroll posting generates voucher N642/C334/C3336/C3383/C3384/C3386
- [ ] Idempotent payroll calculation
- [ ] Sidebar links work

---

**Plan complete.** 5 tasks. Estimated effort: ~3-4 days.
