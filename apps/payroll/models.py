"""Payroll models: AttendanceRecord, PayrollRun, PayrollLine."""

from django.db import models


class AttendanceRecord(models.Model):
    """Daily attendance for an employee."""

    class Status(models.TextChoices):
        PRESENT = "present", "Có mặt"
        LATE = "late", "Đi trễ"
        EARLY_LEAVE = "early_leave", "Về sớm"
        ABSENT = "absent", "Vắng"
        LEAVE = "leave", "Nghỉ phép"
        HOLIDAY = "holiday", "Nghỉ lễ"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        db_index=True,
    )
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    attendance_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    work_days = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.CharField(max_length=500, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "attendance_record"
        unique_together = [("employee", "attendance_date")]
        ordering = ["-attendance_date"]
        indexes = [
            models.Index(fields=["company", "attendance_date"]),
        ]

    def __str__(self):
        return f"{self.employee.code} {self.attendance_date}: {self.status}"


class PayrollRun(models.Model):
    """Monthly payroll run for a company."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Lưu tạm"
        CALCULATED = "calculated", "Đã tính"
        POSTED = "posted", "Đã ghi sổ"
        PAID = "paid", "Đã trả lương"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="payroll_runs",
        db_index=True,
    )
    period = models.CharField(max_length=7, help_text="YYYY-MM")
    fiscal_year = models.SmallIntegerField()
    period_num = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    total_gross = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_pit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_net = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_runs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "payroll_run"
        unique_together = [("company", "period")]
        ordering = ["-period"]

    def __str__(self):
        return f"Payroll {self.period}"


class PayrollLine(models.Model):
    """Per-employee payroll calculation."""

    run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.PROTECT,
        related_name="payroll_lines",
    )
    line_no = models.PositiveSmallIntegerField(default=1)

    work_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    base_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    allowance_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    overtime_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    gross_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Insurance — employee portion (deducted from gross)
    social_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    health_insurance_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    unemployment_insurance_employee = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )

    # Insurance — employer portion (additional cost)
    social_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    health_insurance_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    unemployment_insurance_employer = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )

    pit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    net_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    objects = models.Manager()

    class Meta:
        db_table = "payroll_line"
        unique_together = [("run", "employee")]
        ordering = ["line_no"]

    def __str__(self):
        return f"{self.employee.code}: gross={self.gross_salary} net={self.net_salary}"
