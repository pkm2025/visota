"""Bidding UI views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.models import Company

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
