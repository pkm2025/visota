"""Asset categories and using departments."""
from django.db import models
from apps.core.managers import CompanyOwnedModel


class AssetCategory(CompanyOwnedModel):
    """Asset category (loại/nhóm/phân nhóm) — applies to both TSCĐ and CCDC."""

    class Level(models.TextChoices):
        TYPE = 'type', 'Loại'
        GROUP = 'group', 'Nhóm'
        SUBGROUP = 'subgroup', 'Phân nhóm'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='asset_categories', db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    level = models.CharField(max_length=20, choices=Level.choices)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children',
    )

    is_for_tool = models.BooleanField(default=False,
        help_text='TRUE=CCDC (TK 142/242), FALSE=TSCĐ (TK 211/214)')

    default_gl_account = models.CharField(max_length=20, blank=True, default='')
    default_depreciation_account = models.CharField(max_length=20, blank=True, default='')
    default_expense_account = models.CharField(max_length=20, blank=True, default='')
    default_depreciation_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
    )
    default_useful_life_months = models.PositiveSmallIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'asset_category'
        unique_together = [('company', 'code')]
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class AssetUsingDepartment(CompanyOwnedModel):
    """Department that uses an asset (for expense allocation)."""

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='asset_departments', db_index=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    default_expense_account = models.CharField(max_length=20, default='642')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'asset_using_department'
        unique_together = [('company', 'code')]
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'
