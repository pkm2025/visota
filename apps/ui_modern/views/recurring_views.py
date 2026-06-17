"""Placeholder recurring views — filled in by Task 4."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, View


class RecurringListView(LoginRequiredMixin, ListView):
    template_name = "modern/recurring/list.html"
    context_object_name = "templates"
    login_url = "/auth/login/"

    def get_queryset(self):
        from apps.recurring.models import RecurringTemplate

        return RecurringTemplate.objects.all().order_by("id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Bút toán định kỳ"
        return ctx


class RecurringRunView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        from django.contrib import messages

        from apps.core.models import Company
        from apps.recurring.services import RecurringService

        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty.")
            return redirect("ui_modern:recurring_list")

        svc = RecurringService()
        results = svc.run_all_due()
        messages.success(request, f"Đã chạy {len(results)} bút toán định kỳ đến hạn.")
        return redirect("ui_modern:recurring_list")

    def get(self, request, *args, **kwargs):
        return redirect("ui_modern:recurring_list")
