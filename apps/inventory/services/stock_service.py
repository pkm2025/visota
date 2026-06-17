"""StockService — receipt/issue/transfer."""

from decimal import Decimal

from django.db import transaction

from apps.inventory.models import StockLedger, StockVoucher, StockVoucherLine
from apps.master_data.models import Product, Warehouse


class StockService:
    """Service for creating stock movements and updating the stock ledger."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def create_receipt(self, data: dict) -> StockVoucher:
        return self._create_voucher(StockVoucher.VoucherType.RECEIPT, data)

    @transaction.atomic
    def create_issue(self, data: dict) -> StockVoucher:
        return self._create_voucher(StockVoucher.VoucherType.ISSUE, data)

    @transaction.atomic
    def create_transfer(self, data: dict) -> StockVoucher:
        """Transfer: deduct from warehouse, add to to_warehouse."""
        from_wh = Warehouse.objects.get(id=data["from_warehouse_id"], company=self.company)
        to_wh = Warehouse.objects.get(id=data["to_warehouse_id"], company=self.company)

        voucher = StockVoucher.objects.create(
            company=self.company,
            voucher_type=StockVoucher.VoucherType.TRANSFER,
            voucher_no=data["voucher_no"],
            voucher_date=data["voucher_date"],
            warehouse=from_wh,
            to_warehouse=to_wh,
            reason=data.get("reason", ""),
        )

        for idx, line_data in enumerate(data["lines"], start=1):
            product = Product.objects.get(id=line_data["product_id"], company=self.company)
            qty = Decimal(str(line_data["quantity"]))
            unit_cost = Decimal(str(line_data.get("unit_cost", 0)))
            amount = qty * unit_cost

            StockVoucherLine.objects.create(
                voucher=voucher,
                line_no=idx,
                product=product,
                quantity=qty,
                unit_cost=unit_cost,
                amount=amount,
                description=line_data.get("description", ""),
                unit_id=product.unit_id,
            )

            # Decrement from-wh, increment to-wh
            self._adjust_ledger(product, from_wh, -qty, -amount, data["voucher_date"])
            self._adjust_ledger(product, to_wh, +qty, +amount, data["voucher_date"])

        return voucher

    def _create_voucher(self, voucher_type, data: dict) -> StockVoucher:
        warehouse = Warehouse.objects.get(id=data["warehouse_id"], company=self.company)

        voucher = StockVoucher.objects.create(
            company=self.company,
            voucher_type=voucher_type,
            voucher_no=data["voucher_no"],
            voucher_date=data["voucher_date"],
            warehouse=warehouse,
            reason=data.get("reason", ""),
        )

        # Receipt adds (+), Issue subtracts (-)
        sign = Decimal("+1") if voucher_type == StockVoucher.VoucherType.RECEIPT else Decimal("-1")

        for idx, line_data in enumerate(data["lines"], start=1):
            product = Product.objects.get(id=line_data["product_id"], company=self.company)
            qty = Decimal(str(line_data["quantity"]))
            unit_cost = Decimal(str(line_data.get("unit_cost", 0)))
            amount = qty * unit_cost

            StockVoucherLine.objects.create(
                voucher=voucher,
                line_no=idx,
                product=product,
                quantity=qty,
                unit_cost=unit_cost,
                amount=amount,
                description=line_data.get("description", ""),
                unit_id=product.unit_id,
            )

            self._adjust_ledger(product, warehouse, sign * qty, sign * amount, data["voucher_date"])

        return voucher

    def _adjust_ledger(self, product, warehouse, qty_delta, amount_delta, txn_date):
        ledger, _ = StockLedger.objects.get_or_create(
            company=self.company,
            product=product,
            warehouse=warehouse,
        )
        ledger.quantity += qty_delta
        ledger.amount += amount_delta
        ledger.last_transaction_date = txn_date
        ledger.transaction_count += 1
        ledger.recalculate_avg_cost()
        ledger.save()

    def current_quantity(self, product, warehouse) -> Decimal:
        try:
            return StockLedger.objects.get(
                company=self.company, product=product, warehouse=warehouse
            ).quantity
        except StockLedger.DoesNotExist:
            return Decimal("0")
