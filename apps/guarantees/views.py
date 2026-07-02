"""Bank guarantee UI views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.core.models import Company

from .models import BankGuarantee


class BankGuaranteeListView(LoginRequiredMixin, ListView):
    template_name = "modern/guarantees/list.html"
    context_object_name = "guarantees"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        qs = BankGuarantee.objects.filter(company=company).select_related("contract")
        gt = self.request.GET.get("guarantee_type")
        if gt:
            qs = qs.filter(guarantee_type=gt)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Bảo lãnh ngân hàng"
        ctx["type_choices"] = BankGuarantee.GuaranteeType.choices
        return ctx
