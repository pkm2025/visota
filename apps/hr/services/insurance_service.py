"""InsuranceService — monthly BHXH/BHYT/BHTN/BHTNLĐ/KPCĐ calculation (2025 rates)."""

from decimal import Decimal

from apps.hr.models.insurance import INSURANCE_CAP, InsuranceContribution

# 2025 Vietnamese social insurance rates
RATES = {
    # Employee portion — 10.5% total
    "bhxh_emp": Decimal("0.08"),   # BHXH 8% (hưu + ốm + thai sản + TNLĐ-BNN)
    "bhyt_emp": Decimal("0.015"),  # BHYT 1.5%
    "bhtn_emp": Decimal("0.01"),   # BHTN 1%
    # Employer portion — 21.5% total
    "bhxh_er": Decimal("0.17"),    # 14% hưu trí + 3% ốm/thai
    "bhyt_er": Decimal("0.03"),    # BHYT 3%
    "bhtn_er": Decimal("0.01"),    # BHTN 1%
    "bhtnld_er": Decimal("0.005"), # BHTNLĐ-BNN 0.5% (employer only)
    "kpcd_er": Decimal("0.02"),    # Kinh phí công đoàn 2%
}


def _round(amount: Decimal) -> Decimal:
    """Round to integer VND."""
    return amount.quantize(Decimal("1"))


class InsuranceService:
    """Calculate and persist monthly insurance contribution per employee."""

    def __init__(self, company):
        self.company = company

    def calculate_monthly(self, employee, period: str) -> InsuranceContribution:
        """Calculate contribution for given employee/period (YYYY-MM).

        Caps salary_base at INSURANCE_CAP (46,800,000 VND = 20 × lương cơ sở).
        """
        raw = employee.base_salary or Decimal("0")
        capped = min(raw, Decimal(str(INSURANCE_CAP)))

        bhxh_emp = _round(capped * RATES["bhxh_emp"])
        bhyt_emp = _round(capped * RATES["bhyt_emp"])
        bhtn_emp = _round(capped * RATES["bhtn_emp"])
        total_emp = bhxh_emp + bhyt_emp + bhtn_emp

        bhxh_er = _round(capped * RATES["bhxh_er"])
        bhyt_er = _round(capped * RATES["bhyt_er"])
        bhtn_er = _round(capped * RATES["bhtn_er"])
        bhtnld_er = _round(capped * RATES["bhtnld_er"])
        kpcd_er = _round(capped * RATES["kpcd_er"])
        total_er = bhxh_er + bhyt_er + bhtn_er + bhtnld_er

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
