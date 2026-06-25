"""Bank guarantee models.

BankGuarantee: bid bond / performance bond / advance payment bond / warranty bond.
Auto-creates voucher N244 / C112 on issue + reversal on release.
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class BankGuarantee(CompanyOwnedModel):
    class GuaranteeType(models.TextChoices):
        BID_BOND = "bid_bond", "Bảo lãnh dự thầu"
        PERFORMANCE = "performance", "Bảo lãnh thực hợp đồng"
        ADVANCE_PAYMENT = "advance_payment", "Bảo lãnh ứng trước"
        WARRANTY = "warranty", "Bảo lãnh bảo hành"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        DRAFT = "draft", "Dự thảo"
        ACTIVE = "active", "Hiệu lực"
        RELEASED = "released", "Đã giải chấp"
        EXPIRED = "expired", "Quá hạn"
        CANCELLED = "cancelled", "Đã hủy"

    guarantee_no = models.CharField(max_length=50)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    guarantee_type = models.CharField(
        max_length=20, choices=GuaranteeType.choices, default=GuaranteeType.PERFORMANCE
    )
    bank_account = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    currency_code = models.CharField(max_length=3, default="VND")
    beneficiary_name = models.CharField(max_length=255)
    beneficiary_tax_code = models.CharField(max_length=20, blank=True, default="")
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="guarantees",
    )
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    released_at = models.DateField(null=True, blank=True)
    margin_deposit_account = models.CharField(max_length=20, default="244")  # TK 244
    fee_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    gl_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="guarantees_issued",
    )
    release_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="guarantees_released",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_guarantee"
        unique_together = [("company", "guarantee_no")]
        ordering = ["-issue_date", "-id"]

    def __str__(self):
        return f"{self.guarantee_no} — {self.beneficiary_name} ({self.amount:,.0f})"

    @property
    def days_to_expiry(self):
        from datetime import date as date_cls

        return (self.expiry_date - date_cls.today()).days if self.expiry_date else None
