"""TaxRateCode model — hệ thống mã thuế GTGT theo TT78/2021."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TaxRateCode(models.Model):
    """Mã thuế GTGT theo Thông tư 78/2021/TT-BTC.

    Codes: 00 (0%), 05 (5%), 04 (5% hàng dịch vụ), 10 (10%), 08 (10% đặc biệt),
    KT (không chịu thuế), TS05 (TS tính 5%), kht (không tính).
    """

    code = models.CharField(max_length=10, unique=True, primary_key=True)
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Tỷ lệ thuế GTGT (%)",
    )
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "master_data_taxratecode"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} ({self.rate}%)"
