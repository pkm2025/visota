"""Contract and Minutes models — Hợp đồng và Biên bản."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Contract(CompanyOwnedModel):
    """Hợp đồng — sale/purchase/service/construction/labor/lease/other."""

    class ContractType(models.TextChoices):
        SALE = "sale", "Hợp đồng mua bán"
        PURCHASE = "purchase", "Hợp đồng mua hàng"
        SERVICE = "service", "Hợp đồng cung cấp dịch vụ"
        CONSTRUCTION = "construction", "Hợp đồng thi công"
        LABOR = "labor", "Hợp đồng lao động"
        LEASE = "lease", "Hợp đồng thuê"
        # --- Bidding Law 22/2023/QH15 ---
        BIDDING_LUMP_SUM = "bidding_lump_sum", "Hợp đồng đấu thầu trọn gói"
        BIDDING_UNIT_PRICE = "bidding_unit_price", "Hợp đồng đấu thầu đơn giá điều chỉnh"
        BIDDING_CONSULTING = "bidding_consulting", "Hợp đồng tư vấn đấu thầu"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        DRAFT = "draft", "Dự thảo"
        ACTIVE = "active", "Đang hiệu lực"
        COMPLETED = "completed", "Hoàn thành"
        CANCELLED = "cancelled", "Đã hủy"

    contract_no = models.CharField(max_length=50)
    contract_date = models.DateField()
    contract_type = models.CharField(
        max_length=20,
        choices=ContractType.choices,
        default=ContractType.OTHER,
    )
    party_code = models.CharField(max_length=50, blank=True, default="")
    party_name = models.CharField(max_length=255)
    party_tax_code = models.CharField(max_length=20, blank=True, default="")
    party_address = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    value = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    signed_file = models.FileField(
        upload_to="contracts/",
        null=True,
        blank=True,
    )
    linked_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contract"
        unique_together = [("company", "contract_no")]
        indexes = [
            models.Index(fields=["company", "contract_type"]),
            models.Index(fields=["company", "status"]),
        ]
        ordering = ["-contract_date", "-id"]

    def __str__(self):
        return f"{self.contract_no} ({self.party_name})"


class ContractTemplate(CompanyOwnedModel):
    """Pre-built contract template with standard clauses.

    Company-scoped (multi-tenant) via :class:`CompanyOwnedModel`. The
    ``code`` is unique within a company, not globally — use
    ``(company, code)`` lookups instead of ``code`` alone.
    """

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    contract_type = models.CharField(
        max_length=20
    )  # labor_fixed, labor_indefinite, labor_probation, sale, purchase, service, construction
    template_html = models.TextField()  # Django template HTML for PDF
    required_fields = models.JSONField(default=list)  # ['employee_name', 'salary', ...]
    is_active = models.BooleanField(default=True)
    legal_basis = models.TextField(blank=True, default="")
    version = models.CharField(max_length=20, default="2026")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contract_template"
        unique_together = [("company", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Minutes(CompanyOwnedModel):
    """Biên bản — handover/acceptance/inventory/liquidation/reconciliation/etc."""

    class MinutesType(models.TextChoices):
        HANDOVER = "handover", "Biên bản bàn giao"
        ACCEPTANCE = "acceptance", "Biên bản nghiệm thu"
        INVENTORY = "inventory", "Biên bản kiểm kê"
        LIQUIDATION = "liquidation", "Biên bản thanh lý"
        RECONCILIATION = "reconciliation", "Biên bản đối chiếu"
        ADJUSTMENT = "adjustment", "Biên bản điều chỉnh"
        OTHER = "other", "Biên bản khác"

    minutes_no = models.CharField(max_length=50)
    minutes_date = models.DateField()
    minutes_type = models.CharField(
        max_length=20,
        choices=MinutesType.choices,
        default=MinutesType.OTHER,
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="minutes_set",
    )
    party_code = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    signed_file = models.FileField(
        upload_to="minutes/",
        null=True,
        blank=True,
    )
    linked_voucher = models.ForeignKey(
        "ledger.AccountingVoucher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minutes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "minutes"
        unique_together = [("company", "minutes_no")]
        indexes = [
            models.Index(fields=["company", "minutes_type"]),
            models.Index(fields=["company", "minutes_date"]),
        ]
        ordering = ["-minutes_date", "-id"]

    def __str__(self):
        return f"{self.minutes_no} ({self.get_minutes_type_display()})"
