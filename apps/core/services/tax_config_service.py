"""Tax configuration service.

Provides CIT/VAT lookup based on Luật TNDN 2025 (67/2025/QH15), ND 174/2025 (VAT 8%),
and SME classification per ND 80/2021.
"""

from decimal import Decimal

from django.db.models import Q

from apps.core.models import Company, TaxRateConfig


class TaxConfigService:
    """Lookup active tax rates and classify SMEs."""

    # ND 80/2021 revenue thresholds (VND)
    # Source: ND 80/2021/NĐ-CP Article 5 — three-sector grouping simplified.
    # Sector-specific: Nong-Lam-Thuỷ sản (Agri) and Công nghiệp-Xây dựng (Ind/Const)
    # use lower thresholds than Thương mại-Dịch vụ (Commerce/Service).
    _SECTOR_AGRI_IND = {"agri", "industry", "construction"}
    _SECTOR_COMMERCE_SERVICE = {"commerce", "service"}

    # Revenue thresholds — Agri/Industry: micro<3 tỷ, small 3-50 tỷ, medium 50-200 tỷ
    # Commerce/Service: same revenue brackets but different capital brackets per sector.
    MICRO_REVENUE = Decimal("3000000000")  # <3 tỷ
    SMALL_REVENUE = Decimal("50000000000")  # 3-50 tỷ
    MEDIUM_REVENUE = Decimal("200000000000")  # 50-200 tỷ

    # Capital thresholds (per sector) — Agri/Industry lower
    MICRO_CAPITAL_AGGRI = Decimal("3000000000")
    SMALL_CAPITAL_AGGRI = Decimal("20000000000")
    MEDIUM_CAPITAL_AGGRI = Decimal("100000000000")
    # Commerce/Service
    MICRO_CAPITAL_COMMERCE = Decimal("3000000000")
    SMALL_CAPITAL_COMMERCE = Decimal("20000000000")
    MEDIUM_CAPITAL_COMMERCE = Decimal("100000000000")

    @staticmethod
    def get_active(company=None):
        """Get current active tax config (optionally scoped to company)."""
        qs = TaxRateConfig.objects.filter(is_active=True)
        if company is not None:
            qs = qs.filter(Q(company=company) | Q(company__isnull=True))
        return qs.order_by("-effective_date").first()

    @staticmethod
    def get_cit_rate(company):
        """Get CIT rate based on company SME size and annual revenue.

        Per ND 141/2026, enterprises with annual revenue <= cit_exemption_threshold
        (default 1 billion VND/year) are fully exempt (rate = 0%).
        """
        # Only filter by company if it has a pk; otherwise fall back to global config.
        if company is not None and getattr(company, "pk", None) is not None:
            config = TaxConfigService.get_active(company)
        else:
            config = TaxConfigService.get_active()
        if config is None:
            return Decimal("0.20")  # fallback to standard 20%
        if company is None:
            return config.cit_rate_standard
        # CIT exemption per ND 141/2026: revenue <= threshold -> 0%
        annual_revenue = getattr(company, "annual_revenue", None)
        if annual_revenue is not None and annual_revenue <= config.cit_exemption_threshold:
            return Decimal("0")
        if company.sme_size == Company.SMESize.MICRO:
            return config.cit_rate_micro
        if company.sme_size == Company.SMESize.SMALL:
            return config.cit_rate_small
        return config.cit_rate_standard

    @staticmethod
    def get_vat_rate(is_reduced=False):
        """Get VAT rate — 8% if reduced period active, else 10%."""
        config = TaxConfigService.get_active()
        if config is None:
            return Decimal("0.10")  # fallback
        if config.vat_rate_reduced_active and is_reduced:
            return config.vat_rate_reduced
        return config.vat_rate_standard

    @staticmethod
    def is_vat_exempt(company):
        """Check if a company qualifies for VAT exemption per Luật GTGT 09/2026.

        A company with annual revenue <= vat_exemption_threshold
        (default 1 billion VND/year) is exempt from VAT.
        """
        config = TaxConfigService.get_active()
        if config is None:
            return False
        annual_revenue = getattr(company, "annual_revenue", None)
        if annual_revenue is None:
            return False
        return annual_revenue <= config.vat_exemption_threshold

    @staticmethod
    def is_vat_refund_eligible(company, input_vat):
        """Check if a company is eligible for VAT refund per Luật GTGT 09/2026.

        A company qualifies for VAT refund when:
        - It is NOT VAT-exempt (revenue exceeds the exemption threshold), AND
        - Input VAT >= vat_refund_threshold (default 300 million VND).
        """
        if TaxConfigService.is_vat_exempt(company):
            return False
        config = TaxConfigService.get_active()
        if config is None:
            return False
        if input_vat is None:
            return False
        return input_vat >= config.vat_refund_threshold

    @classmethod
    def classify_sme(cls, annual_revenue, total_capital, employee_count, sector):
        """Classify company as micro/small/medium/large per ND 80/2021.

        ND 80/2021 Article 5: a company is micro/small/medium if it satisfies
        ALL criteria for that size category (revenue OR capital — lower tier wins).
        Sector affects capital thresholds.
        """
        # Normalize sector
        s = (sector or "").lower()
        if s in cls._SECTOR_AGRI_IND:
            micro_cap = cls.MICRO_CAPITAL_AGGRI
            small_cap = cls.SMALL_CAPITAL_AGGRI
            medium_cap = cls.MEDIUM_CAPITAL_AGGRI
        else:
            # Default to commerce/service
            micro_cap = cls.MICRO_CAPITAL_COMMERCE
            small_cap = cls.SMALL_CAPITAL_COMMERCE
            medium_cap = cls.MEDIUM_CAPITAL_COMMERCE

        rev = Decimal(annual_revenue) if not isinstance(annual_revenue, Decimal) else annual_revenue
        cap = Decimal(total_capital) if not isinstance(total_capital, Decimal) else total_capital

        # Take the lower classification from either revenue or capital
        rev_tier = cls._tier_by_threshold(
            rev, cls.MICRO_REVENUE, cls.SMALL_REVENUE, cls.MEDIUM_REVENUE
        )
        cap_tier = cls._tier_by_threshold(cap, micro_cap, small_cap, medium_cap)

        # Lower tier wins (more conservative)
        tier_order = {"micro": 0, "small": 1, "medium": 2, "large": 3}
        result_tier = min(tier_order[rev_tier], tier_order[cap_tier])
        for k, v in tier_order.items():
            if v == result_tier:
                return k
        return "small"

    @staticmethod
    def _tier_by_threshold(value, micro_limit, small_limit, medium_limit):
        if value < micro_limit:
            return "micro"
        if value < small_limit:
            return "small"
        if value < medium_limit:
            return "medium"
        return "large"
