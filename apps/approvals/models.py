"""Approval models — generic multi-step workflow.

ApprovalRule: per voucher_type + threshold → list of approver roles.
ApprovalRequest: pending/approved/rejected request with steps.
ApprovalStep: per-step audit trail.
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class ApprovalRule(CompanyOwnedModel):
    """When this voucher type & threshold hit, send through these approvers."""

    voucher_type = models.CharField(max_length=30)
    min_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    max_amount = models.DecimalField(
        max_digits=20, decimal_places=4, default=999999999999
    )
    approver_roles = models.JSONField(default=list)
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "approval_rule"
        unique_together = [("company", "voucher_type", "min_amount")]

    def __str__(self):
        return (
            f"{self.voucher_type} "
            f"[{self.min_amount:,.0f} - {self.max_amount:,.0f}] "
            f"→ {','.join(self.approver_roles)}"
        )


class ApprovalRequest(models.Model):
    """A pending/approved/rejected approval request."""

    class Status(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"
        CANCELLED = "cancelled", "Đã hủy"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField()
    # Cached info for quick display without joins
    object_label = models.CharField(max_length=255)
    voucher_type = models.CharField(max_length=30, blank=True, default="")
    amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_requests_submitted",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "approval_request"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.object_label} ({self.amount:,.0f})"


class ApprovalStep(models.Model):
    """One approval step in the chain."""

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sequence = models.PositiveSmallIntegerField()
    role_required = models.CharField(max_length=50)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_steps_assigned",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_steps_done",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalRequest.Status.choices,
        default=ApprovalRequest.Status.PENDING,
    )
    note = models.TextField(blank=True, default="")
    acted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approval_step"
        ordering = ["sequence"]
        unique_together = [("request", "sequence")]

    def __str__(self):
        return f"Step {self.sequence} of req#{self.request_id} ({self.status})"
