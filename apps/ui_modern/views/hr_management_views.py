"""HR management views — labor contracts, dependents, leave, insurance dashboard."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView

from apps.hr.models import (
    Dependent,
    InsuranceContribution,
    LaborContract,
    LeaveRecord,
)
from apps.ui_modern.forms import LaborContractForm, LeaveRequestForm
from apps.ui_modern.mixins import require_current_company


class LaborContractListView(LoginRequiredMixin, ListView):
    """Danh sách hợp đồng lao động."""

    template_name = "modern/hr/labor_contract_list.html"
    context_object_name = "contracts"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return (
            LaborContract.objects.filter(company=company)
            .select_related("employee", "department", "company")
            .order_by("-start_date")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hợp đồng lao động"
        return ctx


class LaborContractCreateView(LoginRequiredMixin, CreateView):
    """Tạo hợp đồng lao động mới."""

    model = LaborContract
    template_name = "modern/hr/labor_contract_form.html"
    form_class = LaborContractForm
    login_url = "/auth/login/"
    success_url = reverse_lazy("ui_modern:labor_contract_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm hợp đồng lao động"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = require_current_company(self.request)
        return super().form_valid(form)


class DependentListView(LoginRequiredMixin, ListView):
    """Danh sách người phụ thuộc (giảm trừ gia cảnh)."""

    template_name = "modern/hr/dependent_list.html"
    context_object_name = "dependents"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return (
            Dependent.objects.filter(employee__company=company)
            .select_related("employee")
            .order_by("-valid_from")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Người phụ thuộc"
        return ctx


class LeaveRequestView(LoginRequiredMixin, CreateView):
    """Tạo đơn xin nghỉ phép."""

    model = LeaveRecord
    template_name = "modern/hr/leave_request_form.html"
    form_class = LeaveRequestForm
    login_url = "/auth/login/"
    success_url = reverse_lazy("ui_modern:employee_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Xin nghỉ phép"
        ctx["is_new"] = True
        return ctx


class InsuranceDashboardView(LoginRequiredMixin, TemplateView):
    """Tổng hợp đóng BHXH cho kỳ hiện tại."""

    template_name = "modern/hr/insurance_dashboard.html"
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
        period_str = f"{fiscal_year:04d}-{period:02d}"

        company = require_current_company(self.request)
        contributions_qs = InsuranceContribution.objects.filter(
            company=company, period=period_str
        ).select_related("employee")

        totals = contributions_qs.aggregate(
            salary_base=Sum("salary_base"),
            total_emp=Sum("total_employee"),
            total_er=Sum("total_employer"),
            bhxh_emp=Sum("bhxh_employee"),
            bhxh_er=Sum("bhxh_employer"),
            kpcd_er=Sum("kpcd_employer"),
        )

        ctx.update(
            {
                "page_title": "Tổng hợp BHXH",
                "fiscal_year": fiscal_year,
                "period": period,
                "period_str": period_str,
                "contributions": contributions_qs,
                "total_salary_base": totals["salary_base"] or Decimal("0"),
                "total_employee": totals["total_emp"] or Decimal("0"),
                "total_employer": totals["total_er"] or Decimal("0"),
                "total_bhxh_emp": totals["bhxh_emp"] or Decimal("0"),
                "total_bhxh_er": totals["bhxh_er"] or Decimal("0"),
                "total_kpcd_er": totals["kpcd_er"] or Decimal("0"),
                "employee_count": contributions_qs.count(),
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx
