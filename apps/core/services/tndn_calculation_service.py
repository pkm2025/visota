"""TNDN (Thuế thu nhập doanh nghiệp) calculation service for TT58.

Supports two calculation methods per TT58/2026/TT-BTC:

1. **ty_le_phan_tram** (percentage on revenue): tax = revenue × rate.
   The rate varies by industry per ND 218/2013/NĐ-CP (simplified):
   - Trading (thương mại): 0.5%
   - Services (dịch vụ): 2.0%
   - Production/Construction (sản xuất/xây dựng): 1.5%
   - Other activities: 1.0%

2. **tinh_thue** (calculated on taxable income): tax = taxable_income × CIT_rate.
   Uses TaxConfigService to determine the CIT rate based on company size.
"""

from decimal import Decimal

from apps.core.models import Company
from apps.core.services.tax_config_service import TaxConfigService


class TndnCalculationService:
    """Calculate TNDN (corporate income tax) based on company's tndn_method.

    For TT58 companies:
    - tndn_method='ty_le_phan_tram': tax = revenue × tndn_rate (revenue-based)
    - tndn_method='tinh_thue': tax = taxable_income × cit_rate

    For non-TT58 companies, always uses the tinh_thue method (standard CIT).
    """

    # TNDN percentage rates per TT58/2026/TT-BTC (based on ND 218/2013).
    # These are the percentage-on-revenue rates for DNSN that elect the
    # "tỷ lệ %" method for TNDN.
    TNDN_PCT_RATES: dict[str, Decimal] = {
        "trading": Decimal("0.005"),  # 0.5% — thương mại
        "services": Decimal("0.02"),  # 2.0% — dịch vụ
        "production": Decimal("0.015"),  # 1.5% — sản xuất/xây dựng
        "other": Decimal("0.01"),  # 1.0% — khác (default)
    }

    def __init__(self, company: Company):
        self.company = company

    def calculate(
        self,
        revenue: Decimal | int | str,
        deductible_costs: Decimal | int | str = 0,
    ) -> dict:
        """Calculate TNDN tax for a period.

        Args:
            revenue: Total revenue for the period.
            deductible_costs: Total deductible costs (used for tinh_thue method).

        Returns dict with:
            - method: 'ty_le_phan_tram' or 'tinh_thue'
            - revenue: Decimal
            - taxable_income: Decimal (revenue - costs for tinh_thue, else same as revenue)
            - rate: Decimal (the applicable rate)
            - tax_amount: Decimal (the computed tax)
        """
        rev = Decimal(str(revenue))
        costs = Decimal(str(deductible_costs))

        if self._is_tndn_percentage():
            rate = self._get_tndn_pct_rate()
            tax_amount = (rev * rate).quantize(Decimal("0.0001"))
            return {
                "method": "ty_le_phan_tram",
                "revenue": rev,
                "taxable_income": rev,
                "rate": rate,
                "tax_amount": tax_amount,
            }

        # tinh_thue: tax = taxable_income × CIT rate
        cit_rate = self._get_cit_rate()
        taxable_income = rev - costs
        if taxable_income < 0:
            taxable_income = Decimal("0")
        tax_amount = (taxable_income * cit_rate).quantize(Decimal("0.0001"))
        return {
            "method": "tinh_thue",
            "revenue": rev,
            "taxable_income": taxable_income,
            "rate": cit_rate,
            "tax_amount": tax_amount,
        }

    def _is_tndn_percentage(self) -> bool:
        """Check if company uses the percentage-on-revenue TNDN method."""
        return self.company.tndn_method == Company.TndnMethod.TY_LE_PHAN_TRAM

    def _get_tndn_pct_rate(self) -> Decimal:
        """Get the TNDN percentage rate based on company industry.

        Defaults to 'other' (1.0%) if no industry mapping is set.
        """
        industry = getattr(self.company, "industry", None) or "other"
        return self.TNDN_PCT_RATES.get(industry, self.TNDN_PCT_RATES["other"])

    def _get_cit_rate(self) -> Decimal:
        """Get the CIT rate for tinh_thue method via TaxConfigService."""
        return TaxConfigService.get_cit_rate(self.company)
