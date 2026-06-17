"""Customer and Vendor master data."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Customer(CompanyOwnedModel):
    """Customer (khách hàng) — receivable party."""

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="customers",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, default="")
    short_name = models.CharField(max_length=100, blank=True, default="")
    tax_code = models.CharField(max_length=20, blank=True, default="", db_index=True)
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    customer_group_code = models.CharField(max_length=50, blank=True, default="")
    sales_staff_code = models.CharField(max_length=50, blank=True, default="")
    payment_terms = models.CharField(max_length=100, blank=True, default="")
    credit_limit = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")
    default_vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    gl_account_receivable = models.CharField(max_length=20, default="131")

    is_supplier = models.BooleanField(default=False, help_text="Also a vendor?")
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "customer"
        unique_together = [("company", "code")]
        ordering = ["code"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["tax_code"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Vendor(CompanyOwnedModel):
    """Vendor (nhà cung cấp) — payable party."""

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="vendors",
        db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, default="")
    short_name = models.CharField(max_length=100, blank=True, default="")
    tax_code = models.CharField(max_length=20, blank=True, default="", db_index=True)
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    vendor_group_code = models.CharField(max_length=50, blank=True, default="")
    payment_terms = models.CharField(max_length=100, blank=True, default="")
    currency_code = models.CharField(max_length=3, default="VND")
    gl_account_payable = models.CharField(max_length=20, default="331")

    is_supplier = models.BooleanField(default=True)
    is_contractor = models.BooleanField(default=False, help_text="Cung cấp dịch vụ?")
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "vendor"
        unique_together = [("company", "code")]
        ordering = ["code"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["tax_code"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
