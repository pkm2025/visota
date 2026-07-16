"""InsuranceService — monthly BHXH/BHYT/BHTN/BHTNLĐ/KPCĐ calculation (ND 161/2026)."""

from decimal import Decimal

from apps.core.services.tax_config_service import TaxConfigService
from apps.hr.models.insurance import InsuranceContribution

# Vietnamese social insurance rate percentages (ND 161/2026).
# Cap and base salary are read from TaxRateConfig (no hardcoded constants).
RATES = {
    # Employee portion — 10.5% total
    "bhxh_emp": Decimal("0.08"),  # BHXH 8% (hưu + ốm + thai sản + TNLĐ-BNN)
    "bhyt_emp": Decimal("0.015"),  # BHYT 1.5%
    "bhtn_emp": Decimal("0.01"),  # BHTN 1%
    # Employer portion — 23.5% total (incl. KPCĐ 2%)
    "bhxh_er": Decimal("0.17"),  # 14% hưu trí + 3% ốm/thai
    "bhyt_er": Decimal("0.03"),  # BHYT 3%
    "bhtn_er": Decimal("0.01"),  # BHTN 1%
    "bhtnld_er": Decimal("0.005"),  # BHTNLĐ-BNN 0.5% (employer only)
    "kpcd_er": Decimal("0.02"),  # Kinh phí công đoàn 2%
}

# Fallback values used only when TaxRateConfig has no active entry.
_DEFAULT_CAP = Decimal("50600000")  # 20 x 2,530,000 (ND 161/2026)


def _round(amount: Decimal) -> Decimal:
    """Round to integer VND."""
    return amount.quantize(Decimal("1"))


class InsuranceService:
    """Calculate and persist monthly insurance contribution per employee."""

    def __init__(self, company):
        self.company = company

    def _get_cap(self) -> Decimal:
        """Read insurance cap from TaxRateConfig; fall back to ND 161/2026 default."""
        config = TaxConfigService.get_active(self.company)
        if config is not None:
            return config.bhxh_cap
        return _DEFAULT_CAP

    def calculate_monthly(self, employee, period: str) -> InsuranceContribution:
        """Calculate contribution for given employee/period (YYYY-MM).

        Caps salary_base at bhxh_cap from TaxRateConfig
        (50,600,000 VND = 20 x luong co so 2,530,000 per ND 161/2026).
        """
        raw = employee.base_salary or Decimal("0")
        cap = self._get_cap()
        capped = min(raw, cap)

        bhxh_emp = _round(capped * RATES["bhxh_emp"])
        bhyt_emp = _round(capped * RATES["bhyt_emp"])
        bhtn_emp = _round(capped * RATES["bhtn_emp"])
        total_emp = bhxh_emp + bhyt_emp + bhtn_emp

        bhxh_er = _round(capped * RATES["bhxh_er"])
        bhyt_er = _round(capped * RATES["bhyt_er"])
        bhtn_er = _round(capped * RATES["bhtn_er"])
        bhtnld_er = _round(capped * RATES["bhtnld_er"])
        kpcd_er = _round(capped * RATES["kpcd_er"])
        total_er = bhxh_er + bhyt_er + bhtn_er + bhtnld_er + kpcd_er

        ic, _ = InsuranceContribution.objects.update_or_create(
            employee=employee,
            period=period,
            defaults={
                "company": self.company,
                "salary_base": capped,
                "bhxh_employee": bhxh_emp,
                "bhyt_employee": bhyt_emp,
                "bhtn_employee": bhtn_emp,
                "total_employee": total_emp,
                "bhxh_employer": bhxh_er,
                "bhyt_employer": bhyt_er,
                "bhtn_employer": bhtn_er,
                "bhtnld_employer": bhtnld_er,
                "kpcd_employer": kpcd_er,
                "total_employer": total_er,
            },
        )
        return ic
