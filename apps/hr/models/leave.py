"""Leave records and balances."""

from django.db import models


class LeaveRecord(models.Model):
    """Đơn nghỉ phép / ốm đau / thai sản."""

    class LeaveType(models.TextChoices):
        ANNUAL = "annual", "Nghỉ phép năm"
        SICK = "sick", "Nghỉ ốm đau"
        MATERNITY = "maternity", "Thai sản"
        MARRIAGE = "marriage", "Kết hôn"
        FUNERAL = "funeral", "Tang chế"
        UNPAID = "unpaid", "Nghỉ không lương"

    class Status(models.TextChoices):
        PENDING = "pending", "Chờ duyệt"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Từ chối"

    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="leave_records",
    )
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    maternity_months = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_leave_record"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.employee.code} {self.leave_type} {self.days}d"


class LeaveBalance(models.Model):
    """Số dư ngày phép theo năm tài chính."""

    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    fiscal_year = models.SmallIntegerField()
    standard_days = models.DecimalField(max_digits=5, decimal_places=2, default=12)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    objects = models.Manager()

    class Meta:
        db_table = "hr_leave_balance"
        unique_together = [("employee", "fiscal_year")]

    @property
    def remaining_days(self):
        return self.standard_days + self.carried_forward - self.used_days

    def __str__(self):
        return f"{self.employee.code} FY{self.fiscal_year}: {self.remaining_days}d"
