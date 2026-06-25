"""Tests for budget module: template generation, actuals refresh, cash flow."""

from datetime import date
from decimal import Decimal

import pytest

from apps.budget.models import Budget, BudgetLine, CashFlowProjection
from apps.budget.services import (
    BudgetVarianceService,
    CashFlowService,
)
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTBUDG", name="Test Budget Co")


# ---------- Template generation ----------

@pytest.mark.django_db
def test_generate_default_template_creates_budget(company):
    budget = BudgetVarianceService.generate_default_template(company, 2026)
    assert budget.fiscal_year == 2026
    assert budget.scenario == Budget.Scenario.PLANNED
    # 12 months × 5 groups = 60 lines
    assert budget.lines.count() == 60


@pytest.mark.django_db
def test_generate_default_template_idempotent(company):
    b1 = BudgetVarianceService.generate_default_template(company, 2026)
    b2 = BudgetVarianceService.generate_default_template(company, 2026)
    assert b1.pk == b2.pk


@pytest.mark.django_db
def test_budget_lines_group_distribution(company):
    budget = BudgetVarianceService.generate_default_template(company, 2026)
    groups = set(budget.lines.values_list("account_group", flat=True))
    assert groups == {"revenue", "cogs", "opex", "salaries", "marketing"}
    # 12 months × 5 groups
    assert budget.lines.count() == 60


@pytest.mark.django_db
def test_budget_net_profit_property(company):
    budget = Budget.objects.create(
        company=company, fiscal_year=2026, name="X",
        total_revenue=Decimal("1000"), total_expense=Decimal("700"),
    )
    assert budget.net_profit == Decimal("300")


# ---------- Actuals refresh ----------

@pytest.mark.django_db
def test_refresh_actuals_no_ledger_data_no_change(company):
    """If no AccountPeriodBalance exists, actuals stay 0."""
    budget = BudgetVarianceService.generate_default_template(company, 2026)
    BudgetVarianceService.refresh_actuals(budget)
    for line in budget.lines.all():
        assert line.actual_amount == Decimal("0")


@pytest.mark.django_db
def test_refresh_actuals_pulls_from_period_balance(company):
    """Create ledger data → refresh → verify actuals."""
    from apps.ledger.models import AccountPeriodBalance

    budget = BudgetVarianceService.generate_default_template(company, 2026)

    # Simulate: 100M revenue in Jan 2026
    AccountPeriodBalance.objects.create(
        company=company, fiscal_year=2026, period=1,
        account_code="5111", period_credit=Decimal("100000000"),
    )

    BudgetVarianceService.refresh_actuals(budget)
    revenue_jan = budget.lines.get(period_month=1, account_group="revenue")
    assert revenue_jan.actual_amount == Decimal("100000000")


# ---------- Cash flow ----------

@pytest.mark.django_db
def test_cash_flow_projection_net_flow_property(company):
    proj = CashFlowProjection.objects.create(
        company=company, period_year=2026, period_month=6,
        expected_ar_collection=Decimal("1000"),
        expected_ap_payment=Decimal("500"),
        expected_payroll=Decimal("200"),
        expected_tax=Decimal("100"),
        opening_balance=Decimal("10000"),
    )
    assert proj.net_cash_flow == Decimal("200")
    assert proj.closing_balance == Decimal("10200")


@pytest.mark.django_db
def test_cash_flow_projection_unique_per_period(company):
    CashFlowProjection.objects.create(
        company=company, period_year=2026, period_month=6,
    )
    with pytest.raises(Exception):
        CashFlowProjection.objects.create(
            company=company, period_year=2026, period_month=6,
        )


@pytest.mark.django_db
def test_cash_flow_service_generate_for_period(company):
    """Generate projection for empty company — should still create record."""
    proj = CashFlowService.generate_for_period(company, 2026, 6)
    assert proj.period_year == 2026
    assert proj.period_month == 6
    # All zeros because no vouchers
    assert proj.expected_ar_collection == Decimal("0")


@pytest.mark.django_db
def test_cash_flow_service_generate_with_voucher_data(company):
    """With AR voucher, projection should have positive AR collection."""
    from apps.ledger.models import AccountingVoucher, VoucherLine

    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=5,
        voucher_no="V-001", voucher_type="journal",
        voucher_date=date(2026, 5, 15), currency_code="VND",
        exchange_rate=Decimal("1"), total_vnd=Decimal("1000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v, line_no=1, account_code="131",
        debit_vnd=Decimal("1000000"),
    )

    proj = CashFlowService.generate_for_period(company, 2026, 6)
    # 60% of 1M AR = 600k
    assert proj.expected_ar_collection == Decimal("600000")
