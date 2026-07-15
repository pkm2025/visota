"""InvoiceGroup model — nhóm hóa đơn theo TT133/ND 254/2026."""

from django.db import models


class InvoiceGroup(models.Model):
    """Nhóm hóa đơn GTGT.

    - #4 INPUT (Hóa đơn đầu vào): TK nợ 1331, TK có 331
    - #5 OUTPUT (Hóa đơn đầu ra): TK nợ 131, TK có 33311 (or 511)
    - #6 OTHER (Khác)
    """

    code = models.CharField(max_length=10, unique=True, primary_key=True)
    name_vi = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    default_tax_account_debit = models.CharField(max_length=20, blank=True)
    default_tax_account_credit = models.CharField(max_length=20, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "master_data_invoicegroup"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name_vi}"
