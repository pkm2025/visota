"""Tests for enhanced Inventory + Assets + Products modules."""
from datetime import date
from decimal import Decimal

import pytest

from apps.assets.models import (
    AssetCategory,
    AssetTransaction,
    AssetUsingDepartment,
    FixedAsset,
)
from apps.assets.services import AssetLifecycleService
from apps.core.models import Company
from apps.inventory.models import (
    StockAdjustment,
    StockAdjustmentLine,
    StockAlert,
    StockLedger,
)
from apps.inventory.services import StockDashboardService
from apps.ledger.models import AccountingVoucher
from apps.master_data.models import Product, ProductPrice, ProductVariant, Warehouse

# ---------- Fixtures ----------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="ENH", name="Enhanced Co", tax_code="0109999999", accounting_regime="tt133"
    )


@pytest.fixture
def warehouse(company):
    return Warehouse.objects.create(
        company=company, code="WH1", name="Kho chính", warehouse_type="material"
    )


@pytest.fixture
def product(company):
    return Product.objects.create(
        company=company,
        code="P001",
        name="Sản phẩm A",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="1561",
        gl_account_cogs="632",
        gl_account_revenue="5111",
        default_unit_price=Decimal("100000"),
        min_stock=Decimal("10"),
        max_stock=Decimal("1000"),
    )


# ---------- Part 1: Products ----------


def test_product_price_tiers(product):
    ProductPrice.objects.create(
        product=product,
        name="Giá lẻ",
        min_quantity=Decimal("1"),
        unit_price=Decimal("100000"),
        effective_from=date(2026, 1, 1),
    )
    ProductPrice.objects.create(
        product=product,
        name="Giá sỉ",
        min_quantity=Decimal("100"),
        unit_price=Decimal("80000"),
        effective_from=date(2026, 1, 1),
    )
    assert product.prices.count() == 2
    # ordering by min_quantity
    assert list(product.prices.values_list("name", flat=True)) == ["Giá lẻ", "Giá sỉ"]


def test_product_variant(product):
    v = ProductVariant.objects.create(
        product=product,
        code="P001-RED-L",
        name="Sản phẩm A - Đỏ L",
        attribute_name="Color/Size",
        attribute_value="Red/L",
        barcode="8900000001",
        unit_price_adjustment=Decimal("5000"),
    )
    assert product.variants.count() == 1
    assert v.attribute_value == "Red/L"
    # unique constraint
    with pytest.raises(Exception):  # noqa: B017, PT011 — IntegrityError is DB-specific
        ProductVariant.objects.create(
            product=product, code="P001-RED-L", name="dup",
            attribute_name="x", attribute_value="y",
        )


# ---------- Part 2: Inventory ----------


def test_stock_adjustment_creates_and_updates_ledger(company, warehouse, product):
    # Seed a stock ledger with quantity 50
    StockLedger.objects.create(
        company=company, product=product, warehouse=warehouse,
        quantity=Decimal("50"), amount=Decimal("500000"), avg_cost=Decimal("10000"),
    )
    adj = StockAdjustment.objects.create(
        company=company,
        adjustment_no="KK-001",
        adjustment_date=date(2026, 6, 19),
        warehouse=warehouse,
        reason="Kiểm kê",
        status="posted",
    )
    line = StockAdjustmentLine.objects.create(
        adjustment=adj,
        product=product,
        system_quantity=Decimal("50"),
        counted_quantity=Decimal("48"),
        unit_cost=Decimal("10000"),
    )
    assert line.difference == Decimal("-2")  # auto-computed on save
    # Apply diff manually to ledger (mirrors view behavior)
    ledger = StockLedger.objects.get(product=product, warehouse=warehouse)
    ledger.quantity += line.difference
    ledger.save()
    ledger.refresh_from_db()
    assert ledger.quantity == Decimal("48")


def test_stock_dashboard_service_low_stock(company, warehouse, product):
    # min_stock=10, actual=0 -> low stock
    alerts = StockDashboardService.get_low_stock_products(company)
    assert any(a["product"].code == "P001" for a in alerts)

    # Fill up above threshold
    StockLedger.objects.create(
        company=company, product=product, warehouse=warehouse,
        quantity=Decimal("100"), amount=Decimal("1000000"), avg_cost=Decimal("10000"),
    )
    alerts2 = StockDashboardService.get_low_stock_products(company)
    assert not any(a["product"].code == "P001" for a in alerts2)


def test_stock_dashboard_service_summary(company, warehouse, product):
    StockLedger.objects.create(
        company=company, product=product, warehouse=warehouse,
        quantity=Decimal("20"), amount=Decimal("200000"), avg_cost=Decimal("10000"),
    )
    summary = StockDashboardService.get_summary(company)
    assert len(summary) == 1
    s = summary[0]
    assert s["warehouse"].code == "WH1"
    assert s["total_quantity"] == Decimal("20")
    assert s["total_value"] == Decimal("200000")
    assert s["product_count"] == 1


def test_stock_dashboard_valuation(company, warehouse, product):
    StockLedger.objects.create(
        company=company, product=product, warehouse=warehouse,
        quantity=Decimal("20"), amount=Decimal("200000"), avg_cost=Decimal("10000"),
    )
    val = StockDashboardService.get_stock_valuation(company)
    assert len(val) == 1
    assert val[0]["product_code"] == "P001"
    assert val[0]["quantity"] == Decimal("20")


def test_stock_alert_model(product, warehouse):
    a = StockAlert.objects.create(
        product=product,
        warehouse=warehouse,
        alert_type=StockAlert.AlertType.LOW_STOCK,
        current_quantity=Decimal("5"),
        threshold=Decimal("10"),
    )
    assert a.alert_type == "low_stock"
    assert a.resolved is False


# ---------- Part 3: Asset Lifecycle ----------


@pytest.fixture
def asset_setup(company):
    cat = AssetCategory.objects.create(
        company=company, code="MAY", name="Máy", level="group",
        is_for_tool=False, default_gl_account="211",
        default_depreciation_rate=Decimal("0.20"),
        default_useful_life_months=60,
    )
    dept = AssetUsingDepartment.objects.create(
        company=company, code="BP1", name="BP bán hàng", default_expense_account="641",
    )
    dept2 = AssetUsingDepartment.objects.create(
        company=company, code="BP2", name="BP quản lý", default_expense_account="642",
    )
    asset = FixedAsset.objects.create(
        company=company, asset_code="TS01", asset_name="Xe tải",
        category=cat, using_department=dept,
        original_cost=Decimal("100000000"),
        depreciation_method="straight_line",
        depreciation_rate=Decimal("0.20"),
        useful_life_months=60,
        start_date=date(2025, 1, 1),
        gl_account="211", depreciation_account="2141", expense_account="641",
    )
    return cat, dept, dept2, asset


def test_asset_dispose_with_loss(asset_setup):
    asset = asset_setup[3]
    # Simulate some accumulated depreciation
    asset.accumulated_depreciation = Decimal("40000000")
    asset.save()

    txn = AssetLifecycleService().dispose(asset, disposal_value=Decimal("10000000"), reason="Hỏng")
    # Transaction created
    assert txn.transaction_type == AssetTransaction.TransactionType.DISPOSAL
    assert txn.gl_voucher_id is not None
    # Asset status updated
    asset.refresh_from_db()
    assert asset.status == FixedAsset.Status.DISPOSED
    # Voucher posted (status=LEDGER=2)
    v = AccountingVoucher.objects.get(pk=txn.gl_voucher_id)
    assert v.status == AccountingVoucher.Status.LEDGER
    # Lines: N2141 (40M), N811 (50M loss: NBV=60M - 10M=50M), C211 (100M), N111 (10M cash)
    total_debit = sum(ln.debit_vnd for ln in v.lines.all())
    total_credit = sum(ln.credit_vnd for ln in v.lines.all())
    assert abs(total_debit - total_credit) < Decimal("1")  # balanced


def test_asset_dispose_with_gain(asset_setup):
    asset = asset_setup[3]
    asset.accumulated_depreciation = Decimal("40000000")
    asset.save()
    # NBV=60M, sell for 80M -> gain 20M (C711)
    txn = AssetLifecycleService().dispose(asset, disposal_value=Decimal("80000000"))
    v = AccountingVoucher.objects.get(pk=txn.gl_voucher_id)
    has_711 = v.lines.filter(account_code="711", credit_vnd=Decimal("20000000")).exists()
    assert has_711
    # balanced
    td = sum(ln.debit_vnd for ln in v.lines.all())
    tc = sum(ln.credit_vnd for ln in v.lines.all())
    assert abs(td - tc) < Decimal("1")


def test_asset_transfer(asset_setup):
    _, _, dept2, asset = asset_setup
    original_dept_id = asset.using_department_id
    txn = AssetLifecycleService().transfer(asset, to_department=dept2)
    assert txn.transaction_type == AssetTransaction.TransactionType.TRANSFER
    asset.refresh_from_db()
    assert asset.using_department_id == dept2.pk
    assert asset.using_department_id != original_dept_id
    assert txn.from_department_id == original_dept_id
    assert txn.to_department_id == dept2.pk


def test_asset_transaction_recorded_on_dispose(asset_setup):
    asset = asset_setup[3]
    txn = AssetLifecycleService().dispose(asset, disposal_value=Decimal("0"), reason="Test")
    assert AssetTransaction.objects.filter(asset=asset).count() == 1
    assert AssetTransaction.objects.get(pk=txn.pk).transaction_no.startswith("TL-")
