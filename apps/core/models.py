"""Core models: Company (tenant) and branding."""

from django.core.validators import RegexValidator
from django.db import models

from .managers import CompanyQuerySet

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Color must be in hex format: #RRGGBB",
)


class Company(models.Model):
    """Tenant entity. Multi-tenant isolation via company_id column."""

    class AccountingRegime(models.TextChoices):
        TT133 = "tt133", "TT133/2016 (DN nhỏ và vừa)"
        TT200 = "tt200", "TT200/2014 (DN lớn)"
        Q48 = "q48", "QĐ48/2006 (cũ)"

    # Legal info
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    short_name = models.CharField(max_length=100, blank=True)
    tax_code = models.CharField(max_length=20, blank=True, db_index=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    legal_representative = models.CharField(max_length=255, blank=True)
    chief_accountant = models.CharField(max_length=255, blank=True)

    # Configuration
    accounting_regime = models.CharField(
        max_length=10,
        choices=AccountingRegime.choices,
        default=AccountingRegime.TT133,
    )
    default_currency = models.CharField(max_length=3, default="VND")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    # Branding
    brand_name = models.CharField(max_length=255, blank=True)
    brand_logo = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    brand_logo_dark = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    brand_favicon = models.ImageField(upload_to="brands/favicons/", null=True, blank=True)
    brand_primary_color = models.CharField(
        max_length=7, default="#2563eb", validators=[HEX_COLOR_VALIDATOR]
    )
    brand_accent_color = models.CharField(
        max_length=7, default="#16a34a", validators=[HEX_COLOR_VALIDATOR]
    )
    brand_sidebar_color = models.CharField(max_length=20, default="light")

    default_layout = models.CharField(max_length=20, default="modern")

    # White-label
    hide_pmketoan_branding = models.BooleanField(default=False)
    custom_css = models.TextField(blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyQuerySet.as_manager()

    class Meta:
        db_table = "company"
        verbose_name = "Company (Tenant)"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return self.brand_name or self.name


class LegalReference(models.Model):
    """Vietnamese legal document reference — for compliance tracking."""

    code = models.CharField(max_length=50, unique=True)  # 'TT133', 'TT99', 'TT32'
    name = models.CharField(max_length=500)
    full_name = models.TextField()
    issuing_body = models.CharField(max_length=100)  # 'Bộ Tài chính'
    issue_date = models.DateField()
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )
    status = models.CharField(max_length=20, default="active")  # active/superseded/repealed
    url = models.URLField(blank=True)
    summary = models.TextField(blank=True, default="")
    applicable_to = models.JSONField(default=list)  # ['accounting', 'hr', 'tax', 'e-invoice']
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "legal_reference"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"
