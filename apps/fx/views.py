"""FX UI views."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView

from apps.core.models import Company
from apps.ui_modern.mixins import require_current_company

from .models import Currency, ExchangeRate, FxRevaluationBatch
from .services import FxRevaluationService


class ExchangeRateListView(LoginRequiredMixin, ListView):
    template_name = "modern/fx/rate_list.html"
    context_object_name = "rates"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return ExchangeRate.objects.filter(company=company).order_by("-rate_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tỷ giá hối đoái"
        ctx["currencies"] = Currency.objects.filter(is_active=True).exclude(code="VND")
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        from_currency = request.POST.get("from_currency", "").strip().upper()
        rate_date = request.POST.get("rate_date")
        rate_str = request.POST.get("rate", "").strip()

        if not (from_currency and rate_date and rate_str):
            messages.error(request, "Vui lòng nhập đầy đủ loại ngoại tệ, ngày và tỷ giá.")
            return redirect("ui_modern:fx_rate_list")

        try:
            rate = Decimal(rate_str)
        except Exception:
            messages.error(request, "Tỷ giá không hợp lệ.")
            return redirect("ui_modern:fx_rate_list")

        ExchangeRate.objects.create(
            company=company,
            from_currency=from_currency,
            to_currency="VND",
            rate_date=rate_date,
            rate=rate,
            rate_type=request.POST.get("rate_type", "VCB"),
        )
        messages.success(request, f"Đã thêm tỷ giá 1 {from_currency} = {rate} VND")
        return redirect("ui_modern:fx_rate_list")


class FxRevaluationListView(LoginRequiredMixin, ListView):
    template_name = "modern/fx/revaluation_list.html"
    context_object_name = "batches"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
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
        company = getattr(request, "current_company", None) or Company.objects.first()
        year = int(request.POST.get("year", 2026))
        month = int(request.POST.get("month", 6))
        try:
            batch = FxRevaluationService.run_revaluation(
                company, year, month, posted_by=request.user
            )
            messages.success(
                request,
                f"Đã định giá lại ngoại tệ {month:02d}/{year}"
                f" — voucher {batch.gl_voucher.voucher_no}.",
            )
        except Exception as e:
            messages.error(request, f"Lỗi: {e}")
        return redirect("ui_modern:fx_revaluation_list")
