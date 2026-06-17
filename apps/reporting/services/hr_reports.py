"""HR report services: D62, labor usage, salary fund, PIT monthly."""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q

from apps.hr.models import (
    Department,
    Employee,
    InsuranceContribution,
)
from apps.payroll.models import PayrollRun


def _period_str(fiscal_year: int, period: int) -> str:
    return f"{fiscal_year:04d}-{period:02d}"


class D62ReportService:
    """D62 report: per-employee BHXH contribution summary (monthly)."""

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        period_str = _period_str(fiscal_year, period)
        contributions = (
            InsuranceContribution.objects.filter(
                company=self.company,
                period=period_str,
            )
            .select_related("employee")
            .order_by("employee__code")
        )

        rows = []
        grand_salary_base = Decimal("0")
        grand_bhxh_emp = Decimal("0")
        grand_bhyt_emp = Decimal("0")
        grand_bhtn_emp = Decimal("0")
        grand_total_emp = Decimal("0")
        grand_bhxh_er = Decimal("0")
        grand_bhyt_er = Decimal("0")
        grand_bhtn_er = Decimal("0")
        grand_bhtnld_er = Decimal("0")
        grand_kpcd_er = Decimal("0")
        grand_total_er = Decimal("0")

        for c in contributions:
            emp = c.employee
            rows.append(
                {
                    "employee_code": emp.code,
                    "name": emp.full_name,
                    "department": emp.department.name if emp.department else "",
                    "salary_base": c.salary_base,
                    "bhxh_emp": c.bhxh_employee,
                    "bhyt_emp": c.bhyt_employee,
                    "bhtn_emp": c.bhtn_employee,
                    "total_emp": c.total_employee,
                    "bhxh_er": c.bhxh_employer,
                    "bhyt_er": c.bhyt_employer,
                    "bhtn_er": c.bhtn_employer,
                    "bhtnld_er": c.bhtnld_employer,
                    "kpcd_er": c.kpcd_employer,
                    "total_er": c.total_employer,
                }
            )
            grand_salary_base += c.salary_base
            grand_bhxh_emp += c.bhxh_employee
            grand_bhyt_emp += c.bhyt_employee
            grand_bhtn_emp += c.bhtn_employee
            grand_total_emp += c.total_employee
            grand_bhxh_er += c.bhxh_employer
            grand_bhyt_er += c.bhyt_employer
            grand_bhtn_er += c.bhtn_employer
            grand_bhtnld_er += c.bhtnld_employer
            grand_kpcd_er += c.kpcd_employer
            grand_total_er += c.total_employer

        return {
            "period": period_str,
            "fiscal_year": fiscal_year,
            "period_num": period,
            "rows": rows,
            "grand_salary_base": grand_salary_base,
            "grand_bhxh_emp": grand_bhxh_emp,
            "grand_bhyt_emp": grand_bhyt_emp,
            "grand_bhtn_emp": grand_bhtn_emp,
            "grand_total_emp": grand_total_emp,
            "grand_bhxh_er": grand_bhxh_er,
            "grand_bhyt_er": grand_bhyt_er,
            "grand_bhtn_er": grand_bhtn_er,
            "grand_bhtnld_er": grand_bhtnld_er,
            "grand_kpcd_er": grand_kpcd_er,
            "grand_total_er": grand_total_er,
        }


class LaborUsageReportService:
    """Tình hình sử dụng lao động: headcount, hires, resignations by department."""

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int) -> dict:
        year_start = date(fiscal_year, 1, 1)
        year_end = date(fiscal_year, 12, 31)

        employees = Employee.objects.filter(company=self.company)
        total = employees.count()
        active = employees.filter(status=Employee.Status.ACTIVE).count()
        resigned = employees.filter(status=Employee.Status.RESIGNED).count()
        on_leave = employees.filter(status=Employee.Status.ON_LEAVE).count()

        new_hires = employees.filter(
            hire_date__gte=year_start, hire_date__lte=year_end
        ).count()

        # Per-department breakdown
        depts = (
            Department.objects.filter(company=self.company)
            .annotate(
                emp_count=Count("employees"),
                active_count=Count(
                    "employees", filter=Q(employees__status=Employee.Status.ACTIVE)
                ),
                new_hire_count=Count(
                    "employees",
                    filter=Q(
                        employees__hire_date__gte=year_start,
                        employees__hire_date__lte=year_end,
                    ),
                ),
            )
            .order_by("code")
        )
        by_department = [
            {
                "department_code": d.code,
                "department_name": d.name,
                "headcount": d.emp_count,
                "active": d.active_count,
                "new_hires": d.new_hire_count,
            }
            for d in depts
            if d.emp_count > 0
        ]

        return {
            "fiscal_year": fiscal_year,
            "total_employees": total,
            "active_count": active,
            "resigned_count": resigned,
            "on_leave_count": on_leave,
            "new_hires": new_hires,
            "by_department": by_department,
        }


class SalaryFundReportService:
    """Quỹ lương kỳ: tổng gross/net/BHXH/PIT from PayrollRun."""

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        period_str = _period_str(fiscal_year, period)
        run = (
            PayrollRun.objects.filter(
                company=self.company, period=period_str
            )
            .select_related("gl_voucher")
            .first()
        )

        if not run:
            return {
                "period": period_str,
                "fiscal_year": fiscal_year,
                "period_num": period,
                "status": None,
                "total_gross": Decimal("0"),
                "total_insurance_employee": Decimal("0"),
                "total_insurance_employer": Decimal("0"),
                "total_pit": Decimal("0"),
                "total_net": Decimal("0"),
                "total_kpcd_employer": Decimal("0"),
                "total_bhtnld_employer": Decimal("0"),
                "employee_count": 0,
                "lines": [],
            }

        lines = (
            run.lines.select_related("employee", "employee__department")
            .order_by("line_no")
        )

        return {
            "period": period_str,
            "fiscal_year": fiscal_year,
            "period_num": period,
            "status": run.status,
            "total_gross": run.total_gross,
            "total_insurance_employee": run.total_insurance_employee,
            "total_insurance_employer": run.total_insurance_employer,
            "total_pit": run.total_pit,
            "total_net": run.total_net,
            "total_kpcd_employer": run.total_kpcd_employer,
            "total_bhtnld_employer": run.total_bhtnld_employer,
            "employee_count": lines.count(),
            "lines": list(lines),
        }


class PITMonthlyReportService:
    """Tờ khai thuế TNCN hàng tháng — per-employee PIT breakdown."""

    # Personal deduction (11M) + per-dependent (4.4M) for 2024+
    PERSONAL_DEDUCTION = Decimal("11000000")
    DEPENDENT_DEDUCTION = Decimal("4400000")

    def __init__(self, company):
        self.company = company

    def generate(self, fiscal_year: int, period: int) -> dict:
        period_str = _period_str(fiscal_year, period)
        run = PayrollRun.objects.filter(
            company=self.company, period=period_str
        ).first()

        rows = []
        total_gross = Decimal("0")
        total_insurance = Decimal("0")
        total_pit = Decimal("0")
        total_taxable = Decimal("0")

        if run:
            today = date.today()
            for line in run.lines.select_related(
                "employee", "employee__department"
            ).order_by("line_no"):
                emp = line.employee
                ins = (
                    line.social_insurance_employee
                    + line.health_insurance_employee
                    + line.unemployment_insurance_employee
                )
                # Count active registered dependents
                dep_count = emp.dependents.filter(
                    registration_status="registered",
                    valid_from__lte=today,
                ).exclude(valid_to__lt=today).count() if hasattr(emp, "dependents") else 0
                family_deduction = self.PERSONAL_DEDUCTION + (
                    self.DEPENDENT_DEDUCTION * dep_count
                )
                taxable = line.gross_salary - ins - family_deduction
                if taxable < 0:
                    taxable = Decimal("0")

                rows.append(
                    {
                        "employee_code": emp.code,
                        "name": emp.full_name,
                        "department": emp.department.name if emp.department else "",
                        "gross": line.gross_salary,
                        "insurance_deduction": ins,
                        "dependents": dep_count,
                        "family_deduction": family_deduction,
                        "taxable": taxable,
                        "pit": line.pit,
                        "net": line.net_salary,
                    }
                )
                total_gross += line.gross_salary
                total_insurance += ins
                total_pit += line.pit
                total_taxable += taxable

        return {
            "period": period_str,
            "fiscal_year": fiscal_year,
            "period_num": period,
            "rows": rows,
            "total_gross": total_gross,
            "total_insurance_deduction": total_insurance,
            "total_pit": total_pit,
            "total_taxable": total_taxable,
        }
