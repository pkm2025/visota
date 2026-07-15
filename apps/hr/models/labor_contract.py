"""Labor contract and dependent models for HR module."""

from django.db import models


class LaborContract(models.Model):
    """Hợp đồng lao động — 4 types per VN Labor Code."""

    class ContractType(models.TextChoices):
        PROBATION = "probation", "Thử việc"
        FIXED_TERM = "fixed_term", "Xác định thời hạn"
        INDEFINITE = "indefinite", "Không xác định thời hạn"
        SEASONAL = "seasonal", "Mùa vụ / Công việc cụ thể"

    class Status(models.TextChoices):
        DRAFT = "draft", "Lưu nháp"
        ACTIVE = "active", "Đang hiệu lực"
        EXPIRED = "expired", "Đã hết hạn"
        TERMINATED = "terminated", "Đã chấm dứt"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="labor_contracts",
        db_index=True,
    )
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="labor_contracts",
    )
    contract_no = models.CharField(max_length=50)
    contract_type = models.CharField(max_length=20, choices=ContractType.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)

    salary_base = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    salary_gross = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    allowance_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")

    insurance_salary_base = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    join_insurance = models.BooleanField(default=True)

    position_title = models.CharField(max_length=255, blank=True, default="")
    department = models.ForeignKey(
        "hr.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="labor_contracts",
    )
    work_location = models.CharField(max_length=255, blank=True, default="")

    signing_date = models.DateField(null=True, blank=True)
    signed_file = models.FileField(upload_to="contracts/labor/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_labor_contract"
        unique_together = [("company", "contract_no")]
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.contract_no} ({self.employee.code})"


class Dependent(models.Model):
    """Người phụ thuộc — giảm trừ gia cảnh 6.2M/người (NQ 110/2025)."""

    class Relationship(models.TextChoices):
        SPOUSE = "spouse", "Vợ/Chồng"
        CHILD = "child", "Con"
        FATHER = "father", "Cha"
        MOTHER = "mother", "Mẹ"
        OTHER = "other", "Khác"

    class RegistrationStatus(models.TextChoices):
        PENDING = "pending", "Chờ đăng ký"
        REGISTERED = "registered", "Đã đăng ký"
        CANCELLED = "cancelled", "Đã hủy"

    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="dependents",
    )
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    birth_date = models.DateField(null=True, blank=True)
    id_card_no = models.CharField(max_length=20, blank=True, default="")
    tax_code = models.CharField(max_length=20, blank=True, default="")
    deduction_amount = models.DecimalField(max_digits=20, decimal_places=4, default=6200000)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_dependent"
        ordering = ["-valid_from"]

    def __str__(self):
        return f"{self.employee.code}: {self.full_name} ({self.relationship})"

    @property
    def is_active(self):
        """A dependent is active for PIT deduction if registered and in validity window."""
        from datetime import date

        today = date.today()
        if self.valid_to and self.valid_to < today:
            return False
        return self.valid_from <= today and self.registration_status == "registered"
