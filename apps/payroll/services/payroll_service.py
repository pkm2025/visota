"""PayrollService — calculate salary + BHXH + PIT + post voucher."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.hr.models import Employee
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.payroll.models import PayrollLine, PayrollRun

# 2024-2026 Vietnamese insurance rates
INSURANCE_RATES = {
    "social_employee": Decimal("0.08"),  # BHXH NV đóng 8%
    "social_employer": Decimal("0.175"),  # BHXH DN đóng 17.5%
    "health_employee": Decimal("0.015"),  # BHYT NV 1.5%
    "health_employer": Decimal("0.03"),  # BHYT DN 3%
    "unemployment_employee": Decimal("0.01"),  # BHTN NV 1%
    "unemployment_employer": Decimal("0.01"),  # BHTN DN 1%
}

# PIT brackets (monthly taxable income, VND)
PIT_BRACKETS = [
    (Decimal("5000000"), Decimal("0.05")),
    (Decimal("10000000"), Decimal("0.10")),
    (Decimal("18000000"), Decimal("0.15")),
    (Decimal("32000000"), Decimal("0.20")),
    (Decimal("52000000"), Decimal("0.25")),
    (Decimal("80000000"), Decimal("0.30")),
    (Decimal("999999999"), Decimal("0.35")),
]

PERSONAL_DEDUCTION = Decimal("11000000")  # Giảm trừ gia cảnh bản thân
DEPENDENT_DEDUCTION = Decimal("4400000")  # Mỗi người phụ thuộc


def calculate_pit(taxable_income: Decimal) -> Decimal:
    """Progressive PIT calculation based on brackets."""
    if taxable_income <= 0:
        return Decimal("0")
    pit = Decimal("0")
    remaining = taxable_income
    prev_cap = Decimal("0")
    for cap, rate in PIT_BRACKETS:
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

        for idx, emp in enumerate(employees, start=1):
            # Prorated base salary by work days (simplified — assume full month)
            gross = emp.base_salary + emp.allowance

            # Insurance — employee portion
            si_emp = (gross * INSURANCE_RATES["social_employee"]).quantize(Decimal("1"))
            hi_emp = (gross * INSURANCE_RATES["health_employee"]).quantize(Decimal("1"))
            ui_emp = (gross * INSURANCE_RATES["unemployment_employee"]).quantize(Decimal("1"))
            ins_emp_total = si_emp + hi_emp + ui_emp

            # Insurance — employer portion
            si_er = (gross * INSURANCE_RATES["social_employer"]).quantize(Decimal("1"))
            hi_er = (gross * INSURANCE_RATES["health_employer"]).quantize(Decimal("1"))
            ui_er = (gross * INSURANCE_RATES["unemployment_employer"]).quantize(Decimal("1"))

            # PIT: taxable = gross - insurance_employee - personal deduction
            taxable = gross - ins_emp_total - PERSONAL_DEDUCTION
            pit = calculate_pit(taxable) if taxable > 0 else Decimal("0")

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
                pit=pit,
                net_salary=net,
            )

            total_gross += gross
            total_ins_emp += ins_emp_total
            total_ins_er += si_er + hi_er + ui_er
            total_pit += pit
            total_net += net

        run.total_gross = total_gross
        run.total_insurance_employee = total_ins_emp
        run.total_insurance_employer = total_ins_er
        run.total_pit = total_pit
        run.total_net = total_net
        run.status = "calculated"
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
        if run.status == "posted":
            return run.gl_voucher

        voucher_date = date(run.fiscal_year, run.period_num, 1)

        voucher = AccountingVoucher.objects.create(
            company=run.company,
            fiscal_year=run.fiscal_year,
            period=run.period_num,
            voucher_no=f"PAY-{run.period}",
            voucher_type="payroll",
            voucher_date=voucher_date,
            currency_code="VND",
            total_vnd=run.total_gross + run.total_insurance_employer,
            status=AccountingVoucher.Status.DRAFT,
            source="payroll",
            source_reference_id=run.id,
            description=f"Tiền lương kỳ {run.period}",
        )

        line_no = 1
        # N642 — total cost = gross + employer insurance
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code="642",
            debit_vnd=run.total_gross + run.total_insurance_employer,
            description=f"CP lương + BHXH DN kỳ {run.period}",
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

        # Post voucher
        VoucherPostingService().post(voucher)

        run.gl_voucher = voucher
        run.status = "posted"
        run.save()

        return voucher
