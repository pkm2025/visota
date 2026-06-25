"""Approval UI views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.models import Company
from apps.identity.middleware import ModulePermissionMiddleware  # noqa
from apps.identity.models import UserCompanyRole

from .models import ApprovalRequest, ApprovalRule
from .services import ApprovalService


class ApprovalQueueView(LoginRequiredMixin, ListView):
    """Pending approvals awaiting this user's action."""

    template_name = "modern/approvals/queue.html"
    context_object_name = "requests"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = (
            getattr(self.request, "current_company", None) or Company.objects.first()
        )
        if not company:
            return ApprovalRequest.objects.none()
        return ApprovalService.pending_for_user(self.request.user, company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Phê duyệt chờ xử lý"
        ctx["user_role_codes"] = set(
            UserCompanyRole.objects.filter(
                user=self.request.user,
                company=getattr(self.request, "current_company", None)
                or Company.objects.first(),
            ).values_list("role__code", flat=True)
        )
        return ctx


class ApprovalDetailView(LoginRequiredMixin, DetailView):
    """Detail of a single request — see steps + approve/reject buttons."""

    template_name = "modern/approvals/detail.html"
    context_object_name = "request"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return ApprovalRequest.objects.select_related("requested_by", "company")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.object
        ctx["page_title"] = f"Yêu cầu duyệt #{req.id}"
        company = req.company
        user_roles = set(
            UserCompanyRole.objects.filter(
                user=self.request.user, company=company
            ).values_list("role__code", flat=True)
        )
        # Can this user act on the next step?
        next_step = (
            req.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        ctx["next_step"] = next_step
        ctx["can_act"] = (
            req.status == ApprovalRequest.Status.PENDING
            and next_step is not None
            and next_step.role_required in user_roles
        )
        return ctx


class ApprovalApproveView(LoginRequiredMixin, View):
    """POST: approve the current step."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        req = get_object_or_404(ApprovalRequest, pk=pk)
        if req.status != ApprovalRequest.Status.PENDING:
            messages.error(request, "Yêu cầu đã được xử lý.")
            return redirect("ui_modern:approval_detail", pk=pk)
        # Verify user has the required role
        company = req.company
        user_roles = set(
            UserCompanyRole.objects.filter(
                user=request.user, company=company
            ).values_list("role__code", flat=True)
        )
        next_step = (
            req.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        if not next_step or next_step.role_required not in user_roles:
            messages.error(
                request, "Bạn không có quyền phê duyệt bước này."
            )
            return redirect("ui_modern:approval_detail", pk=pk)

        note = request.POST.get("note", "")
        ApprovalService.approve(req, request.user, note)
        messages.success(request, "Đã phê duyệt bước này.")
        return redirect("ui_modern:approval_queue")


class ApprovalRejectView(LoginRequiredMixin, View):
    """POST: reject the request."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        req = get_object_or_404(ApprovalRequest, pk=pk)
        if req.status != ApprovalRequest.Status.PENDING:
            messages.error(request, "Yêu cầu đã được xử lý.")
            return redirect("ui_modern:approval_detail", pk=pk)
        reason = request.POST.get("reason", "")
        if not reason.strip():
            messages.error(request, "Cần nhập lý do từ chối.")
            return redirect("ui_modern:approval_detail", pk=pk)
        ApprovalService.reject(req, request.user, reason)
        messages.warning(request, "Đã từ chối yêu cầu.")
        return redirect("ui_modern:approval_queue")


class ApprovalRuleListView(LoginRequiredMixin, ListView):
    """List all approval rules (admin only)."""

    template_name = "modern/approvals/rule_list.html"
    context_object_name = "rules"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = (
            getattr(self.request, "current_company", None) or Company.objects.first()
        )
        return ApprovalRule.objects.filter(company=company).order_by(
            "voucher_type", "min_amount"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Quy tắc phê duyệt"
        return ctx
