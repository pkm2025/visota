"""Dashboard view for Modern UI."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.inventory.models import StockVoucher
from apps.ledger.models import AccountPeriodBalance
from apps.ledger.models.voucher import AccountingVoucher


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard for authenticated users."""

    template_name = "modern/dashboard/index.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tổng quan"

        company = Company.objects.first()
        today = date.today()

        # KPI 1: Vouchers today
        vouchers_today = 0
        if company:
            vouchers_today = AccountingVoucher.objects.filter(
                company=company, voucher_date=today
            ).count()

        # KPI 2/3: AR (131) / AP (331) closing balances for current period
        ar_total = Decimal("0")
        ap_total = Decimal("0")
        if company:
            balance_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
            )
            # AR = TK 131 (closing debit - closing credit), customers owe us
            ar_qs = balance_qs.filter(account_code__startswith="131")
            ar_total = (
                ar_qs.aggregate(
                    d=Sum("closing_debit") - Sum("closing_credit")
                )["d"]
                or Decimal("0")
            )
            # AP = TK 331 (closing credit - closing debit), we owe vendors
            ap_qs = balance_qs.filter(account_code__startswith="331")
            ap_total = (
                ap_qs.aggregate(
                    c=Sum("closing_credit") - Sum("closing_debit")
                )["c"]
                or Decimal("0")
            )

        # KPI 4: Inventory value (sum of all stock receipts value as a rough proxy)
        # Approximate via 152/153 account balances; fall back to 0.
        inventory_value = Decimal("0")
        if company:
            inv_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
                account_code__startswith="15",
            )
            inventory_value = (
                inv_qs.aggregate(v=Sum("closing_debit") - Sum("closing_credit"))["v"]
                or Decimal("0")
            )

        ctx.update(
            {
                "vouchers_today": vouchers_today,
                "ar_total": ar_total,
                "ap_total": ap_total,
                "inventory_value": inventory_value,
                "stock_vouchers_today": (
                    StockVoucher.objects.filter(
                        company=company, voucher_date=today
                    ).count()
                    if company
                    else 0
                ),
            }
        )
        return ctx
