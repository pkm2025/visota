"""Bidding UI views."""

import contextlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.models import Company
from apps.ui_modern.mixins import require_current_company

from .models import BidOpportunity
from .services import BidConverterService


class BidOpportunityListView(LoginRequiredMixin, ListView):
    template_name = "modern/bidding/list.html"
    context_object_name = "bids"
    paginate_by = 50
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        qs = BidOpportunity.objects.filter(company=company)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Cơ hội đấu thầu"
        return ctx


class BidOpportunityCreateView(LoginRequiredMixin, TemplateView):
    """Create a new bid opportunity via custom POST handling."""

    template_name = "modern/bidding/bid_form.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm gói thầu"
        ctx["bid_methods"] = BidOpportunity.BiddingMethod.choices
        ctx["bid_forms"] = BidOpportunity.Form.choices
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)

        bid_no = request.POST.get("bid_no", "").strip()
        bid_name = request.POST.get("bid_name", "").strip()
        investor_name = request.POST.get("investor_name", "").strip()

        if not (bid_no and bid_name and investor_name):
            messages.error(request, "Vui lòng nhập mã gói thầu, tên gói và chủ đầu tư.")
            return redirect("ui_modern:bid_create")

        try:
            price = Decimal(request.POST.get("bid_package_price", "0") or "0")
        except InvalidOperation:
            price = Decimal("0")

        try:
            duration = int(request.POST.get("duration_days", "0") or "0")
        except ValueError:
            duration = 0

        submission_deadline = None
        deadline_str = request.POST.get("bid_submission_deadline", "").strip()
        if deadline_str:
            with contextlib.suppress(ValueError):
                submission_deadline = datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")

        BidOpportunity.objects.create(
            company=company,
            bid_no=bid_no,
            bid_name=bid_name,
            investor_name=investor_name,
            investor_tax_code=request.POST.get("investor_tax_code", "").strip(),
            bid_method=request.POST.get("bid_method", BidOpportunity.BiddingMethod.OPEN),
            bid_form=request.POST.get("bid_form", BidOpportunity.Form.ONE_STAGE),
            bid_type=request.POST.get("bid_type", "construction").strip(),
            bid_package_price=price,
            currency_code=request.POST.get("currency_code", "VND").strip(),
            duration_days=duration,
            published_at=request.POST.get("published_at") or None,
            bid_submission_deadline=submission_deadline,
            is_online=request.POST.get("is_online") == "1",
            bid_system_ref=request.POST.get("bid_system_ref", "").strip(),
            description=request.POST.get("description", "").strip(),
            status="identified",
            created_by=request.user,
        )
        messages.success(request, f"Đã tạo gói thầu {bid_no} - {bid_name}")
        return redirect("ui_modern:bid_list")


class BidOpportunityDetailView(LoginRequiredMixin, DetailView):
    template_name = "modern/bidding/detail.html"
    context_object_name = "bid"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return BidOpportunity.objects.select_related("result", "submission", "company")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Gói thầu {self.object.bid_no}"
        return ctx


class BidConvertToContractView(LoginRequiredMixin, View):
    """POST: convert a WON bid to Contract."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        bid = get_object_or_404(BidOpportunity, pk=pk)
        try:
            BidConverterService.mark_won(bid)
            contract = BidConverterService.convert_to_contract(bid)
            messages.success(
                request,
                f"Đã trúng thầu và tạo hợp đồng {contract.contract_no} "
                f"({contract.value:,.0f} VND).",
            )
        except Exception as e:
            messages.error(request, f"Lỗi chuyển đổi: {e}")
        return redirect("ui_modern:bid_detail", pk=pk)
