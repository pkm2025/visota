"""Loan UI views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.core.models import Company

from .models import BankLoan


class BankLoanListView(LoginRequiredMixin, ListView):
    template_name = "modern/loans/list.html"
    context_object_name = "loans"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = (
            getattr(self.request, "current_company", None) or Company.objects.first()
        )
        return BankLoan.objects.filter(company=company).select_related("contract")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Vay vốn ngân hàng"
        return ctx
