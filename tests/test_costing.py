"""Tests for cost accounting (giá thành) service and view."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, VoucherLine


@pytest.fixture
def company(db):
    return Company.objects.create(code="COST", name="Costing Test Co")


@pytest.fixture
def setup_vouchers(company):
    """Create production cost vouchers: TK 621/622/623."""
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no="COST-001",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        currency_code="VND",
        exchange_rate=Decimal("1"),
        total_vnd=Decimal("30000000"),
        status=AccountingVoucher.Status.LEDGER,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code="621",
        debit_vnd=Decimal("15000000"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="622",
        debit_vnd=Decimal("8000000"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=3,
        account_code="623",
        debit_vnd=Decimal("7000000"),
    )
    return v


# ---------- Service tests ----------


@pytest.mark.django_db
def test_collect_costs(company, setup_vouchers):
    from apps.costing.services import CostingService

    service = CostingService(company)
    summary = service.collect_costs(2026, 6)
    assert summary.materials == Decimal("15000000")
    assert summary.labor == Decimal("8000000")
    assert summary.overhead == Decimal("7000000")
    assert summary.total_input == Decimal("30000000")


@pytest.mark.django_db
def test_calculate_unit_cost(company, setup_vouchers):
    from apps.costing.services import CostingService

    service = CostingService(company)
    summary = service.calculate_unit_cost(2026, 6, Decimal("1000"))
    assert summary.output_quantity == Decimal("1000")
    assert summary.unit_cost == Decimal("30000.0000")  # 30M / 1000


@pytest.mark.django_db
def test_collect_costs_empty_period(company):
    from apps.costing.services import CostingService

    service = CostingService(company)
    summary = service.collect_costs(2026, 6)
    assert summary.materials == Decimal("0")
    assert summary.total_input == Decimal("0")


@pytest.mark.django_db
def test_create_closing_entry(company, setup_vouchers):
    from apps.costing.services import CostingService

    service = CostingService(company)
    voucher = service.create_closing_entry(2026, 6)
    assert voucher is not None
    assert voucher.voucher_no.startswith("GTHANH-202606")
    lines = VoucherLine.objects.filter(voucher=voucher).order_by("line_no")
    # N154 + C621 + C622 + C623 = 4 lines
    assert lines.count() == 4
    # First line is N154 with total
    assert lines[0].account_code == "154"
    assert lines[0].debit_vnd == Decimal("30000000")
    # Remaining are credits
    credit_total = sum(l.credit_vnd for l in lines)
    assert credit_total == Decimal("30000000")


@pytest.mark.django_db
def test_create_closing_entry_no_costs(company):
    from apps.costing.services import CostingService

    service = CostingService(company)
    voucher = service.create_closing_entry(2026, 6)
    assert voucher is None  # no costs to close


# ---------- View tests ----------


@pytest.mark.django_db
def test_cost_report_view_loads(company, setup_vouchers):
    user = User.objects.create_superuser(
        username="costadmin", password="Secret123", email="c@test.local"
    )
    c = Client()
    c.force_login(user)
    response = c.get("/modern/reports/cost/?fiscal_year=2026&period=6")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Bảng tính giá thành" in content
    assert "15.000.000" in content or "15000000" in content


@pytest.mark.django_db
def test_cost_report_with_output_qty(company, setup_vouchers):
    user = User.objects.create_superuser(
        username="costadmin2", password="Secret123", email="c2@test.local"
    )
    c = Client()
    c.force_login(user)
    response = c.get("/modern/reports/cost/?fiscal_year=2026&period=6&output_qty=1000")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "30000,0000" in content or "30000.0000" in content  # unit cost: 30M / 1000
