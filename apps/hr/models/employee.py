"""HR models: Department, Position, Employee."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Department(CompanyOwnedModel):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="departments",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    manager_code = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_department"
        unique_together = [("company", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Position(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    level = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_position"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Employee(CompanyOwnedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Nam"
        FEMALE = "female", "Nữ"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        ACTIVE = "active", "Đang làm việc"
        ON_LEAVE = "on_leave", "Nghỉ phép"
        RESIGNED = "resigned", "Đã nghỉ việc"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="employees",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.MALE,
    )
    id_card_no = models.CharField(max_length=20, blank=True, default="")
    id_card_date = models.DateField(null=True, blank=True)
    id_card_place = models.CharField(max_length=255, blank=True, default="")
    personal_tax_code = models.CharField(max_length=20, blank=True, default="")
    social_insurance_no = models.CharField(max_length=20, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="employees",
    )

    hire_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)
    official_date = models.DateField(null=True, blank=True)
    leave_date = models.DateField(null=True, blank=True)

    base_salary = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    allowance = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bank_account_no = models.CharField(max_length=50, blank=True, default="")
    bank_id = models.CharField(max_length=20, blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_employee"
        unique_together = [("company", "code")]
        ordering = ["code"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.full_name}"
