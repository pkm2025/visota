"""Notification model + EmailLog."""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class Notification(models.Model):
    """User notification — visible in bell dropdown + dedicated inbox."""

    class Type(models.TextChoices):
        INFO = "info", "Thông tin"
        SUCCESS = "success", "Thành công"
        WARNING = "warning", "Cảnh báo"
        ERROR = "error", "Lỗi"
        APPROVAL = "approval", "Yêu cầu duyệt"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "Trong ứng dụng"
        EMAIL = "email", "Email"
        BOTH = "both", "Cả hai"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    title = models.CharField(max_length=255)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True, default="")
    related_object_type = models.CharField(max_length=100, blank=True, default="")
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
            models.Index(fields=["company", "type"]),
        ]

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user.username}"

    @property
    def icon(self):
        return {
            "info": "bi-info-circle text-info",
            "success": "bi-check-circle text-success",
            "warning": "bi-exclamation-triangle text-warning",
            "error": "bi-x-circle text-danger",
            "approval": "bi-clipboard-check text-primary",
        }.get(self.type, "bi-bell")


class EmailLog(models.Model):
    """Audit log of every email sent by the system."""

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    from_email = models.CharField(max_length=255)
    to_emails = models.TextField()  # comma-separated
    cc_emails = models.TextField(blank=True, default="")
    subject = models.CharField(max_length=500)
    body = models.TextField()
    status = models.CharField(max_length=20, default="sent")  # sent/failed
    error_message = models.TextField(blank=True, default="")
    related_object_type = models.CharField(max_length=100, blank=True, default="")
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} → {self.to_emails} [{self.status}]"
