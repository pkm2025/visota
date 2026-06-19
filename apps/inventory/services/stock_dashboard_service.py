"""Stock dashboard service — warehouse summaries, low-stock, valuation."""

from decimal import Decimal

from django.db.models import Sum

from apps.inventory.models import StockLedger
from apps.master_data.models import Product, Warehouse


class StockDashboardService:
    @staticmethod
    def get_summary(company):
        """Per-warehouse: total qty, total value, product count, low stock count."""
        warehouses = Warehouse.objects.filter(company=company, is_active=True)
        summary = []
        for wh in warehouses:
            ledger = StockLedger.objects.filter(company=company, warehouse=wh)
            total_qty = ledger.aggregate(t=Sum("quantity"))["t"] or Decimal("0")
            total_value = ledger.aggregate(v=Sum("amount"))["v"] or Decimal("0")
            product_count = ledger.filter(quantity__gt=0).count()

            # Low stock: products with min_stock > 0 whose total qty in this
            # warehouse is below min_stock threshold.
            low_stock = 0
            for prod in Product.objects.filter(company=company, is_active=True, min_stock__gt=0):
                qty = StockLedger.objects.filter(product=prod, warehouse=wh).aggregate(
                    t=Sum("quantity")
                )["t"] or Decimal("0")
                if prod.min_stock > 0 and qty < prod.min_stock:
                    low_stock += 1

            summary.append(
                {
                    "warehouse": wh,
                    "total_quantity": total_qty,
                    "total_value": total_value,
                    "product_count": product_count,
                    "low_stock_count": low_stock,
                }
            )
        return summary

    @staticmethod
    def get_low_stock_products(company):
        """Products below min_stock threshold (total across warehouses)."""
        products = Product.objects.filter(company=company, is_active=True, min_stock__gt=0)
        alerts = []
        for p in products:
            ledgers = StockLedger.objects.filter(product=p)
            total_qty = ledgers.aggregate(t=Sum("quantity"))["t"] or Decimal("0")
            if total_qty < p.min_stock:
                first = ledgers.first()
                alerts.append(
                    {
                        "product": p,
                        "current": total_qty,
                        "min": p.min_stock,
                        "warehouse": first.warehouse if first else None,
                    }
                )
        return alerts

    @staticmethod
    def get_stock_valuation(company, method="weighted_avg"):
        """Stock valuation by product+warehouse ledger row."""
        ledgers = StockLedger.objects.filter(company=company, quantity__gt=0).select_related(
            "product", "warehouse"
        )
        valuation = []
        for row in ledgers:
            valuation.append(
                {
                    "product_code": row.product.code,
                    "product_name": row.product.name,
                    "warehouse": row.warehouse.code,
                    "quantity": row.quantity,
                    "avg_cost": row.avg_cost,
                    "total_value": row.amount,
                }
            )
        return valuation

    @staticmethod
    def get_stock_card(company, product_id, warehouse_id=None):
        """Stock card (thẻ kho): running ledger for one product (+optional wh)."""
        from apps.inventory.models import StockVoucherLine

        lines_qs = StockVoucherLine.objects.filter(
            voucher__company=company,
            product_id=product_id,
        ).select_related("voucher", "voucher__warehouse")
        if warehouse_id:
            lines_qs = lines_qs.filter(voucher__warehouse_id=warehouse_id)
        lines_qs = lines_qs.order_by("voucher__voucher_date", "voucher__id", "line_no")

        running = Decimal("0")
        rows = []
        for ln in lines_qs:
            vtype = ln.voucher.voucher_type
            if vtype == "issue":
                qty_signed = -ln.quantity
            elif vtype == "receipt":
                qty_signed = ln.quantity
            else:
                qty_signed = Decimal("0")  # transfer handled separately
            running += qty_signed
            rows.append(
                {
                    "date": ln.voucher.voucher_date,
                    "voucher_no": ln.voucher.voucher_no,
                    "voucher_type": vtype,
                    "in_qty": ln.quantity if vtype == "receipt" else Decimal("0"),
                    "out_qty": ln.quantity if vtype == "issue" else Decimal("0"),
                    "unit_cost": ln.unit_cost,
                    "balance": running,
                }
            )
        return rows
