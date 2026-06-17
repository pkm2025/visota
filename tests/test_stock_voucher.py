"""Tests for StockVoucher + StockLedger (Phase 2 Task 5)."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.master_data.models import Product, Warehouse


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test")
    product = Product.objects.create(
        company=company,
        code="SP001",
        name="Pin",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )
    warehouse = Warehouse.objects.create(
        company=company,
        code="KHO_HN",
        name="Kho HN",
        warehouse_type="finished",
    )
    return company, product, warehouse


def test_stock_receipt_creates_ledger_entry(setup):
    """Receipt adds to stock_ledger."""
    from apps.inventory.models import StockLedger
    from apps.inventory.services import StockService

    company, product, warehouse = setup
    service = StockService(company=company)

    voucher = service.create_receipt(
        {
            "voucher_no": "PN0001",
            "voucher_date": date(2026, 6, 15),
            "warehouse_id": warehouse.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("100"),
                    "unit_cost": Decimal("50000"),
                },
            ],
        }
    )

    assert voucher.voucher_type == "receipt"
    ledger = StockLedger.objects.get(product=product, warehouse=warehouse)
    assert ledger.quantity == Decimal("100")
    assert ledger.amount == Decimal("5000000")


def test_stock_issue_decreases_quantity(setup):
    from apps.inventory.models import StockLedger
    from apps.inventory.services import StockService

    company, product, warehouse = setup
    service = StockService(company=company)

    # First receipt 100
    service.create_receipt(
        {
            "voucher_no": "PN01",
            "voucher_date": date(2026, 6, 15),
            "warehouse_id": warehouse.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("100"),
                    "unit_cost": Decimal("50000"),
                }
            ],
        }
    )

    # Then issue 30
    service.create_issue(
        {
            "voucher_no": "PX01",
            "voucher_date": date(2026, 6, 20),
            "warehouse_id": warehouse.id,
            "lines": [
                {"product_id": product.id, "quantity": Decimal("30"), "unit_cost": Decimal("50000")}
            ],
        }
    )

    ledger = StockLedger.objects.get(product=product, warehouse=warehouse)
    assert ledger.quantity == Decimal("70")  # 100 - 30
    assert ledger.amount == Decimal("3500000")  # 70 * 50k


def test_stock_transfer_moves_between_warehouses(setup):
    from apps.inventory.models import StockLedger
    from apps.inventory.services import StockService

    company, product, warehouse = setup
    other_wh = Warehouse.objects.create(
        company=company,
        code="KHO_HCM",
        name="Kho HCM",
        warehouse_type="finished",
    )
    service = StockService(company=company)

    # Receipt 100 to KHO_HN
    service.create_receipt(
        {
            "voucher_no": "PN01",
            "voucher_date": date(2026, 6, 15),
            "warehouse_id": warehouse.id,
            "lines": [
                {
                    "product_id": product.id,
                    "quantity": Decimal("100"),
                    "unit_cost": Decimal("50000"),
                }
            ],
        }
    )

    # Transfer 40 from HN to HCM
    service.create_transfer(
        {
            "voucher_no": "PC01",
            "voucher_date": date(2026, 6, 20),
            "from_warehouse_id": warehouse.id,
            "to_warehouse_id": other_wh.id,
            "lines": [
                {"product_id": product.id, "quantity": Decimal("40"), "unit_cost": Decimal("50000")}
            ],
        }
    )

    hn_ledger = StockLedger.objects.get(product=product, warehouse=warehouse)
    hcm_ledger = StockLedger.objects.get(product=product, warehouse=other_wh)
    assert hn_ledger.quantity == Decimal("60")
    assert hcm_ledger.quantity == Decimal("40")


def test_stock_current_quantity(setup):
    """Helper returns current stock level."""
    from apps.inventory.services import StockService

    company, product, warehouse = setup
    service = StockService(company=company)

    service.create_receipt(
        {
            "voucher_no": "PN01",
            "voucher_date": date(2026, 6, 15),
            "warehouse_id": warehouse.id,
            "lines": [
                {"product_id": product.id, "quantity": Decimal("50"), "unit_cost": Decimal("10000")}
            ],
        }
    )

    qty = service.current_quantity(product, warehouse)
    assert qty == Decimal("50")
