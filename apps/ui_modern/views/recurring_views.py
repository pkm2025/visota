"""Recurring UI views — list + manual run."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View

from apps.recurring.models import RecurringTemplate
from apps.recurring.services import RecurringService
from apps.ui_modern.mixins import require_current_company


class RecurringListView(LoginRequiredMixin, ListView):
    """List of recurring templates with last_run/next_run/is_active."""

    template_name = "modern/recurring/list.html"
    context_object_name = "templates"
    login_url = "/auth/login/"

    def get_queryset(self):
        return RecurringTemplate.objects.select_related("company").order_by(
            "schedule_type", "day_of_month", "id"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Bút toán định kỳ"
        return ctx


class RecurringRunView(LoginRequiredMixin, View):
    """POST triggers run_all_due (or run a specific template via ?id=)."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        if not company:
            messages.error(request, "Chưa có công ty.")
            return redirect("ui_modern:recurring_list")

        svc = RecurringService(company=company)

        specific_id = request.POST.get("template_id") or request.GET.get("id")
        if specific_id:
            tpl = get_object_or_404(RecurringTemplate, pk=specific_id, company=company)
            result = svc.run_one(tpl)
            messages.success(
                request,
                f"Đã chạy '{tpl.name}' → {result.get('status', '?')}",
            )
        else:
            results = svc.run_all_due()
            messages.success(request, f"Đã chạy {len(results)} bút toán định kỳ đến hạn.")
        return redirect("ui_modern:recurring_list")

    def get(self, request, *args, **kwargs):
        # GET also triggers (convenience for sidebar link)
        return self.post(request, *args, **kwargs)
