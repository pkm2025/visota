"""Bidding models per Luật Đấu thầu 23/2023/QH15.

BidOpportunity: cơ hội đấu thầu (được mời / tự tìm).
BidDocument: gói hồ sơ dự thầu / hồ sơ mời thầu.
BidSubmission: hồ sơ dự thầu đã nộp.
BidResult: kết quả trúng thầu / trượt.
ContractorProfile: hồ sơ năng lực nhà thầu.
"""

from django.conf import settings
from django.db import models

from apps.core.managers import CompanyOwnedModel


class ContractorProfile(CompanyOwnedModel):
    """Company's contractor profile for bidding (Hồ sơ năng lực)."""

    class CapabilityLevel(models.TextChoices):
        LEVEL_I = "I", "Hạng I"
        LEVEL_II = "II", "Hạng II"
        LEVEL_III = "III", "Hạng III"
        UNRANKED = "X", "Chưa xếp hạng"

    code = models.CharField(max_length=30, default="MAIN")
    name = models.CharField(max_length=255, default="")
    legal_representative = models.CharField(max_length=255, blank=True, default="")
    tax_code = models.CharField(max_length=20, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")

    capability_level = models.CharField(
        max_length=5, choices=CapabilityLevel.choices,
        default=CapabilityLevel.UNRANKED,
    )
    fields_of_activity = models.TextField(blank=True, default="")  # Lĩnh vực HĐ
    years_in_business = models.PositiveSmallIntegerField(default=0)
    financial_capacity = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    staff_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contractor_profile"

    def __str__(self):
        return f"{self.name} (hạng {self.capability_level})"


class BidOpportunity(CompanyOwnedModel):
    """A bid opportunity — invited or unsolicited."""

    class BiddingMethod(models.TextChoices):
        OPEN = "open", "Đấu thầu rộng rãi"
        LIMITED = "limited", "Đấu thầu hạn chế"
        DIRECT = "direct", "Chỉ định thầu"
        SELF_PERFORMED = "self_performed", "Tự thực hiện"
        COMMUNITY = "community", "Đấu thầu cộng đồng"

    class Form(models.TextChoices):
        ONE_STAGE = "one_stage", "Một giai đoạn một túi hồ sơ"
        ONE_STAGE_TWO_ENVELOPES = "1s2e", "Một giai đoạn hai túi hồ sơ"
        TWO_STAGE = "two_stage", "Hai giai đoạn một túi hồ sơ"

    bid_no = models.CharField(max_length=50)
    bid_name = models.CharField(max_length=500)
    investor_name = models.CharField(max_length=255)  # Chủ đầu tư
    investor_tax_code = models.CharField(max_length=20, blank=True, default="")

    bid_method = models.CharField(
        max_length=20, choices=BiddingMethod.choices,
        default=BiddingMethod.OPEN,
    )
    bid_form = models.CharField(
        max_length=20, choices=Form.choices,
        default=Form.ONE_STAGE,
    )

    bid_type = models.CharField(max_length=30, default=" construction")  # construction/goods/services/consulting/mixed
    bid_package_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")
    duration_days = models.PositiveIntegerField(default=0)

    published_at = models.DateField(null=True, blank=True)  # Ngày đăng thông báo
    bid_submission_deadline = models.DateTimeField(null=True, blank=True)
    bid_opening_at = models.DateTimeField(null=True, blank=True)

    is_online = models.BooleanField(default=True)  # Hệ thống mạng đấu thầu quốc gia
    bid_system_ref = models.CharField(max_length=100, blank=True, default="")  # mã trên muasamcong.mpi.gov.vn

    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, default="identified")  # identified, decided_to_bid, preparing, submitted, won, lost, cancelled

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bids_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bid_opportunity"
        unique_together = [("company", "bid_no")]
        ordering = ["-bid_submission_deadline", "-id"]

    def __str__(self):
        return f"{self.bid_no} — {self.bid_name[:40]}"


class BidDocument(CompanyOwnedModel):
    """Hồ sơ mời thầu / hồ sơ dự thầu files."""

    class DocType(models.TextChoices):
        IFB = "ifb", "Hồ sơ mời thầu (HSMT)"
        PROPOSAL = "proposal", "Hồ sơ dự thầu (HSDT)"
        TECHNICAL = "technical", "Đề xuất kỹ thuật"
        FINANCIAL = "financial", "Đề xuất tài chính"
        CONTRACT_DRAFT = "contract_draft", "Dự thảo hợp đồng"
        OTHER = "other", "Khác"

    bid = models.ForeignKey(
        BidOpportunity, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(
        max_length=20, choices=DocType.choices, default=DocType.PROPOSAL
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="bidding/docs/", null=True, blank=True)
    version = models.CharField(max_length=20, default="1.0")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bid_document"


class BidSubmission(CompanyOwnedModel):
    """Submission of our bid for an opportunity."""

    bid = models.OneToOneField(
        BidOpportunity, on_delete=models.CASCADE, related_name="submission"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    bid_security_amount = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )  # Bảo đảm dự thầu
    bid_security_provider = models.CharField(max_length=100, blank=True, default="")  # bank
    proposed_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    proposed_duration_days = models.PositiveIntegerField(default=0)
    proposed_technical_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    notes = models.TextField(blank=True, default="")

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bid_submissions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bid_submission"

    def __str__(self):
        return f"Submission for {self.bid.bid_no}"


class BidResult(CompanyOwnedModel):
    """Result of bid evaluation."""

    class Outcome(models.TextChoices):
        WON = "won", "Trúng thầu"
        LOST = "lost", "Trượt thầu"
        CANCELLED = "cancelled", "Hủy bỏ"
        WAITING = "waiting", "Chờ kết quả"

    bid = models.OneToOneField(
        BidOpportunity, on_delete=models.CASCADE, related_name="result"
    )
    outcome = models.CharField(
        max_length=20, choices=Outcome.choices, default=Outcome.WAITING
    )
    awarded_at = models.DateField(null=True, blank=True)
    final_contract_value = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )
    winner_name = models.CharField(max_length=255, blank=True, default="")  # nhà thầu trúng
    loss_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    # If won, link to resulting Contract
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bid_results",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bid_result"

    def __str__(self):
        return f"{self.bid.bid_no} → {self.outcome}"
