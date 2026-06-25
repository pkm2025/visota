"""FX UI views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.core.models import Company

from .models import Currency, ExchangeRate, FxRevaluationBatch
from .services import FxRevaluationService


class ExchangeRateListView(LoginRequiredMixin, ListView):
    template_name = "modern/fx/rate_list.html"
    context_object_name = "rates"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = (
            getattr(self.request, "current_company", None) or Company.objects.first()
        )
        return ExchangeRate.objects.filter(company=company).order_by("-rate_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tỷ giá hối đoái"
        ctx["currencies"] = Currency.objects.filter(is_active=True).exclude(code="VND")
        return ctx


class FxRevaluationListView(LoginRequiredMixin, ListView):
    template_name = "modern/fx/revaluation_list.html"
    context_object_name = "batches"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = (
            getattr(self.request, "current_company", None) or Company.objects.first()
        )
        return FxRevaluationBatch.objects.filter(company=company).order_by(
            "-period_year", "-period_month"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Định giá lại ngoại tệ cuối kỳ"
        return ctx


class FxRevaluationRunView(LoginRequiredMixin, View):
    """POST: run revaluation for given period."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = (
            getattr(request, "current_company", None) or Company.objects.first()
        )
        year = int(request.POST.get("year", 2026))
        month = int(request.POST.get("month", 6))
        try:
            batch = FxRevaluationService.run_revaluation(
                company, year, month, posted_by=request.user
            )
            messages.success(
                request,
                f"Đã định giá lại ngoại tệ {month:02d}/{year} — voucher {batch.gl_voucher.voucher_no}.",
            )
        except Exception as e:
            messages.error(request, f"Lỗi: {e}")
        return redirect("ui_modern:fx_revaluation_list")
