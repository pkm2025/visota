"""Payroll UI view — calculate / post a monthly payroll run."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.payroll.models import PayrollRun
from apps.payroll.services import PayrollService


class PayrollRunView(LoginRequiredMixin, View):
    """GET shows the period picker + recent runs table.
    POST with action=calculate → PayrollService.calculate(period, 22).
    POST with action=post → calculate then PayrollService.post(run)."""

    template_name = "modern/payroll/run.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        from datetime import date

        today = date.today()
        recent_runs = PayrollRun.objects.select_related("company").order_by("-period")[:10]
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
        from apps.core.models import Company

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

        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty nào được cấu hình.")
            return redirect("ui_modern:payroll_run")

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
