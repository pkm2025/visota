"""Cash flow statement views (B03-DN) — direct and indirect methods."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.reporting.services.cash_flow import CashFlowService
from apps.ui_modern.mixins import require_current_company
from apps.ui_modern.views.report_views import _financial_period_choices, _parse_period_kwargs


class CashFlowDirectView(LoginRequiredMixin, TemplateView):
    """BC dòng tiền theo PP trực tiếp (B03-DN)."""

    template_name = "modern/reporting/cash_flow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)
        if company:
            ctx.update(CashFlowService(company=company).generate_direct(fy, period))
        ctx.update(
            {
                "page_title": "BC dòng tiền PP trực tiếp (B03-DN)",
                "fiscal_year": fy,
                "period": period,
                **_financial_period_choices(),
            }
        )
        return ctx


class CashFlowIndirectView(LoginRequiredMixin, TemplateView):
    """BC dòng tiền theo PP gián tiếp (B03-DN)."""

    template_name = "modern/reporting/cash_flow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)
        if company:
            ctx.update(CashFlowService(company=company).generate_indirect(fy, period))
        ctx.update(
            {
                "page_title": "BC dòng tiền PP gián tiếp (B03-DN)",
                "fiscal_year": fy,
                "period": period,
                **_financial_period_choices(),
            }
        )
        return ctx
