"""FixedAsset model — handles both TSCĐ and CCDC."""

from decimal import Decimal

from django.db import models

from apps.core.managers import CompanyOwnedModel


class FixedAsset(CompanyOwnedModel):
    """Asset (TSCĐ or CCDC). Use is_tool=True for CCDC."""

    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = "straight_line", "Đường thẳng"
        DECLINING_BALANCE = "declining_balance", "Số dư giảm dần"
        UNITS_OF_PRODUCTION = "units_of_production", "Theo sản lượng"

    class Status(models.TextChoices):
        DRAFT = "draft", "Lưu tạm"
        ACTIVE = "active", "Đang dùng"
        FULLY_DEPRECIATED = "fully_depreciated", "Đã khấu hao hết"
        DISPOSED = "disposed", "Đã thanh lý"

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="fixed_assets",
        db_index=True,
    )
    asset_code = models.CharField(max_length=50)
    asset_name = models.CharField(max_length=255)
    asset_name_en = models.CharField(max_length=255, blank=True, default="")

    category = models.ForeignKey(
        "assets.AssetCategory",
        on_delete=models.PROTECT,
        related_name="assets",
    )
    using_department = models.ForeignKey(
        "assets.AssetUsingDepartment",
        on_delete=models.PROTECT,
        related_name="assets",
    )

    # GL accounts
    gl_account = models.CharField(
        max_length=20, help_text="TK tài sản (211/212/213 cho TSCĐ, 142/242 cho CCDC)"
    )
    depreciation_account = models.CharField(
        max_length=20, help_text="TK hao mòn/lũy kế (2141/2142/2143 cho TSCĐ, 142/242 cho CCDC)"
    )
    expense_account = models.CharField(
        max_length=20, default="642", help_text="TK chi phí (641/642/635)"
    )

    # Cost & depreciation
    original_cost = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="VND")

    depreciation_method = models.CharField(
        max_length=30,
        choices=DepreciationMethod.choices,
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    depreciation_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
        help_text="Tỷ lệ KH/năm (vd 0.20 = 20%/năm)",
    )
    useful_life_months = models.PositiveSmallIntegerField(default=0)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salvage_value = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    accumulated_depreciation = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=0,
    )

    # Flag
    is_tool = models.BooleanField(
        default=False, help_text="TRUE=CCDC (TK 142/242), FALSE=TSCĐ (TK 211/214)"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "fixed_asset"
        unique_together = [("company", "asset_code")]
        ordering = ["asset_code"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "is_tool"]),
        ]

    def __str__(self):
        return f"{self.asset_code} - {self.asset_name}"

    @property
    def net_book_value(self) -> Decimal:
        return self.original_cost - self.accumulated_depreciation

    def calculate_monthly_depreciation(self) -> Decimal:
        """Compute depreciation for one month (straight-line only for now)."""
        if self.status != self.Status.ACTIVE:
            return Decimal("0")
        if self.depreciation_method != self.DepreciationMethod.STRAIGHT_LINE:
            # Other methods not implemented in Phase 3
            return Decimal("0")

        # Annual depreciation / 12
        annual = self.original_cost * self.depreciation_rate
        monthly = (annual / Decimal("12")).quantize(Decimal("0.0001"))

        # Don't exceed net book value
        remaining = self.original_cost - self.accumulated_depreciation - self.salvage_value
        if monthly > remaining:
            monthly = remaining
        if monthly < 0:
            monthly = Decimal("0")

        return monthly
