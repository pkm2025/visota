"""Payroll UI view — calculate / post a monthly payroll run."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.payroll.models import PayrollRun
from apps.payroll.services import PayrollService
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class PayrollRunView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET shows the period picker + recent runs table.
    POST with action=calculate → PayrollService.calculate(period, 22).
    POST with action=post → calculate then PayrollService.post(run)."""

    template_name = "modern/payroll/run.html"
    login_url = "/auth/login/"
    required_permission = "payroll.access"

    def get(self, request, *args, **kwargs):
        from datetime import date

        today = date.today()
        company = require_current_company(request)
        recent_runs = (
            PayrollRun.objects.filter(company=company)
            .select_related("company")
            .order_by("-period")[:10]
        )
        return render(
            request,
            self.template_name,
            {
                "page_title": "Tính lương kỳ",
                "default_year": today.year,
                "default_month": today.month,
                "recent_runs": recent_runs,
            },
        )

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        action = request.POST.get("action", "calculate")
        year = request.POST.get("year")
        month = request.POST.get("month")

        try:
            year_i = int(year)
            month_i = int(month)
        except (TypeError, ValueError):
            messages.error(request, "Năm/tháng không hợp lệ")
            return redirect("ui_modern:payroll_run")

        if not (1 <= month_i <= 12) or year_i < 2000:
            messages.error(request, "Năm/tháng không hợp lệ")
            return redirect("ui_modern:payroll_run")

        period = f"{year_i:04d}-{month_i:02d}"

        try:
            run = PayrollService(company).calculate(period, standard_work_days=22)

            if action == "post":
                PayrollService(company).post(run)
                messages.success(
                    request,
                    f"Đã ghi sổ lương {period}: gross={run.total_gross:,} "
                    f"net={run.total_net:,} PIT={run.total_pit:,}",
                )
            else:
                messages.success(
                    request,
                    f"Đã tính lương {period}: gross={run.total_gross:,} "
                    f"net={run.total_net:,} ({run.lines.count()} nhân viên)",
                )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Lỗi tính lương: {exc}")

        return redirect("ui_modern:payroll_run")
