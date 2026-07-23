"""CRM models — leads, accounts, contacts, opportunities, activities, tickets, campaigns."""

from decimal import Decimal

from django.db import models

from apps.core.managers import CompanyOwnedModel


class CRMLead(CompanyOwnedModel):
    """Sales lead — potential customer."""

    class LeadSource(models.TextChoices):
        WEBSITE = "website", "Website"
        REFERRAL = "referral", "Giới thiệu"
        CAMPAIGN = "campaign", "Chiến dịch"
        COLD_CALL = "cold_call", "Gọi điện"
        EVENT = "event", "Sự kiện"
        OTHER = "other", "Khác"

    class LeadStatus(models.TextChoices):
        NEW = "new", "Mới"
        CONTACTED = "contacted", "Đã liên hệ"
        QUALIFIED = "qualified", "Đủ điều kiện"
        CONVERTED = "converted", "Đã chuyển đổi"
        REJECTED = "rejected", "Từ chối"

    code = models.CharField(max_length=50, blank=True, default="")
    full_name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    mobile = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    tax_code = models.CharField(max_length=20, blank=True, default="")
    source = models.CharField(max_length=20, choices=LeadSource.choices, default=LeadSource.OTHER)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)
    assigned_to = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    description = models.TextField(blank=True, default="")
    converted_account = models.ForeignKey(
        "crm.CRMAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_leads",
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_lead"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.company_name})"


class CRMAccount(CompanyOwnedModel):
    """Organization/account — linked to Customer when converted."""

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    tax_code = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")

    customer = models.ForeignKey(
        "master_data.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_accounts",
    )
    assigned_to = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_accounts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_account"
        unique_together = [("company", "code")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class CRMContact(CompanyOwnedModel):
    """Person at an account."""

    account = models.ForeignKey(
        CRMAccount, on_delete=models.CASCADE, related_name="contacts", null=True, blank=True
    )
    full_name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    mobile = models.CharField(max_length=50, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    is_decision_maker = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_contact"
        ordering = ["-is_primary", "full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.account})"


class Opportunity(CompanyOwnedModel):
    """Sales opportunity/deal in pipeline."""

    class Stage(models.TextChoices):
        PROSPECTING = "prospecting", "Tìm kiếm (10%)"
        QUALIFICATION = "qualification", "Đánh giá (25%)"
        PROPOSAL = "proposal", "Báo giá (50%)"
        NEGOTIATION = "negotiation", "Đàm phán (75%)"
        WON = "won", "Thắng (100%)"
        LOST = "lost", "Thua (0%)"

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    account = models.ForeignKey(
        CRMAccount,
        on_delete=models.PROTECT,
        related_name="opportunities",
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        CRMContact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )

    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.PROSPECTING)
    probability = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10"))

    estimated_value = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency_code = models.CharField(max_length=3, default="VND")

    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)

    assigned_to = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_opportunities",
    )

    description = models.TextField(blank=True, default="")
    loss_reason = models.TextField(blank=True, default="")

    created_contract_id = models.BigIntegerField(null=True, blank=True)
    created_project_id = models.BigIntegerField(null=True, blank=True)
    created_invoice_id = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_opportunity"
        unique_together = [("company", "code")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def weighted_value(self):
        return (self.estimated_value * self.probability / 100).quantize(Decimal("1"))


class OpportunityLine(models.Model):
    """Product/service line in an opportunity."""

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="lines")
    line_no = models.PositiveSmallIntegerField()
    product = models.ForeignKey(
        "master_data.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.CharField(max_length=500, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.08"))
    amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    class Meta:
        db_table = "crm_opportunity_line"
        ordering = ["line_no"]

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Activity(CompanyOwnedModel):
    """CRM activity — calls, meetings, emails, tasks."""

    class ActivityType(models.TextChoices):
        CALL = "call", "Gọi điện"
        MEETING = "meeting", "Họp"
        EMAIL = "email", "Email"
        TASK = "task", "Nhiệm vụ"
        NOTE = "note", "Ghi chú"
        VISIT = "visit", "Thăm khách"

    class Status(models.TextChoices):
        PLANNED = "planned", "Lên kế hoạch"
        IN_PROGRESS = "in_progress", "Đang thực hiện"
        COMPLETED = "completed", "Hoàn thành"
        CANCELLED = "cancelled", "Đã hủy"

    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    subject = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    lead = models.ForeignKey(
        CRMLead, on_delete=models.CASCADE, null=True, blank=True, related_name="activities"
    )
    account = models.ForeignKey(
        CRMAccount,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    ticket = models.ForeignKey(
        "crm.Ticket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )

    assigned_to = models.ForeignKey(
        "identity.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_activity"
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.activity_type}: {self.subject}"


class Ticket(CompanyOwnedModel):
    """Customer support ticket."""

    class Priority(models.TextChoices):
        LOW = "low", "Thấp"
        NORMAL = "normal", "Bình thường"
        HIGH = "high", "Cao"
        URGENT = "urgent", "Khẩn cấp"

    class Status(models.TextChoices):
        OPEN = "open", "Mở"
        IN_PROGRESS = "in_progress", "Đang xử lý"
        RESOLVED = "resolved", "Đã giải quyết"
        CLOSED = "closed", "Đã đóng"

    code = models.CharField(max_length=50)
    subject = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")

    customer_code = models.CharField(max_length=50, blank=True, default="")
    customer_name = models.CharField(max_length=255, blank=True, default="")
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")

    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    assigned_to = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    related_opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_ticket"
        unique_together = [("company", "code")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code}: {self.subject}"


class TicketResponse(models.Model):
    """Response to a support ticket."""

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="responses")
    author = models.ForeignKey("identity.User", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_ticket_response"
        ordering = ["created_at"]


class Campaign(CompanyOwnedModel):
    """Marketing campaign."""

    class CampaignType(models.TextChoices):
        EMAIL = "email", "Email marketing"
        SOCIAL = "social", "Mạng xã hội"
        EVENT = "event", "Sự kiện"
        WEBINAR = "webinar", "Webinar"
        ADS = "ads", "Quảng cáo"
        OTHER = "other", "Khác"

    class Status(models.TextChoices):
        DRAFT = "draft", "Lưu nháp"
        ACTIVE = "active", "Đang chạy"
        PAUSED = "paused", "Tạm dừng"
        COMPLETED = "completed", "Hoàn thành"

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    campaign_type = models.CharField(
        max_length=20, choices=CampaignType.choices, default=CampaignType.EMAIL
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    budget = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    actual_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_campaign"
        unique_together = [("company", "code")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class CampaignMember(models.Model):
    """Lead/contact in a campaign."""

    class Response(models.TextChoices):
        SENT = "sent", "Đã gửi"
        OPENED = "opened", "Đã mở"
        CLICKED = "clicked", "Đã click"
        REPLIED = "replied", "Đã phản hồi"
        CONVERTED = "converted", "Đã chuyển đổi"
        BOUNCED = "bounced", "Bounce"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="members")
    lead = models.ForeignKey(
        CRMLead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="campaign_memberships",
    )
    contact = models.ForeignKey(
        CRMContact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="campaign_memberships",
    )
    response_status = models.CharField(
        max_length=20, choices=Response.choices, default=Response.SENT
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_campaign_member"
        unique_together = [("campaign", "lead"), ("campaign", "contact")]
