"""Approval workflow service.

ApprovalService.submit() creates a request + steps based on rule.
ApprovalService.approve()/reject() advances through the chain.
When final step approved, fires hook on target object (e.g. auto-post voucher).
"""

from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.notifications.services import NotificationService

from .models import ApprovalRequest, ApprovalRule, ApprovalStep


class NoApprovalRuleError(Exception):
    """Raised when no rule matches but approval was requested."""


class ApprovalService:
    """Manage approval workflow for any object."""

    @staticmethod
    def get_rule(company, voucher_type, amount):
        """Find the rule matching this voucher_type and amount range."""
        amount = Decimal(str(amount or 0))
        return (
            ApprovalRule.objects.filter(
                company=company,
                voucher_type=voucher_type,
                is_active=True,
                min_amount__lte=amount,
                max_amount__gte=amount,
            )
            .order_by("-min_amount")
            .first()
        )

    @staticmethod
    def is_approval_required(company, voucher_type, amount):
        """Check if approval is needed before this object can be posted."""
        return ApprovalService.get_rule(company, voucher_type, amount) is not None

    @classmethod
    def submit(cls, *, obj, voucher_type, amount, requested_by, label=None):
        """Create an approval request + steps. Returns the request."""
        from apps.core.models import Company

        company = getattr(obj, "company", None) or Company.objects.first()
        if not company:
            raise ValueError("Object has no company and no company in DB")

        rule = cls.get_rule(company, voucher_type, amount)
        if not rule:
            raise NoApprovalRuleError(
                f"No approval rule for {voucher_type} amount {amount}"
            )

        ct = ContentType.objects.get_for_model(obj)

        # Cancel any prior pending requests for same object
        ApprovalRequest.objects.filter(
            content_type=ct, object_id=obj.id, status=ApprovalRequest.Status.PENDING,
        ).update(status=ApprovalRequest.Status.CANCELLED, completed_at=timezone.now())

        label = label or str(obj)
        request = ApprovalRequest.objects.create(
            company=company,
            content_type=ct,
            object_id=obj.id,
            object_label=label,
            voucher_type=voucher_type,
            amount=Decimal(str(amount)),
            requested_by=requested_by,
            status=ApprovalRequest.Status.PENDING,
        )

        # Build the step chain
        for seq, role_code in enumerate(rule.approver_roles, 1):
            ApprovalStep.objects.create(
                request=request,
                sequence=seq,
                role_required=role_code,
            )

        cls._notify_next_approver(request)
        return request

    @classmethod
    def approve(cls, request, user, note=""):
        """Approve the current step. Auto-advance to next or finalize."""
        current_step = (
            request.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        if not current_step:
            return request  # already done

        current_step.status = ApprovalRequest.Status.APPROVED
        current_step.approved_by = user
        current_step.acted_at = timezone.now()
        current_step.note = note
        current_step.save()

        next_step = (
            request.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        if next_step:
            cls._notify_next_approver(request)
            return request

        # Final step approved — finalize request + fire hook
        request.status = ApprovalRequest.Status.APPROVED
        request.completed_at = timezone.now()
        request.save()
        cls._fire_approval_hook(request)
        cls._notify_submitter(request, approved=True)
        return request

    @classmethod
    def reject(cls, request, user, reason=""):
        """Reject the request — blocks all future steps."""
        current_step = (
            request.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        if current_step:
            current_step.status = ApprovalRequest.Status.REJECTED
            current_step.approved_by = user
            current_step.acted_at = timezone.now()
            current_step.note = reason
            current_step.save()

        request.status = ApprovalRequest.Status.REJECTED
        request.rejection_reason = reason
        request.completed_at = timezone.now()
        request.save()
        cls._notify_submitter(request, approved=False)
        return request

    @staticmethod
    def _notify_next_approver(request):
        next_step = (
            request.steps.filter(status=ApprovalRequest.Status.PENDING)
            .order_by("sequence")
            .first()
        )
        if not next_step:
            return
        NotificationService.send_to_role(
            role_code=next_step.role_required,
            company=request.company,
            type="approval",
            title=f"Cần phê duyệt: {request.object_label}",
            message=(
                f"Yêu cầu duyệt {request.voucher_type} giá trị "
                f"{request.amount:,.0f} VND đang chờ bạn phê duyệt "
                f"(bước {next_step.sequence}/{request.steps.count()})."
            ),
            url=f"/modern/approvals/{request.id}/",
            related_object_type="approvals.approvalrequest",
            related_object_id=request.id,
        )

    @staticmethod
    def _notify_submitter(request, approved):
        if not request.requested_by:
            return
        NotificationService.send(
            user=request.requested_by,
            company=request.company,
            type="success" if approved else "error",
            title=(
                f"Đã duyệt: {request.object_label}"
                if approved
                else f"Từ chối: {request.object_label}"
            ),
            message=(
                f"Yêu cầu phê duyệt {request.voucher_type} của bạn đã được DUYỆT."
                if approved
                else f"Yêu cầu phê duyệt {request.voucher_type} của bạn bị TỪ CHỐI. "
                f"Lý do: {request.rejection_reason}"
            ),
            url=f"/modern/approvals/{request.id}/",
        )

    @staticmethod
    def _fire_approval_hook(request):
        """Hook: auto-post voucher after final approval."""
        try:
            obj = request.content_type.get_object_for_object_type(pk=request.object_id)
        except Exception:
            return

        # Generic hook for vouchers
        if request.content_type.app_label == "ledger" and request.content_type.model == "accountingvoucher":
            from apps.ledger.services.voucher_posting_service import VoucherPostingService

            try:
                VoucherPostingService().post(obj)
            except Exception:
                pass  # Already posted or other issue

    @staticmethod
    def pending_for_user(user, company):
        """Get all requests awaiting action by this user."""
        from apps.identity.models import UserCompanyRole

        # Roles this user has
        user_roles = UserCompanyRole.objects.filter(
            user=user, company=company
        ).values_list("role__code", flat=True)

        request_ids = ApprovalStep.objects.filter(
            status=ApprovalRequest.Status.PENDING,
            role_required__in=list(user_roles),
        ).values_list("request_id", flat=True)

        return ApprovalRequest.objects.filter(
            id__in=request_ids,
            company=company,
            status=ApprovalRequest.Status.PENDING,
        ).order_by("-created_at")
