"""Cost accounting service — tập hợp chi phí, tính giá thành, kết chuyển.

TT133 accounts:
  621 — Chi phí NVL trực tiếp
  622 — Chi phí nhân công trực tiếp
  623 — Chi phí sản xuất chung
  154 — Chi phí SXKD dở dang
  632 — Giá vốn hàng bán

Flow:
  1. Tập hợp CP: query VoucherLine for TK 621/622/623 in period
  2. Tính giá thành: allocate total cost to finished goods output
  3. Kết chuyển: N154/C621,622,623 then N632/C154
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.ledger.models import AccountingVoucher, VoucherLine


@dataclass
class CostSummary:
    """Cost summary for a production period."""

    materials: Decimal = Decimal("0")  # TK 621
    labor: Decimal = Decimal("0")  # TK 622
    overhead: Decimal = Decimal("0")  # TK 623
    total_input: Decimal = Decimal("0")  # 621 + 622 + 623

    # Output
    output_quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    cogs: Decimal = Decimal("0")  # TK 632

    # WIP
    wip_opening: Decimal = Decimal("0")
    wip_closing: Decimal = Decimal("0")

    @property
    def total_production_cost(self):
        return self.total_input + self.wip_opening - self.wip_closing


class CostingService:
    """Calculate production cost (giá thành) for a period."""

    DIRECT_MATERIALS = "621"
    DIRECT_LABOR = "622"
    MANUFACTURING_OVERHEAD = "623"
    WIP = "154"
    COGS = "632"
    FINISHED_GOODS = "155"

    def __init__(self, company):
        self.company = company

    def collect_costs(self, fiscal_year: int, period: int) -> CostSummary:
        """Collect all production costs for the period from voucher lines."""
        base_qs = VoucherLine.objects.filter(
            voucher__company=self.company,
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
            voucher__status__gte=AccountingVoucher.Status.LEDGER,
        )

        materials = self._sum_debit(base_qs, self.DIRECT_MATERIALS)
        labor = self._sum_debit(base_qs, self.DIRECT_LABOR)
        overhead = self._sum_debit(base_qs, self.MANUFACTURING_OVERHEAD)

        total_input = materials + labor + overhead

        # WIP (TK 154): closing balance from debit - credit
        wip_debit = self._sum_debit(base_qs, self.WIP)
        wip_credit = self._sum_credit(base_qs, self.WIP)
        wip_movement = wip_debit - wip_credit

        # COGS (TK 632): already recorded cost of goods sold
        cogs = self._sum_debit(base_qs, self.COGS)

        return CostSummary(
            materials=materials,
            labor=labor,
            overhead=overhead,
            total_input=total_input,
            cogs=cogs,
            wip_closing=wip_movement if wip_movement > 0 else Decimal("0"),
        )

    def calculate_unit_cost(
        self,
        fiscal_year: int,
        period: int,
        output_quantity: Decimal,
    ) -> CostSummary:
        """Calculate unit cost for finished goods output.

        Args:
            output_quantity: number of finished units produced this period.
        """
        summary = self.collect_costs(fiscal_year, period)
        if output_quantity > 0:
            summary.output_quantity = output_quantity
            summary.unit_cost = (summary.total_production_cost / output_quantity).quantize(
                Decimal("0.0001")
            )
        return summary

    def create_closing_entry(
        self,
        fiscal_year: int,
        period: int,
        created_by=None,
    ) -> AccountingVoucher | None:
        """Create period-end cost closing voucher.

        N154 / C621, C622, C623  — tập hợp CP vào WIP
        N632 / C154              — kết chuyển giá vốn
        """
        summary = self.collect_costs(fiscal_year, period)
        if summary.total_input == 0:
            return None

        today = date.today()
        count = AccountingVoucher.objects.filter(
            company=self.company,
            voucher_no__startswith="GTHANH",
            fiscal_year=fiscal_year,
            period=period,
        ).count()
        voucher_no = f"GTHANH-{fiscal_year}{period:02d}-{count + 1:03d}"

        voucher = AccountingVoucher.objects.create(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            voucher_no=voucher_no,
            voucher_type=AccountingVoucher.VoucherType.CLOSING,
            voucher_date=today,
            description=f"Kết chuyển giá thành kỳ {period}/{fiscal_year}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=summary.total_input,
            status=AccountingVoucher.Status.DRAFT,
            created_by=created_by,
        )

        line_no = 1
        # N154 — tổng hợp CP sản xuất
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code=self.WIP,
            debit_vnd=summary.total_input,
            description="Tổng hợp CP SXKD",
        )
        line_no += 1

        # C621 — NVL trực tiếp
        if summary.materials > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=self.DIRECT_MATERIALS,
                credit_vnd=summary.materials,
                description="K/C CP NVL trực tiếp",
            )
            line_no += 1

        # C622 — Nhân công trực tiếp
        if summary.labor > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=self.DIRECT_LABOR,
                credit_vnd=summary.labor,
                description="K/C CP nhân công trực tiếp",
            )
            line_no += 1

        # C623 — SX chung
        if summary.overhead > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=self.MANUFACTURING_OVERHEAD,
                credit_vnd=summary.overhead,
                description="K/C CP SX chung",
            )

        return voucher

    def _sum_debit(self, qs, account_prefix: str) -> Decimal:
        result = qs.filter(account_code__startswith=account_prefix).aggregate(s=Sum("debit_vnd"))
        return result["s"] or Decimal("0")

    def _sum_credit(self, qs, account_prefix: str) -> Decimal:
        result = qs.filter(account_code__startswith=account_prefix).aggregate(s=Sum("credit_vnd"))
        return result["s"] or Decimal("0")
