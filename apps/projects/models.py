"""Project management models — Project, Phase, Resource, Transaction."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Project(CompanyOwnedModel):
    """Project — linked to a contract, tracks progress/cost/resources."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Lập kế hoạch"
        ACTIVE = "active", "Đang thực hiện"
        ON_HOLD = "on_hold", "Tạm dừng"
        COMPLETED = "completed", "Hoàn thành"
        CANCELLED = "cancelled", "Đã hủy"

    class Priority(models.TextChoices):
        LOW = "low", "Thấp"
        MEDIUM = "medium", "Trung bình"
        HIGH = "high", "Cao"
        CRITICAL = "critical", "Khẩn cấp"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="projects",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")

    # Links
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    customer_code = models.CharField(max_length=50, blank=True, default="")
    customer_name = models.CharField(max_length=255, blank=True, default="")

    # Manager
    manager = models.ForeignKey(
        "hr.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
    )

    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)

    # Budget
    budget_revenue = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    budget_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Progress (auto-calculated from phases, or manual)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "project"
        unique_together = [("company", "code")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "manager"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_overdue(self):
        from datetime import date

        if self.end_date and self.status not in ["completed", "cancelled"]:
            return date.today() > self.end_date
        return False


class ProjectPhase(models.Model):
    """Project phase/milestone — tracks progress of sub-tasks."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Chưa bắt đầu"
        IN_PROGRESS = "in_progress", "Đang thực hiện"
        COMPLETED = "completed", "Hoàn thành"
        BLOCKED = "blocked", "Bị chặn"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="phases",
    )
    sequence = models.PositiveSmallIntegerField(default=1)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)

    # Weight for progress calculation (sum of all phases = 100%)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Budget for this phase
    budget_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "project_phase"
        ordering = ["sequence"]
        unique_together = [("project", "sequence")]

    def __str__(self):
        return f"{self.project.code} - Phase {self.sequence}: {self.name}"


class ProjectResource(models.Model):
    """Resource assigned to a project — human or material."""

    class ResourceType(models.TextChoices):
        HUMAN = "human", "Nhân sự"
        MATERIAL = "material", "Vật tư/Thiết bị"
        EQUIPMENT = "equipment", "Thiết bị/Máy móc"
        SERVICE = "service", "Dịch vụ ngoài"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
    )

    # For human resources
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_assignments",
    )
    role = models.CharField(max_length=100, blank=True, default="")  # Developer, QA, PM...

    # For material resources
    product = models.ForeignKey(
        "master_data.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_usages",
    )

    # Common fields
    name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")

    # Quantity
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=1)
    unit = models.CharField(max_length=20, blank=True, default="")  # hours, days, units...

    # Cost
    unit_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    planned_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    actual_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Dates
    assigned_from = models.DateField(null=True, blank=True)
    assigned_to = models.DateField(null=True, blank=True)

    # Utilization (% of resource dedicated to this project)
    utilization = models.DecimalField(max_digits=5, decimal_places=2, default=100)

    # Phase link
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resources",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "project_resource"
        ordering = ["resource_type", "id"]

    def __str__(self):
        target = self.employee or self.product or self.name
        return f"{self.project.code} - {self.resource_type}: {target}"

    def save(self, *args, **kwargs):
        # Auto-calculate planned_cost if not set
        if not self.planned_cost and self.quantity and self.unit_cost:
            self.planned_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class ProjectTransaction(models.Model):
    """Cost/revenue transaction linked to a project.

    Auto-created from invoices, payroll, stock movements.
    """

    class TransactionType(models.TextChoices):
        REVENUE = "revenue", "Doanh thu"
        MATERIAL_COST = "material_cost", "Chi phí vật tư"
        LABOR_COST = "labor_cost", "Chi phí nhân công"
        OVERHEAD = "overhead", "Chi phí chung"
        OTHER = "other", "Khác"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )

    # Date and amount
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=4)

    # Links to source documents
    description = models.TextField(blank=True, default="")
    sales_invoice_id = models.BigIntegerField(null=True, blank=True)
    purchase_invoice_id = models.BigIntegerField(null=True, blank=True)
    voucher_id = models.BigIntegerField(null=True, blank=True)
    payroll_line_id = models.BigIntegerField(null=True, blank=True)

    # Phase link
    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Resource link (which resource consumed this cost)
    resource = models.ForeignKey(
        ProjectResource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "project_transaction"
        ordering = ["-transaction_date"]
        indexes = [
            models.Index(fields=["project", "transaction_type"]),
            models.Index(fields=["transaction_date"]),
        ]

    def __str__(self):
        return f"{self.project.code} - {self.transaction_type} - {self.amount}"
