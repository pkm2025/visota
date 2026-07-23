"""Timesheet / attendance views — chấm công."""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.hr.models import Employee
from apps.payroll.models import AttendanceRecord
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class TimesheetView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET shows attendance grid for a month; POST saves individual entries.

    Supports bulk entry: user picks year+month, sees all active employees in rows,
    days in columns. Each cell is a dropdown (X/P/L/Ô/E/A).
    """

    template_name = "modern/payroll/timesheet.html"
    login_url = "/auth/login/"
    required_permission = "payroll.access"

    SYMBOLS = {
        "X": ("present", 1.0, "Có mặt"),
        "P": ("leave", 0.0, "Nghỉ phép"),
        "L": ("late", 1.0, "Đi trễ"),
        "O": ("early_leave", 1.0, "Về sớm"),
        "A": ("absent", 0.0, "Vắng"),
        "H": ("holiday", 0.0, "Nghỉ lễ"),
    }

    def get(self, request, *args, **kwargs):
        company = require_current_company(request)
        today = date.today()
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        employees = Employee.objects.filter(
            company=company, is_active=True
        ).order_by("code")

        # Build days in month
        next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        days_in_month = (next_month - timedelta(days=1)).day
        days = list(range(1, days_in_month + 1))

        # Load existing attendance into dict: {(emp_id, day): symbol}
        existing = {}
        records = AttendanceRecord.objects.filter(
            company=company,
            attendance_date__year=year,
            attendance_date__month=month,
        )
        status_to_symbol = {v[0]: k for k, v in self.SYMBOLS.items()}
        for rec in records:
            symbol = status_to_symbol.get(rec.status, "X")
            existing[(rec.employee_id, rec.attendance_date.day)] = symbol

        return render(
            request,
            self.template_name,
            {
                "page_title": f"Chấm công {month:02d}/{year}",
                "employees": employees,
                "days": days,
                "year": year,
                "month": month,
                "existing": existing,
                "symbols": self.SYMBOLS,
                "symbol_keys": list(self.SYMBOLS.keys()),
            },
        )

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        year = int(request.POST.get("year", date.today().year))
        month = int(request.POST.get("month", date.today().month))

        employees = Employee.objects.filter(
            company=company, is_active=True
        ).values_list("id", flat=True)

        next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        days_in_month = (next_month - timedelta(days=1)).day

        updated = 0
        for emp_id in employees:
            for day in range(1, days_in_month + 1):
                field_name = f"att_{emp_id}_{day}"
                symbol = request.POST.get(field_name, "").strip()
                if not symbol or symbol not in self.SYMBOLS:
                    continue

                status, work_days, _ = self.SYMBOLS[symbol]
                att_date = date(year, month, day)

                obj, created = AttendanceRecord.objects.update_or_create(
                    employee_id=emp_id,
                    attendance_date=att_date,
                    defaults={
                        "company": company,
                        "status": status,
                        "work_days": work_days,
                    },
                )
                updated += 1

        messages.success(request, f"Đã lưu {updated} bản ghi chấm công {month:02d}/{year}")
        return redirect(f"{request.path}?year={year}&month={month}")
