"""PayrollService — calculate salary + BHXH + PIT + post voucher."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.core.services.tax_config_service import TaxConfigService
from apps.hr.models import Employee
from apps.hr.services import InsuranceService
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.payroll.models import PayrollLine, PayrollRun

# 2024-2026 Vietnamese insurance rates (legacy inline rates — kept for reference;
# calculations now delegate to InsuranceService for cap + correct rate table).
INSURANCE_RATES = {
    "social_employee": Decimal("0.08"),  # BHXH NV đóng 8%
    "social_employer": Decimal("0.175"),  # BHXH DN đóng 17.5%
    "health_employee": Decimal("0.015"),  # BHYT NV 1.5%
    "health_employer": Decimal("0.03"),  # BHYT DN 3%
    "unemployment_employee": Decimal("0.01"),  # BHTN NV 1%
    "unemployment_employer": Decimal("0.01"),  # BHTN DN 1%
}

# PIT brackets (monthly taxable income, VND) — 5-bracket system per NQ 110/2025/UBTVQH15
# (effective 01/07/2026) + Luật 09/2026/QH16.
PIT_BRACKETS = [
    (Decimal("5000000"), Decimal("0.05")),  # ≤ 5M: 5%
    (Decimal("10000000"), Decimal("0.10")),  # 5M–10M: 10%
    (Decimal("18000000"), Decimal("0.20")),  # 10M–18M: 20%
    (Decimal("32000000"), Decimal("0.30")),  # 18M–32M: 30%
    (Decimal("999999999"), Decimal("0.35")),  # > 32M: 35%
]

PERSONAL_DEDUCTION = Decimal("15500000")  # Giảm trừ gia cảnh bản thân (NQ 110/2025)
DEPENDENT_DEDUCTION = Decimal("6200000")  # Mỗi người phụ thuộc (NQ 110/2025)


def calculate_pit(taxable_income: Decimal, brackets=None) -> Decimal:
    """Progressive PIT calculation based on brackets.

    ``brackets`` is an optional iterable of ``(cap, rate)`` pairs; if omitted,
    the hardcoded ``PIT_BRACKETS`` (per NQ 110/2025) are used as fallback.
    """
    if taxable_income <= 0:
        return Decimal("0")
    pit = Decimal("0")
    remaining = taxable_income
    prev_cap = Decimal("0")
    for cap, rate in brackets if brackets is not None else PIT_BRACKETS:
        cap = Decimal(str(cap))
        rate = Decimal(str(rate))
        if remaining <= 0:
            break
        slab = min(remaining, cap - prev_cap)
        pit += slab * rate
        remaining -= slab
        prev_cap = cap
    return pit.quantize(Decimal("1"))  # round to VND


class PayrollService:
    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def calculate(self, period: str, standard_work_days: int = 22) -> PayrollRun:
        """Calculate payroll for all active employees in given period (YYYY-MM).

        Idempotent: returns existing PayrollRun if already calculated.
        """
        fiscal_year = int(period.split("-")[0])
        period_num = int(period.split("-")[1])

        run, _created = PayrollRun.objects.get_or_create(
            company=self.company,
            period=period,
            defaults={
                "fiscal_year": fiscal_year,
                "period_num": period_num,
                "status": "draft",
            },
        )

        if run.status in ("posted", "paid"):
            return run  # don't recalculate posted payroll

        # Clear existing lines (in case of recalculation)
        run.lines.all().delete()

        employees = Employee.objects.filter(
            company=self.company,
            status="active",
        ).select_related("department", "position")

        std_days = Decimal(str(standard_work_days))
        total_gross = Decimal("0")
        total_ins_emp = Decimal("0")
        total_ins_er = Decimal("0")
        total_pit = Decimal("0")
        total_net = Decimal("0")
        total_kpcd = Decimal("0")
        total_bhtnld = Decimal("0")

        ins_svc = InsuranceService(company=self.company)

        # Read PIT deductions + brackets from TaxRateConfig (NQ 110/2025 ready);
        # fall back to hardcoded NQ 110/2025 values if no active config.
        # Prefer the _2026 fields (current rates per NQ 110/2025 effective 01/07/2026);
        # fall back to the base fields for configs that haven't been updated.
        config = TaxConfigService.get_active(self.company)
        if config is not None:
            personal_deduction = config.pit_personal_deduction_2026 or config.pit_personal_deduction
            dependent_deduction = (
                config.pit_dependent_deduction_2026 or config.pit_dependent_deduction
            )
            pit_brackets = config.pit_brackets_2026 or config.pit_brackets or None
            # Non-taxable allowance caps (ND 253/2026 + TT 87/2026)
            meal_cap = config.pit_meal_allowance
            pension_cap = config.pit_pension_allowance
        else:
            personal_deduction = PERSONAL_DEDUCTION
            dependent_deduction = DEPENDENT_DEDUCTION
            pit_brackets = None
            # Fallback caps per ND 253/2026 + TT 87/2026
            meal_cap = Decimal("1200000")
            pension_cap = Decimal("3000000")

        for idx, emp in enumerate(employees, start=1):
            # Prorated base salary by work days (simplified — assume full month)
            gross = emp.base_salary + emp.allowance

            # Delegate to InsuranceService — handles 46.8M cap + correct 2025 rates.
            # Insurance base is base_salary only (allowance treated as non-insurance pay
            # in line with VN practice for capped allowances); capped inside service.
            ic = ins_svc.calculate_monthly(emp, period)

            # Employee portion (BHXH/BHYT/BHTN) from InsuranceContribution
            si_emp = ic.bhxh_employee
            hi_emp = ic.bhyt_employee
            ui_emp = ic.bhtn_employee
            ins_emp_total = ic.total_employee

            # Employer portion — BHXH/BHYT/BHTN + extra KPCĐ/BHTNLĐ-BNN
            si_er = ic.bhxh_employer
            hi_er = ic.bhyt_employer
            ui_er = ic.bhtn_employer
            kpcd_er = ic.kpcd_employer
            bhtnld_er = ic.bhtnld_employer

            # PIT: taxable = gross - insurance_employee - personal deduction
            #      - dependent deduction (6.2M per active dependent)
            #      - non-taxable allowances (meal up to cap, pension up to cap)
            #      per ND 253/2026 + TT 87/2026
            active_dependents = emp.dependents.filter(
                registration_status="registered",
                valid_from__lte=date.today(),
            ).count()
            # Simplified active filter: registered + valid_from <= today
            # (Dependent.is_active property is the canonical check, but it's
            #  per-instance — using queryset for efficiency.)
            total_deduction = personal_deduction + (
                dependent_deduction * Decimal(active_dependents)
            )
            # Exclude non-taxable portion of meal + pension allowances
            meal_exclude = min(emp.meal_allowance, meal_cap)
            pension_exclude = min(emp.pension_allowance, pension_cap)
            non_taxable_allowances = meal_exclude + pension_exclude
            taxable = gross - ins_emp_total - total_deduction - non_taxable_allowances
            pit = calculate_pit(taxable, brackets=pit_brackets) if taxable > 0 else Decimal("0")

            net = gross - ins_emp_total - pit

            PayrollLine.objects.create(
                run=run,
                employee=emp,
                line_no=idx,
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
                kpcd_employer=kpcd_er,
                bhtnld_employer=bhtnld_er,
                pit=pit,
                net_salary=net,
            )

            total_gross += gross
            total_ins_emp += ins_emp_total
            total_ins_er += si_er + hi_er + ui_er
            total_kpcd += kpcd_er
            total_bhtnld += bhtnld_er
            total_pit += pit
            total_net += net

        run.total_gross = total_gross
        run.total_insurance_employee = total_ins_emp
        run.total_insurance_employer = total_ins_er
        run.total_kpcd_employer = total_kpcd
        run.total_bhtnld_employer = total_bhtnld
        run.total_pit = total_pit
        run.total_net = total_net
        run.status = "calculated"
        run.save()

        return run

    @transaction.atomic
    def post(self, run: PayrollRun) -> AccountingVoucher:
        """Post payroll → generate accounting voucher.

        Bút toán (8 lines):
        N642   (total gross + employer insurance + KPCĐ + BHTNLĐ) — salary expense
        C334   (net payable to employees)
        C3336  (PIT payable)
        C3382  (KPCĐ payable — kinh phí công đoàn)
        C3383  (BHXH payable — employee + employer)
        C3384  (BHYT payable)
        C3386  (BHTN payable)
        C3339  (BHTNLĐ-BNN payable — other statutory payables)
        """
        if run.status == "posted":
            return run.gl_voucher

        voucher_date = date(run.fiscal_year, run.period_num, 1)

        employer_total_cost = (
            run.total_insurance_employer + run.total_kpcd_employer + run.total_bhtnld_employer
        )

        voucher = AccountingVoucher.objects.create(
            company=run.company,
            fiscal_year=run.fiscal_year,
            period=run.period_num,
            voucher_no=f"PAY-{run.period}",
            voucher_type="payroll",
            voucher_date=voucher_date,
            currency_code="VND",
            total_vnd=run.total_gross + employer_total_cost,
            status=AccountingVoucher.Status.DRAFT,
            source="payroll",
            source_reference_id=run.id,
            description=f"Tiền lương kỳ {run.period}",
        )

        line_no = 1
        # N642 — total cost = gross + employer insurance + KPCĐ + BHTNLĐ
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code="642",
            debit_vnd=run.total_gross + employer_total_cost,
            description=f"CP lương + BHXH/KPCĐ/BHTNLĐ DN kỳ {run.period}",
        )
        line_no += 1

        # C334 — net payable to employees
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code="334",
            credit_vnd=run.total_net,
            description=f"Phải trả NLĐ (net) {run.period}",
        )
        line_no += 1

        # C3336 — PIT payable
        if run.total_pit > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3336",
                credit_vnd=run.total_pit,
                description=f"Thuế TNCN kỳ {run.period}",
            )
            line_no += 1

        # C3382 — Kinh phí công đoàn (employer only, 2%)
        if run.total_kpcd_employer > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3382",
                credit_vnd=run.total_kpcd_employer,
                description=f"Kinh phí công đoàn kỳ {run.period}",
            )
            line_no += 1

        # C3383 — BHXH payable (employee + employer)
        total_bhxh = sum(
            (ln.social_insurance_employee + ln.social_insurance_employer) for ln in run.lines.all()
        )
        if total_bhxh > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3383",
                credit_vnd=total_bhxh,
                description=f"BHXH kỳ {run.period}",
            )
            line_no += 1

        # C3384 — BHYT payable
        total_bhyt = sum(
            (ln.health_insurance_employee + ln.health_insurance_employer) for ln in run.lines.all()
        )
        if total_bhyt > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3384",
                credit_vnd=total_bhyt,
                description=f"BHYT kỳ {run.period}",
            )
            line_no += 1

        # C3386 — BHTN payable
        total_bhtn = sum(
            (ln.unemployment_insurance_employee + ln.unemployment_insurance_employer)
            for ln in run.lines.all()
        )
        if total_bhtn > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3386",
                credit_vnd=total_bhtn,
                description=f"BHTN kỳ {run.period}",
            )
            line_no += 1

        # C3339 — BHTNLĐ-BNN payable (employer only, 0.5%)
        if run.total_bhtnld_employer > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="3339",
                credit_vnd=run.total_bhtnld_employer,
                description=f"BHTNLĐ-BNN kỳ {run.period}",
            )
            line_no += 1

        # Post voucher
        VoucherPostingService().post(voucher)

        run.gl_voucher = voucher
        run.status = "posted"
        run.save()

        return voucher
