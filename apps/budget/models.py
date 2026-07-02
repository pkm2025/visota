"""Budget + Cash flow models.

Budget: a year + scenario (planned/forecast/actual).
BudgetLine: per period × account code.
CashFlowProjection: monthly AR/AP projected cash in/out.
"""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class Budget(CompanyOwnedModel):
    """Annual budget for a scenario."""

    class Scenario(models.TextChoices):
        PLANNED = "planned", "Kế hoạch"
        FORECAST = "forecast", "Dự phóng"
        ROLLING = "rolling", "Cuộn (rolling)"

    fiscal_year = models.PositiveSmallIntegerField()
    scenario = models.CharField(max_length=20, choices=Scenario.choices, default=Scenario.PLANNED)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    total_revenue = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    total_expense = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    is_active = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        "identity.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budgets_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budget"
        unique_together = [("company", "fiscal_year", "scenario")]
        ordering = ["-fiscal_year", "scenario"]

    def __str__(self):
        return f"{self.fiscal_year} {self.get_scenario_display()} — {self.name}"

    @property
    def net_profit(self):
        return self.total_revenue - self.total_expense


class BudgetLine(models.Model):
    """One budget line: period × account group."""

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    period_month = models.PositiveSmallIntegerField()  # 1-12
    account_group = models.CharField(max_length=50)
    # E.g., "revenue", "cogs", "opex", "salaries", "marketing", "capex"
    direction = models.CharField(max_length=10, default="debit")
    # debit = expense (chi), credit = revenue (thu)

    planned_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    actual_amount = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "budget_line"
        unique_together = [("budget", "period_month", "account_group", "direction")]
        ordering = ["period_month", "account_group"]

    @property
    def variance(self):
        return self.actual_amount - self.planned_amount

    @property
    def variance_pct(self):
        if not self.planned_amount:
            return 0
        return self.variance / self.planned_amount * 100


class CashFlowProjection(CompanyOwnedModel):
    """Monthly cash flow projection based on AR/AP due dates."""

    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    # Projected inflow from AR (131) due in this month
    expected_ar_collection = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    # Projected outflow to AP (331) due in this month
    expected_ap_payment = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    # Payroll + tax + other committed
    expected_payroll = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    expected_tax = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    expected_other = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    # Beginning balance (cash on hand start of month)
    opening_balance = models.DecimalField(max_digits=20, decimal_places=4, default=0)

    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cash_flow_projection"
        unique_together = [("company", "period_year", "period_month")]

    @property
    def net_cash_flow(self):
        return (
            self.expected_ar_collection
            - self.expected_ap_payment
            - self.expected_payroll
            - self.expected_tax
            - self.expected_other
        )

    @property
    def closing_balance(self):
        return self.opening_balance + self.net_cash_flow
