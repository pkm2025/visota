"""Insurance contribution model — BHXH/BHYT/BHTN/BHTNLĐ/KPCĐ."""

from django.db import models

# Trần đóng bảo hiểm: 20 × lương cơ sở (2,340,000 VND for 2025)
INSURANCE_CAP = 46800000


class InsuranceContribution(models.Model):
    """Bảng kê đóng bảo hiểm xã hội/y tế/thất nghiệp hàng tháng.

    10 fields: 3 employee + 4 employer + kpcd + 2 totals + salary_base.
    """

    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="insurance_contributions",
        db_index=True,
    )
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.CASCADE,
        related_name="insurance_contributions",
    )
    period = models.CharField(max_length=7, help_text="YYYY-MM")
    salary_base = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Employee portion (NV đóng — deducted from gross)
    bhxh_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bhyt_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bhtn_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_employee = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    # Employer portion (DN đóng — additional cost)
    bhxh_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bhyt_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bhtn_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    bhtnld_employer = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )  # BHTNLĐ-BNN 0.5%
    kpcd_employer = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )  # Kinh phí công đoàn 2%
    total_employer = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "hr_insurance_contribution"
        unique_together = [("employee", "period")]
        ordering = ["-period"]

    def __str__(self):
        return f"{self.employee.code} {self.period}"
