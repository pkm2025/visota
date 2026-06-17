"""AssetDepreciation — history of depreciation per period."""

from django.db import models


class AssetDepreciation(models.Model):
    """Depreciation entry for one asset in one period."""

    asset = models.ForeignKey(
        "assets.FixedAsset",
        on_delete=models.CASCADE,
        related_name="depreciation_history",
    )
    period = models.CharField(max_length=7, help_text="YYYY-MM format")
    depreciation_amount = models.DecimalField(max_digits=20, decimal_places=4)
    accumulated_depreciation_end = models.DecimalField(max_digits=20, decimal_places=4)
    net_book_value_end = models.DecimalField(max_digits=20, decimal_places=4)

    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_depreciations",
    )
    posted_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        db_table = "asset_depreciation"
        unique_together = [("asset", "period")]
        ordering = ["-period"]

    def __str__(self):
        return f"{self.asset.asset_code} P{self.period}: {self.depreciation_amount}"
