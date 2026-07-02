"""Cost accounting report view — Bảng tính giá thành."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.costing.services import CostingService


class CostReportView(LoginRequiredMixin, TemplateView):
    """Bảng tính giá thành sản phẩm — chi phí SX theo kỳ."""

    template_name = "modern/reporting/cost_report.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        output_qty_str = self.request.GET.get("output_qty", "0").strip()
        try:
            output_qty = Decimal(output_qty_str) if output_qty_str else Decimal("0")
        except Exception:
            output_qty = Decimal("0")

        company = getattr(self.request, "current_company", None) or Company.objects.first()

        service = CostingService(company)
        if output_qty > 0:
            summary = service.calculate_unit_cost(fiscal_year, period, output_qty)
        else:
            summary = service.collect_costs(fiscal_year, period)

        ctx.update(
            {
                "page_title": "Bảng tính giá thành",
                "fiscal_year": fiscal_year,
                "period": period,
                "summary": summary,
                "output_qty": output_qty,
            }
        )
        return ctx
