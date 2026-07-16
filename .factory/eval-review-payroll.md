# Payroll & HR Review — Compliance, Correctness, and Edge Cases

> **Review date**: 2026-07-16
> **Scope**: `apps/payroll/` (models, services), `apps/hr/` (models, services), PIT calculation, BHXH rates, Dependent model.
> **Context**: Reviewed against NQ 110/2025/UBTVQH15, ND 161/2026, ND 253/2026, TT 87/2026, Luật 09/2026/QH16.
> **Status**: Major July-2026 compliance fixes already applied (PIT deductions 15.5M/6.2M, 5-bracket system, BHXH cap 50.6M, non-taxable allowances). Remaining issues are correctness bugs, missing edge-case handling, and dead code.

---

## Summary

| Severity | Count |
|----------|-------|
| **Critical** | 3 |
| **High** | 6 |
| **Medium** | 7 |
| **Low** | 5 |
| **Info** | 4 |
| **Total** | 25 |

**Overall assessment**: The core PIT and BHXH rate values are current and correct per July 2026 regulations. However, there are several correctness bugs in amount calculation (total_employer missing KPCĐ, non-taxable allowances not paid to employees), missing work-day proration logic, unhandled edge cases (mid-month join/leave, expired dependents), and insurance rates that remain hardcoded instead of config-driven.

---

## 1. PIT Calculation Correctness

### Finding 1.1 — Non-taxable allowances reduce PIT but are never paid to employee (CRITICAL)

**Severity**: Critical
**File**: `apps/payroll/services/payroll_service.py:113-125`
**Description**: The meal and pension allowances (`emp.meal_allowance`, `emp.pension_allowance`) are used to reduce taxable income:

```python
gross = emp.base_salary + emp.allowance  # meal/pension NOT in gross
meal_exclude = min(emp.meal_allowance, meal_cap)
pension_exclude = min(emp.pension_allowance, pension_cap)
non_taxable_allowances = meal_exclude + pension_exclude
taxable = gross - ins_emp_total - total_deduction - non_taxable_allowances
```

The problem: `gross` does **not** include `meal_allowance` or `pension_allowance`. The taxable income is reduced by amounts that were never added to gross in the first place. This means:
1. PIT is artificially reduced (the exclusion is applied to income that doesn't exist in the gross figure).
2. The employee never receives the meal/pension allowance in their net pay (`net = gross - ins_emp_total - pit`).

The correct approach is either: (a) include meal/pension in gross, then exclude from taxable, or (b) document that `emp.allowance` already includes meal/pension as a lump sum.

**Fix**: Include non-taxable allowances in gross salary:
```python
gross = emp.base_salary + emp.allowance + emp.meal_allowance + emp.pension_allowance
# Then exclude non-taxable portion from taxable income
taxable = gross - ins_emp_total - total_deduction - non_taxable_allowances
```

---

### Finding 1.2 — Dependent active filter ignores valid_to expiry (HIGH)

**Severity**: High
**File**: `apps/payroll/services/payroll_service.py:127-130`
**Description**: The dependent queryset filter checks `registration_status="registered"` and `valid_from__lte=date.today()` but does **not** check `valid_to`:

```python
active_dependents = emp.dependents.filter(
    registration_status="registered",
    valid_from__lte=date.today(),
).count()
```

A dependent whose `valid_to` has passed (e.g., child turned 18, or dependent deregistered) will still be counted, overstating deductions and understating PIT. The `Dependent.is_active` property correctly checks `valid_to`, but it is not used.

**Fix**: Add `valid_to` filter:
```python
active_dependents = emp.dependents.filter(
    registration_status="registered",
    valid_from__lte=date.today(),
).filter(
    models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=date.today())
).count()
```

---

### Finding 1.3 — PIT brackets use hardcoded sentinel 999,999,999 as top cap (LOW)

**Severity**: Low
**File**: `apps/payroll/services/payroll_service.py:34`
**Description**: The top PIT bracket uses `Decimal("999999999")` (~1B VND) as the cap. If taxable income exceeds this amount (extremely rare but possible for C-level executives with stock compensation), the amount above 999,999,999 VND goes untaxed because the loop simply ends with `remaining > 0` unconsumed.

**Fix**: Use `Decimal("Infinity")` for the top bracket or add a guard after the loop:
```python
if remaining > 0:
    pit += remaining * rate  # apply top rate to remainder
```

---

### Finding 1.4 — Medical and education deductions not applied (MEDIUM)

**Severity**: Medium
**File**: `apps/payroll/services/payroll_service.py` (entire file)
**Description**: `TaxRateConfig` has `pit_medical_deduction` (23M/year) and `pit_education_deduction` (24M/year) fields per ND 253/2026, but `PayrollService` never reads or applies them. These are annual deductions for catastrophic medical expenses and children's tuition that reduce taxable income.

**Fix**: Add annual medical/education deduction tracking. Since these are annual (not monthly), a year-to-date accumulation is needed. At minimum, document that these are not implemented and require manual year-end finalization.

---

### Finding 1.5 — PIT rounding uses ROUND_HALF_EVEN instead of ROUND_HALF_UP (LOW)

**Severity**: Low
**File**: `apps/payroll/services/payroll_service.py:58`, `apps/hr/services/insurance_service.py:23`
**Description**: `quantize(Decimal("1"))` defaults to `ROUND_HALF_EVEN` (banker's rounding). Vietnamese tax practice and BHXH declarations typically use `ROUND_HALF_UP`. This can cause off-by-1 VND discrepancies on amounts ending in exactly 0.5 VND. In practice, salaries are usually whole numbers so this rarely triggers, but it is technically non-compliant.

**Fix**:
```python
from decimal import ROUND_HALF_UP
return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
```

---

## 2. BHXH Rate Correctness

### Finding 2.1 — InsuranceService.total_employer excludes KPCĐ 2% (CRITICAL)

**Severity**: Critical
**File**: `apps/hr/services/insurance_service.py:66`
**Description**: The `total_employer` calculation omits `kpcd_er` (Kinh phí công đoàn 2%):

```python
total_er = bhxh_er + bhyt_er + bhtn_er + bhtnld_er  # kpcd_er MISSING
```

The KPCĐ (2%) is calculated and stored in `kpcd_employer` field separately, but `total_employer` underreports the true employer cost by 2%. Any downstream report or calculation relying on `total_employer` will be wrong.

The comment on line 14 also says "Employer portion — 21.5% total" but the actual employer total including KPCĐ is 23.5% (17 + 3 + 1 + 0.5 + 2).

**Fix**:
```python
total_er = bhxh_er + bhyt_er + bhtn_er + bhtnld_er + kpcd_er
```

---

### Finding 2.2 — Insurance rates hardcoded in RATES dict, not config-driven (HIGH)

**Severity**: High
**File**: `apps/hr/services/insurance_service.py:6-18`
**Description**: The BHXH/BHYT/BHTN/BHTNLĐ/KPCĐ rate percentages are hardcoded in the `RATES` dict. Only the cap and base salary are read from `TaxRateConfig`. If the government adjusts rates (e.g., BHXH employer changes from 17% to 18%, or BHTN is reduced), a code change + deployment is required instead of a database update.

The `TaxRateConfig` model does not have fields for individual insurance rate percentages.

**Fix**: Add rate fields to `TaxRateConfig` (e.g., `bhxh_rate_employer`, `bhyt_rate_employee`, etc.) with current values as defaults. Read from config in `InsuranceService.__init__` with fallback to the hardcoded dict.

---

### Finding 2.3 — InsuranceService uses employee.base_salary, ignores LaborContract.insurance_salary_base (HIGH)

**Severity**: High
**File**: `apps/hr/services/insurance_service.py:49`
**Description**: The insurance base is taken from `employee.base_salary`, but `LaborContract` has a dedicated `insurance_salary_base` field that represents the agreed BHXH contribution salary. In Vietnamese practice, the insurance salary base may differ from the base salary (e.g., it may include or exclude certain allowances per the contract).

```python
raw = employee.base_salary or Decimal("0")  # ignores contract.insurance_salary_base
```

Additionally, `LaborContract.join_insurance` flag is never checked. An employee whose contract specifies `join_insurance=False` (e.g., contractor) will still have insurance calculated.

**Fix**: Look up the active labor contract for the employee and use `contract.insurance_salary_base` (falling back to `employee.base_salary`). Skip insurance if `join_insurance=False`:
```python
contract = employee.labor_contracts.filter(status="active").order_by("-start_date").first()
if contract and not contract.join_insurance:
    raw = Decimal("0")
elif contract and contract.insurance_salary_base > 0:
    raw = contract.insurance_salary_base
else:
    raw = employee.base_salary or Decimal("0")
```

---

### Finding 2.4 — No insurance base floor (minimum wage) (MEDIUM)

**Severity**: Medium
**File**: `apps/hr/services/insurance_service.py:49-50`
**Description**: There is a cap (`min(raw, cap)`) but no floor. Vietnamese regulation requires that the insurance contribution base cannot be below the regional minimum wage. If an employee's base salary is below 2,530,000 VND/month (Region I minimum for 2026), the insurance should be calculated on the minimum, not the actual lower salary.

**Fix**:
```python
config = TaxConfigService.get_active(self.company)
floor = config.bhxh_base_salary if config else _DEFAULT_BASE
capped = max(min(raw, cap), floor)
```

---

### Finding 2.5 — Dead INSURANCE_RATES dict with wrong rates (MEDIUM)

**Severity**: Medium
**File**: `apps/payroll/services/payroll_service.py:15-23`
**Description**: The `INSURANCE_RATES` dict in `payroll_service.py` is dead code (never referenced). It also contains a misleading rate: `"social_employer": Decimal("0.175")` (17.5%), which conflates BHXH (17%) with BHTNLĐ-BNN (0.5%). The `InsuranceService` correctly separates these, but the dead dict could confuse a developer reading the file.

**Fix**: Remove the `INSURANCE_RATES` dict entirely. The canonical rates live in `InsuranceService.RATES`.

---

### Finding 2.6 — Employer portion comment says 21.5% but actual is 23.5% (LOW)

**Severity**: Low
**File**: `apps/hr/services/insurance_service.py:12`
**Description**: Comment reads `# Employer portion — 21.5% total` but the actual total is 23.5% (17 + 3 + 1 + 0.5 + 2 = 23.5%). The 21.5% appears to exclude KPCĐ (2%).

**Fix**: Update comment to `# Employer portion — 23.5% total (incl. KPCĐ 2%)`.

---

## 3. Decimal Handling

### Finding 3.1 — No float usage in payroll/HR modules (POSITIVE)

**Severity**: Info (positive finding)
**File**: all payroll and HR files
**Description**: All monetary amounts use `Decimal` fields and arithmetic. No `float` or implicit float conversion found in `apps/payroll/` or `apps/hr/`. The only `float()` calls in the codebase are in UI/template layer (`apps/ui_modern/`) and unrelated modules (e.g., FX, einvoice). This is correct and well done.

---

### Finding 3.2 — Decimal default=0 on model fields could mask None (LOW)

**Severity**: Low
**File**: `apps/payroll/models.py` (multiple fields), `apps/hr/models/insurance.py` (multiple fields)
**Description**: All monetary fields use `default=0` (integer 0, not `Decimal("0")`). While Django converts this correctly, it is inconsistent with the Decimal field type. Using `Decimal("0")` would be more explicit and consistent with how values are compared in the service layer.

**Fix**: No functional impact. For code consistency, use `default=Decimal("0")` in model definitions.

---

## 4. Allowance Handling

### Finding 4.1 — Meal and pension allowances excluded from taxable income (CORRECT intent, see 1.1)

**Severity**: Info
**File**: `apps/payroll/services/payroll_service.py:120-124`
**Description**: The exclusion logic (`min(emp.meal_allowance, meal_cap)`) is correctly capped at the ND 253/2026 limits (meal 1.2M, pension 3M). The cap application is correct. However, the underlying issue is that these allowances are not included in gross (see Finding 1.1).

---

### Finding 4.2 — Generic allowance (emp.allowance) is fully taxable with no category breakdown (MEDIUM)

**Severity**: Medium
**File**: `apps/payroll/services/payroll_service.py:98`, `apps/hr/models/employee.py:84-85`
**Description**: `emp.allowance` is added directly to gross and is fully taxable. There is no mechanism to categorize which portion of the allowance is taxable vs non-taxable beyond the separate meal/pension fields. In practice, Vietnamese employees may have various allowance types (housing, transportation, phone, etc.) with different tax treatments. Some are fully taxable, some partially exempt.

**Fix**: Consider adding an `AllowanceType` model or JSON field that categorizes allowances by tax treatment. For now, document that `emp.allowance` is treated as fully taxable.

---

## 5. Edge Cases

### Finding 5.1 — No work-day proration; AttendanceRecord unused (CRITICAL)

**Severity**: Critical
**File**: `apps/payroll/services/payroll_service.py:88-112`
**Description**: The `calculate` method accepts `standard_work_days=22` and sets `work_days=std_days` on every PayrollLine, but:
1. It never queries `AttendanceRecord` to get actual work days per employee.
2. Gross is always `emp.base_salary + emp.allowance` (full month), regardless of actual work days.
3. The `overtime_hours` field on PayrollLine is always 0 (overtime is never calculated).
4. The `std_days` parameter is computed as `Decimal(str(standard_work_days))` but never used for proration.

This means an employee who was absent for 10 days still gets a full month's salary. An employee with 50 hours of overtime gets no overtime pay.

**Fix**: Query `AttendanceRecord` for each employee in the period, compute actual work days, prorate base salary:
```python
actual_days = AttendanceRecord.objects.filter(
    employee=emp,
    attendance_date__month=period_num,
    attendance_date__year=fiscal_year,
).aggregate(total=Sum("work_days"))["total"] or std_days
gross = (emp.base_salary + emp.allowance) * (actual_days / std_days)
```

---

### Finding 5.2 — No mid-month join/leave handling (HIGH)

**Severity**: High
**File**: `apps/payroll/services/payroll_service.py:86-91`
**Description**: The employee queryset filters only by `status="active"`. It does not check:
- `hire_date <= period_end` — an employee hired mid-period gets a full month's salary.
- `leave_date >= period_start` — an employee who resigned mid-period (but whose status is still "active" because the leave_date was set but status wasn't changed) gets a full month's salary.
- `is_active` boolean — the `is_active` field on Employee is not checked at all.

**Fix**:
```python
period_end = date(fiscal_year, period_num, calendar.monthrange(fiscal_year, period_num)[1])
employees = Employee.objects.filter(
    company=self.company,
    status="active",
    is_active=True,
    hire_date__lte=period_end,
).filter(
    models.Q(leave_date__isnull=True) | models.Q(leave_date__gte=date(fiscal_year, period_num, 1))
)
```

---

### Finding 5.3 — No negative adjustment or bonus handling (MEDIUM)

**Severity**: Medium
**File**: `apps/payroll/models.py` (PayrollLine), `apps/payroll/services/payroll_service.py`
**Description**: There is no mechanism for salary adjustments (bonuses, deductions, penalties, retroactive corrections). The `PayrollLine` model has no fields for adjustments. The `gross_salary` is always `base_salary + allowance` with no room for one-time payments or deductions.

Vietnamese payroll commonly includes: thuong (bonus), phat (penalty), tam ung (salary advance), cong them (overtime pay), khau tru khac (other deductions). None of these are modeled.

**Fix**: Add adjustment fields to `PayrollLine` (e.g., `bonus_amount`, `deduction_amount`, `advance_deduction`) or create a `PayrollAdjustment` model linked to `PayrollLine`.

---

### Finding 5.4 — No retroactive payroll recalculation support (MEDIUM)

**Severity**: Medium
**File**: `apps/payroll/services/payroll_service.py:70-73`
**Description**: If an employee's salary or dependent status changes retroactively (e.g., salary increase effective from last month), there is no mechanism to recalculate and post the difference. The payroll can only be recalculated if status is "draft" or "calculated" — posted/paid runs are protected (which is correct), but there's no supplementary run or adjustment voucher capability.

**Fix**: Add a supplementary payroll run type or adjustment voucher for retroactive changes.

---

## 6. Double-Count Prevention

### Finding 6.1 — Payroll idempotency works correctly (POSITIVE)

**Severity**: Info (positive finding)
**File**: `apps/payroll/services/payroll_service.py:67-73`
**Description**: The `calculate` method is idempotent:
- Uses `get_or_create` for the PayrollRun.
- Deletes existing lines before recalculating (`run.lines.all().delete()`).
- Returns early if status is "posted" or "paid".
- `InsuranceContribution` uses `update_or_create`.

Calling `calculate` twice for the same period does not duplicate data. This is correct.

---

### Finding 6.2 — PayrollView uses Company.objects.first() instead of tenant scoping (MEDIUM)

**Severity**: Medium
**File**: `apps/ui_modern/views/payroll_views.py:49`
**Description**: The payroll UI view hardcodes `Company.objects.first()` instead of using the authenticated user's active company. In a multi-tenant setup, this means any user can trigger payroll for an arbitrary company. While the service layer accepts a company parameter, the view layer has no tenant isolation.

**Fix**: Use the request user's active company:
```python
company = request.user.company  # or however the tenant context is resolved
```

---

## 7. Hardcoded Constants

### Finding 7.1 — Insurance rate percentages hardcoded (see Finding 2.2)

**Severity**: High (see 2.2 for details)

---

### Finding 7.2 — PIT fallback constants are current but fragile (LOW)

**Severity**: Low
**File**: `apps/payroll/services/payroll_service.py:36-37`
**Description**: The fallback constants `PERSONAL_DEDUCTION = Decimal("15500000")` and `DEPENDENT_DEDUCTION = Decimal("62000000")` are current per NQ 110/2025. However, they duplicate values that also live in `TaxRateConfig` defaults and `seed_demo.py`. When the next PIT change occurs (e.g., 2027 adjustment), all three locations must be updated in sync.

**Fix**: Acceptable as fallback-of-last-resort. Add a comment noting these are emergency fallbacks only and the canonical source is `TaxRateConfig`.

---

### Finding 7.3 — pit_dependent_income_threshold and pit_withholding_threshold unused (MEDIUM)

**Severity**: Medium
**File**: `apps/core/models.py` (field definitions), `apps/payroll/services/payroll_service.py` (not referenced)
**Description**: `TaxRateConfig.pit_dependent_income_threshold` (3M/month) and `pit_withholding_threshold` (5M/payment) are stored but never used:
- `pit_dependent_income_threshold`: A dependent earning more than this amount is no longer eligible for family deduction. The payroll does not check dependent income.
- `pit_withholding_threshold`: The threshold for 10% withholding tax on casual/one-time payments. Not relevant for regular payroll but needed for contractor/occasional payments.

**Fix**: Add dependent income validation before applying dependent deduction. For withholding threshold, add to a separate service for non-payroll payments.

---

## 8. Test Coverage

### Finding 8.1 — No tests for work-day proration or AttendanceRecord integration (HIGH)

**Severity**: High
**File**: `tests/test_payroll_service.py`, `tests/test_payroll_v2.py`
**Description**: Existing tests always use `standard_work_days=22` and assume all employees work a full month. There are no tests for:
- Partial month work (e.g., 15 out of 22 days)
- Overtime calculation
- AttendanceRecord → PayrollLine integration
- Employee on unpaid leave for part of the month

Since the proration logic doesn't exist in the service, this is both a missing-feature and missing-test issue.

**Fix**: After implementing work-day proration (Finding 5.1), add tests for partial-month scenarios.

---

### Finding 8.2 — No tests for mid-month join/leave (MEDIUM)

**Severity**: Medium
**File**: `tests/`
**Description**: No tests verify that an employee who joins mid-month or leaves mid-month gets prorated salary. No tests verify the employee filter excludes inactive or out-of-period employees.

---

### Finding 8.3 — No tests for PIT bracket boundary values (MEDIUM)

**Severity**: Medium
**File**: `tests/test_pit_2026_july_fix.py`
**Description**: The existing PIT tests verify the fallback calculation for 10M and 42M taxable income, but do not test bracket boundaries:
- Exactly 5,000,000 VND (boundary between bracket 1 and 2)
- Exactly 10,000,000 VND (boundary between bracket 2 and 3)
- Exactly 18,000,000 VND (boundary between bracket 3 and 4)
- Exactly 32,000,000 VND (boundary between bracket 4 and 5)
- 1 VND above/below each boundary
- Zero taxable income
- Very high income (> 999,999,999)

**Fix**: Add parametrized tests for each bracket boundary.

---

### Finding 8.4 — No test for total_employer calculation (CRITICAL — ties to Finding 2.1)

**Severity**: Critical
**File**: `tests/test_insurance_leave.py`
**Description**: The test `test_insurance_calculation` checks individual components (bhxh_employer, bhyt_employer, etc.) but does not assert on `total_employer`. This is why the missing KPCĐ in `total_employer` (Finding 2.1) was not caught.

**Fix**: After fixing the bug, add assertion:
```python
assert ic.total_employer == Decimal("3525000")  # 15M * 23.5%
```

---

### Finding 8.5 — Existing tests for 2026 rates are thorough (POSITIVE)

**Severity**: Info (positive finding)
**File**: `tests/test_pit_2026_july_fix.py`, `tests/test_bhxh_rates.py`, `tests/test_pit_allowances.py`
**Description**: The test suite comprehensively verifies:
- PIT personal deduction (15.5M), dependent deduction (6.2M), 5-bracket system
- BHXH cap (50.6M), base salary (2.53M)
- Non-taxable allowance caps (meal 1.2M, pension 3M)
- Fallback constants in PayrollService
- PITRateHistory seed correctness
- Config-driven rate reading (not hardcoded constants)

This is well done. The rate values are properly tested for compliance with July 2026 regulations.

---

### Finding 8.6 — test_labor_contract.py uses old deduction_amount 4,400,000 (LOW)

**Severity**: Low
**File**: `tests/test_labor_contract.py:55, 62`
**Description**: The test explicitly sets `deduction_amount=Decimal('4400000')` (old TT 111/2013 value). While this doesn't break anything (the model default is 6,200,000), the test data is outdated and could confuse. It does not test the updated default.

**Fix**: Update test to use `Decimal('6200000')` or remove the explicit value to test the default.

---

## Detailed Line-Reference Index

| # | Finding | Severity | File | Lines |
|---|---------|----------|------|-------|
| 1.1 | Non-taxable allowances not in gross | Critical | `apps/payroll/services/payroll_service.py` | 98, 113-125 |
| 1.2 | Dependent filter ignores valid_to | High | `apps/payroll/services/payroll_service.py` | 127-130 |
| 1.3 | Top PIT bracket sentinel 999M | Low | `apps/payroll/services/payroll_service.py` | 34 |
| 1.4 | Medical/education deductions not applied | Medium | `apps/payroll/services/payroll_service.py` | (missing) |
| 1.5 | ROUND_HALF_EVEN vs ROUND_HALF_UP | Low | `apps/payroll/services/payroll_service.py:58`, `apps/hr/services/insurance_service.py:23` |
| 2.1 | total_employer missing KPCĐ | Critical | `apps/hr/services/insurance_service.py` | 66 |
| 2.2 | Insurance rates hardcoded | High | `apps/hr/services/insurance_service.py` | 6-18 |
| 2.3 | insurance_salary_base unused | High | `apps/hr/services/insurance_service.py` | 49 |
| 2.4 | No insurance floor (min wage) | Medium | `apps/hr/services/insurance_service.py` | 49-50 |
| 2.5 | Dead INSURANCE_RATES dict | Medium | `apps/payroll/services/payroll_service.py` | 15-23 |
| 2.6 | Employer total comment wrong (21.5 vs 23.5) | Low | `apps/hr/services/insurance_service.py` | 12 |
| 3.1 | No float usage (positive) | Info | `apps/payroll/`, `apps/hr/` | all |
| 3.2 | default=0 vs default=Decimal("0") | Low | `apps/payroll/models.py`, `apps/hr/models/insurance.py` | multiple |
| 4.1 | Allowance exclusion logic correct (positive, see 1.1) | Info | `apps/payroll/services/payroll_service.py` | 120-124 |
| 4.2 | Generic allowance fully taxable, no categories | Medium | `apps/hr/models/employee.py:84-85`, `apps/payroll/services/payroll_service.py:98` |
| 5.1 | No work-day proration, AttendanceRecord unused | Critical | `apps/payroll/services/payroll_service.py` | 88-112 |
| 5.2 | No mid-month join/leave filter | High | `apps/payroll/services/payroll_service.py` | 86-91 |
| 5.3 | No adjustment/bonus/penalty fields | Medium | `apps/payroll/models.py` (PayrollLine) |
| 5.4 | No retroactive recalculation | Medium | `apps/payroll/services/payroll_service.py` | 70-73 |
| 6.1 | Idempotency correct (positive) | Info | `apps/payroll/services/payroll_service.py` | 67-73 |
| 6.2 | PayrollView uses Company.objects.first() | Medium | `apps/ui_modern/views/payroll_views.py` | 49 |
| 7.1 | (see 2.2) | High | — |
| 7.2 | PIT fallback constants duplicated | Low | `apps/payroll/services/payroll_service.py` | 36-37 |
| 7.3 | dependent_income_threshold, withholding_threshold unused | Medium | `apps/core/models.py`, `apps/payroll/services/payroll_service.py` |
| 8.1 | No proration tests | High | `tests/test_payroll_service.py` |
| 8.2 | No mid-month tests | Medium | `tests/` |
| 8.3 | No bracket boundary tests | Medium | `tests/test_pit_2026_july_fix.py` |
| 8.4 | No total_employer test | Critical | `tests/test_insurance_leave.py` |
| 8.5 | 2026 rate tests thorough (positive) | Info | `tests/test_pit_2026_july_fix.py`, `tests/test_bhxh_rates.py` |
| 8.6 | Old deduction_amount in test | Low | `tests/test_labor_contract.py` | 55, 62 |

---

## Regulatory Compliance Checklist

| Regulation | Status | Notes |
|-----------|--------|-------|
| NQ 110/2025 — PIT personal deduction 15.5M | ✅ Applied | Config + fallback both correct |
| NQ 110/2025 — PIT dependent deduction 6.2M | ✅ Applied | Config + fallback both correct |
| NQ 110/2025 — 5-bracket PIT system | ✅ Applied | Brackets correct, boundary edge case (Finding 1.3) |
| ND 161/2026 — BHXH cap 50.6M | ✅ Applied | Read from TaxRateConfig with fallback |
| ND 161/2026 — BHXH base salary 2.53M | ✅ Applied | Stored in config, used for cap derivation |
| ND 253/2026 — Meal allowance non-taxable 1.2M | ⚠️ Partial | Exclusion logic correct but not included in gross (Finding 1.1) |
| ND 253/2026 — Pension allowance non-taxable 3M | ⚠️ Partial | Same as above |
| ND 253/2026 — Medical deduction 23M/year | ❌ Not implemented | Field exists but not applied (Finding 1.4) |
| ND 253/2026 — Education deduction 24M/year | ❌ Not implemented | Field exists but not applied (Finding 1.4) |
| ND 253/2026 — Dependent income threshold 3M | ❌ Not implemented | Field exists but not checked (Finding 7.3) |
| BHXH rates (employer/employee) | ✅ Correct values | Hardcoded instead of config-driven (Finding 2.2) |
| KPCĐ 2% employer | ⚠️ Bug | Calculated but not in total_employer (Finding 2.1) |
| BHTNLĐ-BNN 0.5% employer | ✅ Applied | Correctly separated |
| Insurance base from labor contract | ❌ Not implemented | Uses employee.base_salary (Finding 2.3) |
| Insurance floor (min wage) | ❌ Not implemented | No minimum base enforcement (Finding 2.4) |

---

*Review complete. 25 findings: 3 Critical, 6 High, 7 Medium, 5 Low, 4 Info.*
