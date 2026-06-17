"""Period closing view."""

from datetime import date as dt

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.ledger.services import PeriodClosingService


class PeriodClosingView(LoginRequiredMixin, TemplateView):
    template_name = "modern/ledger/closing.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Kết chuyển cuối kỳ"
        today = dt.today()
        ctx["default_year"] = today.year
        ctx["default_month"] = today.month
        ctx["year_choices"] = [2024, 2025, 2026, 2027]
        ctx["period_choices"] = list(range(1, 13))
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, "No company")
            return redirect("ui_modern:period_closing")

        year = int(request.POST.get("fiscal_year"))
        month = int(request.POST.get("period"))

        service = PeriodClosingService(company=company)
        result = service.close_period(fiscal_year=year, period=month)

        if result.get("skipped"):
            messages.info(request, f"Kỳ {month}/{year} đã kết chuyển hoặc không có dữ liệu")
        else:
            messages.success(
                request,
                f"Kết chuyển {month}/{year}: DT={result['total_revenue']:,.0f} "
                f"CP={result['total_expense']:,.0f} "
                f"Lãi/Lỗ={result['profit']:,.0f}",
            )
        return redirect("ui_modern:period_closing")
