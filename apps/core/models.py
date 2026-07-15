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
        TT58 = "tt58", "TT58/2026 (DN siêu nhỏ)"

    class VatMethod(models.TextChoices):
        KHAU_TRU = "khau_tru", "Khấu trừ"
        TY_LE_PHAN_TRAM = "ty_le_phan_tram", "Tỷ lệ %"

    class TndnMethod(models.TextChoices):
        TINH_THUE = "tinh_thue", "Tính thuế"
        TY_LE_PHAN_TRAM = "ty_le_phan_tram", "Tỷ lệ %"

    class EntityType(models.TextChoices):
        DOANH_NGHIEP_SIEU_NHO = "doanh_nghiep_sieu_nho", "Doanh nghiệp siêu nhỏ"
        HO_KINH_DOANH = "ho_kinh_doanh", "Hộ kinh doanh"
        CA_NHAN_KINH_DOANH = "ca_nhan_kinh_doanh", "Cá nhân kinh doanh"

    # Tax method group labels keyed by group number (1-4).
    TAX_METHOD_GROUP_LABELS = {
        1: "Nhóm 1 — GTGT tỷ lệ % + TNDN tỷ lệ %",
        2: "Nhóm 2 — GTGT tỷ lệ % + TNDN tính thuế",
        3: "Nhóm 3 — GTGT khấu trừ + TNDN tỷ lệ %",
        4: "Nhóm 4 — GTGT khấu trừ + TNDN tính thuế",
    }

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

    # SME classification (per ND 80/2021)
    class SMESize(models.TextChoices):
        MICRO = "micro", "Siêu nhỏ"
        SMALL = "small", "Nhỏ"
        MEDIUM = "medium", "Vừa"
        LARGE = "large", "Lớn"

    # Configuration
    accounting_regime = models.CharField(
        max_length=10,
        choices=AccountingRegime.choices,
        default=AccountingRegime.TT133,
    )
    default_currency = models.CharField(max_length=3, default="VND")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)

    # TT58 tax configuration (only used when accounting_regime='tt58')
    vat_method = models.CharField(
        max_length=20,
        choices=VatMethod.choices,
        default=VatMethod.KHAU_TRU,
    )
    tndn_method = models.CharField(
        max_length=20,
        choices=TndnMethod.choices,
        default=TndnMethod.TINH_THUE,
    )
    entity_type = models.CharField(
        max_length=30,
        choices=EntityType.choices,
        default=EntityType.DOANH_NGHIEP_SIEU_NHO,
    )

    # SME classification per ND 80/2021
    sme_size = models.CharField(
        max_length=10,
        choices=SMESize.choices,
        default=SMESize.SMALL,
    )
    annual_revenue = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )  # for SME classification

    is_active = models.BooleanField(default=True)

    # Business registration
    business_license_no = models.CharField(max_length=50, blank=True, default="")
    business_license_date = models.DateField(null=True, blank=True)
    business_license_place = models.CharField(max_length=255, blank=True, default="")

    # Extended contact
    fax = models.CharField(max_length=20, blank=True, default="")
    website = models.URLField(blank=True, default="")
    representative_position = models.CharField(max_length=100, blank=True, default="")
    representative_phone = models.CharField(max_length=20, blank=True, default="")
    representative_email = models.EmailField(blank=True, default="")
    representative_id_no = models.CharField(max_length=20, blank=True, default="")
    chief_accountant_license = models.CharField(max_length=50, blank=True, default="")
    chief_accountant_phone = models.CharField(max_length=20, blank=True, default="")

    # Bank accounts (JSON: [{"bank": "VCB", "account": "...", "holder": "..."}])
    bank_accounts = models.JSONField(default=list, blank=True)

    # Social media
    facebook = models.URLField(blank=True, default="")
    linkedin = models.URLField(blank=True, default="")
    zalo = models.CharField(max_length=50, blank=True, default="")

    # Branding
    brand_name = models.CharField(max_length=255, blank=True)
    brand_logo = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    brand_logo_dark = models.ImageField(upload_to="brands/logos/", null=True, blank=True)
    brand_favicon = models.ImageField(upload_to="brands/favicons/", null=True, blank=True)
    company_stamp = models.ImageField(upload_to="brands/stamps/", null=True, blank=True)
    brand_primary_color = models.CharField(
        max_length=7, default="#2563eb", validators=[HEX_COLOR_VALIDATOR]
    )
    brand_accent_color = models.CharField(
        max_length=7, default="#16a34a", validators=[HEX_COLOR_VALIDATOR]
    )
    brand_sidebar_color = models.CharField(max_length=20, default="light")

    default_layout = models.CharField(max_length=20, default="modern")

    # White-label
    hide_visota_branding = models.BooleanField(default=False)
    custom_css = models.TextField(blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)

    # TT58 optional ledger enablement (S4a-S4d, all disabled by default).
    # JSON dict like {"s4a": true, "s4b": false, ...}
    dnsn_optional_ledgers = models.JSONField(default=dict, blank=True)

    # Module visibility: which advanced sidebar modules are enabled.
    # JSON dict like {"nhan_su": true, "tai_san": false, ...}
    # Core modules are always visible; advanced modules are gated by this
    # field for DNSN (TT58) companies. See apps.core.module_config.
    enabled_modules = models.JSONField(default=dict, blank=True)

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

    @property
    def tax_method_group(self) -> int:
        """Compute tax method group (1-4) from vat_method + tndn_method.

        Group 1: vat=ty_le_phan_tram + tndn=ty_le_phan_tram
        Group 2: vat=ty_le_phan_tram + tndn=tinh_thue
        Group 3: vat=khau_tru + tndn=ty_le_phan_tram
        Group 4: vat=khau_tru + tndn=tinh_thue
        """
        vat_pct = self.vat_method == self.VatMethod.TY_LE_PHAN_TRAM
        tndn_pct = self.tndn_method == self.TndnMethod.TY_LE_PHAN_TRAM
        if vat_pct and tndn_pct:
            return 1
        if vat_pct and not tndn_pct:
            return 2
        if not vat_pct and tndn_pct:
            return 3
        return 4

    @property
    def tax_method_group_label(self) -> str:
        """Human-readable label for the tax method group."""
        return self.TAX_METHOD_GROUP_LABELS.get(
            self.tax_method_group, f"Nhóm {self.tax_method_group}"
        )


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


class TaxRateConfig(models.Model):
    """Configurable tax rates — updated when law changes.

    Cit rates follow Luật Thuế TNDN 2025 (67/2025/QH15).
    Vat reduction follows ND 174/2025 (8% from 01/07/2025 to 31/12/2026).
    Pit deductions & BHXH cap follow TT 111/2013 + ND 74/2024.
    """

    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, null=True, blank=True)

    # CIT rates (Luật TNDN 2025)
    cit_rate_standard = models.DecimalField(max_digits=6, decimal_places=4, default=0.20)  # 20%
    cit_rate_small = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.17
    )  # 17% (3-50 tỷ)
    cit_rate_micro = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.15
    )  # 15% (<=3 tỷ)
    # CIT exemption threshold (ND 141/2026 — revenue <= 1B VND/year = 0% CIT)
    cit_exemption_threshold = models.DecimalField(
        max_digits=20, decimal_places=4, default=1000000000
    )  # 1 tỷ VND/year

    # VAT rates (ND 174/2025)
    vat_rate_standard = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)  # 10%
    vat_rate_reduced = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.08
    )  # 8% (reduced 2025-2026)
    vat_rate_reduced_active = models.BooleanField(default=True)  # toggle 8% on/off

    # VAT exemption + refund thresholds (Luật GTGT 09/2026)
    # Revenue <= 1 tỷ/year = VAT exempt; input VAT >= 300 triệu = refund eligible.
    vat_exemption_threshold = models.DecimalField(
        max_digits=20, decimal_places=4, default=1000000000
    )  # 1 tỷ VND/year
    vat_refund_threshold = models.DecimalField(
        max_digits=20, decimal_places=4, default=300000000
    )  # 300 triệu VND

    # PIT (TNCN) — personal deduction (Luật 09/2026/QH16 effective 01/01/2026)
    pit_personal_deduction = models.DecimalField(max_digits=15, decimal_places=4, default=13200000)
    pit_dependent_deduction = models.DecimalField(max_digits=15, decimal_places=4, default=5200000)
    # Progressive PIT brackets — list of [threshold_cap, rate] pairs, ordered ascending.
    # Per TT 111/2013 (monthly taxable income, VND): 5%/10%/15%/20%/25%/30%/35%.
    pit_brackets = models.JSONField(
        default=list,
        help_text="[[5000000, 0.05], [10000000, 0.10], ...]",
    )

    # --- PIT 2026 (Luật 09/2026/QH16 — effective 01/07/2026) ---
    # New 5-bracket progressive system replacing the 7-bracket TT 111/2013 system.
    pit_personal_deduction_2026 = models.DecimalField(
        max_digits=15, decimal_places=4, default=15500000
    )  # 15.5M from 1/7/2026
    pit_dependent_deduction_2026 = models.DecimalField(
        max_digits=15, decimal_places=4, default=6200000
    )  # 6.2M from 1/7/2026
    pit_brackets_2026 = models.JSONField(
        default=list,
        blank=True,
        help_text="5-bracket system from Luật 09/2026/QH16 (from 01/07/2026)",
    )

    # --- PIT non-taxable allowances (ND 253/2026 + TT 87/2026, from 01/07/2026) ---
    # Các khoản trợ cấp không chịu thuế TNCN.
    pit_meal_allowance = models.DecimalField(
        max_digits=15, decimal_places=4, default=1200000
    )  # Trợ cấp ăn trưa — tối đa 1.2M/tháng
    pit_pension_allowance = models.DecimalField(
        max_digits=15, decimal_places=4, default=3000000
    )  # Trợ cấp BHXH tự nguyện / Bảo hiểm人寿 — tối đa 3M/tháng
    pit_medical_deduction = models.DecimalField(
        max_digits=15, decimal_places=4, default=23000000
    )  # Tan thuốc BHYT tự thanh toán — tối đa 23M/năm
    pit_education_deduction = models.DecimalField(
        max_digits=15, decimal_places=4, default=24000000
    )  # Học phí con — tối đa 24M/năm
    pit_dependent_income_threshold = models.DecimalField(
        max_digits=15, decimal_places=4, default=3000000
    )  # Mức thu nhập tối thiểu của người phụ thuộc — 3M/tháng
    pit_withholding_threshold = models.DecimalField(
        max_digits=15, decimal_places=4, default=5000000
    )  # Mức thu nhập phải khấu trừ tại nguồn — 5M/lần chi trả

    # --- TTĐB rates (Luật TTĐB 66/2025/QH15) ---
    ttdb_alcohol_high = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.65
    )  # rượu ≥20° → 90% by 2031
    ttdb_alcohol_low = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.35
    )  # rượu <20° → 60% by 2031
    ttdb_beer = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.65
    )  # bia → 90% by 2031
    ttdb_tobacco_rate = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.75
    )  # thuốc lá tỷ lệ
    ttdb_tobacco_absolute = models.DecimalField(
        max_digits=15, decimal_places=4, default=5000
    )  # 5.000đ/bao (thuế tuyệt đối)
    ttdb_car_under_9 = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.15
    )  # ô tô <9 chỗ (varies)
    ttdb_car_hybrid_discount = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.70
    )  # HEV = 70% mức thường

    # --- Lệ phí môn bài (ND 22/2020) ---
    fee_monbai_over_10b = models.DecimalField(
        max_digits=15, decimal_places=4, default=3000000
    )  # vốn >10 tỷ
    fee_monbai_under_10b = models.DecimalField(
        max_digits=15, decimal_places=4, default=2000000
    )  # vốn ≤10 tỷ

    # --- Lệ phí trước bạ (ND 10/2022) ---
    fee_truoc_ba_real_estate = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.005
    )  # 0.5% — nhà/đất/ô tô <9 chỗ
    fee_truoc_ba_other = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.01
    )  # 1% — tài sản khác

    # --- Thuế nhà thầu (Foreign Contractor Tax — TT 20/2026) ---
    fct_cit_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.05)  # TNDN 5%
    fct_vat_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.05)  # VAT (varies)

    # Insurance (ND 161/2026 — effective 01/07/2026)
    bhxh_cap = models.DecimalField(
        max_digits=15, decimal_places=4, default=50600000
    )  # 20 x 2,530,000
    bhxh_base_salary = models.DecimalField(max_digits=15, decimal_places=4, default=2530000)

    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tax_rate_config"
        ordering = ["-effective_date"]

    def __str__(self):
        return f"TaxRateConfig (eff. {self.effective_date}, active={self.is_active})"


class PITRateHistory(models.Model):
    """Historical PIT (Thuế TNCN) rates for audit and comparison.

    Tracks changes in personal/dependent deduction + brackets across
    Vietnamese PIT law revisions since 2009:
    - 2009-2013: Luật TNCN 04/2007/QH12 (4M/1.6M, 7 brackets)
    - 2013-2020: Luật 26/2012/QH13 (9M/3.6M, 7 brackets)
    - 2020-2026: NQ 954/2020/UBTVQH14 (11M/4.4M, 7 brackets)
    - 2026+:     Luật 09/2026/QH16 + NQ 110/2025 (15.5M/6.2M, 5 brackets)
    """

    period_start = models.DateField()
    period_end = models.DateField(null=True, blank=True)
    personal_deduction = models.DecimalField(max_digits=15, decimal_places=4)
    dependent_deduction = models.DecimalField(max_digits=15, decimal_places=4)
    brackets = models.JSONField(default=list)  # [[cap, rate], ...]
    legal_basis = models.CharField(max_length=200)
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "pit_rate_history"
        ordering = ["-period_start"]
        verbose_name = "PIT Rate History"
        verbose_name_plural = "PIT Rate History"

    def __str__(self):
        end = self.period_end or "now"
        return f"PIT {self.period_start} → {end} (GTGC {self.personal_deduction})"


class TaxType(models.Model):
    """Master record of all Vietnamese tax types.

    Covers direct (Thuế trực thu), indirect (gián thu), and fee (lệ phí) categories.
    Acts as a reference dictionary; rates are stored in TaxRateConfig.
    """

    CATEGORY_DIRECT = "direct"
    CATEGORY_INDIRECT = "indirect"
    CATEGORY_FEE = "fee"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=20)  # direct, indirect, fee
    description = models.TextField(blank=True, default="")
    current_rate_text = models.TextField(help_text="Human-readable rate description")
    legal_basis = models.CharField(max_length=100, blank=True, default="")
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tax_type"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class FeatureFlag(models.Model):
    """Feature flag for safe rollouts. Per-company or global (company=null)."""

    key = models.CharField(max_length=100, db_index=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feature_flags",
    )
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feature_flag"
        unique_together = [("key", "company")]
        indexes = [models.Index(fields=["key", "enabled"])]

    def __str__(self):
        scope = self.company.code if self.company else "global"
        return f"{self.key} ({scope}): {'ON' if self.enabled else 'OFF'}"


class UserSearchAffinity(models.Model):
    """Per-user interest score per search object type, used to personalize
    the ordering of result groups in global search. Score is time-decayed
    and incremented on each result click."""

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="search_affinities",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="search_affinities",
    )
    object_type = models.CharField(max_length=50)
    score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_search_affinity"
        unique_together = [("user", "company", "object_type")]
        indexes = [models.Index(fields=["user", "company"])]

    def __str__(self):
        return f"{self.user_id}@{self.company_id} {self.object_type}={self.score:.2f}"
