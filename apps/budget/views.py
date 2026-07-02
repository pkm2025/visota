"""Budget UI views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.models import Company

from .models import Budget, CashFlowProjection
from .services import BudgetVarianceService, CashFlowService


class BudgetListView(LoginRequiredMixin, ListView):
    template_name = "modern/budget/list.html"
    context_object_name = "budgets"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        return Budget.objects.filter(company=company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ngân sách"
        return ctx


class BudgetDetailView(LoginRequiredMixin, DetailView):
    template_name = "modern/budget/detail.html"
    context_object_name = "budget"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return Budget.objects.prefetch_related("lines")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = str(self.object)
        # Aggregate by account_group
        groups = {}
        for line in self.object.lines.all():
            key = line.account_group
            if key not in groups:
                groups[key] = {
                    "name": key,
                    "planned": Decimal(0),
                    "actual": Decimal(0),
                    "direction": line.direction,
                }
            groups[key]["planned"] += line.planned_amount
            groups[key]["actual"] += line.actual_amount
        ctx["groups"] = list(groups.values())
        return ctx


class BudgetGenerateView(LoginRequiredMixin, View):
    """POST: generate default budget template for given year."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        year = int(request.POST.get("year", 2026))
        budget = BudgetVarianceService.generate_default_template(company, year)
        messages.success(request, f"Đã tạo ngân sách {year} ({budget.lines.count()} dòng).")
        return redirect("ui_modern:budget_detail", pk=budget.pk)


class BudgetRefreshActualsView(LoginRequiredMixin, View):
    """POST: refresh actuals from ledger."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        budget = Budget.objects.get(pk=pk)
        BudgetVarianceService.refresh_actuals(budget)
        messages.success(request, "Đã cập nhật số thực tế từ sổ cái.")
        return redirect("ui_modern:budget_detail", pk=pk)


class CashFlowView(LoginRequiredMixin, TemplateView):
    template_name = "modern/budget/cash_flow.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        ctx["page_title"] = "Dự phóng dòng tiền"
        ctx["projections"] = CashFlowProjection.objects.filter(company=company).order_by(
            "-period_year", "-period_month"
        )[:12]
        return ctx


class CashFlowGenerateView(LoginRequiredMixin, View):
    """POST: generate projection for given period."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        year = int(request.POST.get("year", 2026))
        month = int(request.POST.get("month", 6))
        proj = CashFlowService.generate_for_period(company, year, month)
        messages.success(
            request,
            f"Dự phóng {month:02d}/{year}: AR {proj.expected_ar_collection:,.0f} / "
            f"AP {proj.expected_ap_payment:,.0f} / Net {proj.net_cash_flow:,.0f}",
        )
        return redirect("ui_modern:cash_flow")


# Avoid import error at top of file
from decimal import Decimal  # noqa: E402
