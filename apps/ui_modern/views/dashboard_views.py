"""Dashboard view for Modern UI — redesigned for startup persona."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.inventory.models import StockVoucher
from apps.ledger.models import AccountPeriodBalance
from apps.ledger.models.dnsn import DnsnLedgerBalance, DnsnLedgerEntry, DnsnVoucher
from apps.ledger.models.voucher import AccountingVoucher, VoucherLine
from apps.ledger.services.voucher_posting_service import VoucherPostingService
from apps.sales.models import SalesInvoice


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard — CEO view by default, toggle to kế toán view."""

    template_name = "modern/dashboard/index.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):  # noqa: C901
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tổng quan"

        company = getattr(self.request, "current_company", None) or Company.objects.first()
        today = date.today()
        view_mode = self.request.GET.get("view", "ceo")

        # ===== DNSN dashboard detection =====
        is_dnsn = bool(company and company.accounting_regime == Company.AccountingRegime.TT58)
        ctx["is_dnsn"] = is_dnsn

        if is_dnsn:
            dnsn_metrics = self._get_dnsn_metrics(company, today)
            ctx.update(dnsn_metrics)
            # Still provide minimal context for template fallbacks
            ctx.setdefault("view_mode", view_mode)
            return ctx

        # ===== Common stats =====
        vouchers_today = 0
        total_vouchers = 0
        posted_count = 0
        draft_count = 0
        recent_vouchers = []

        if company:
            vouchers_today = AccountingVoucher.objects.filter(
                company=company, voucher_date=today
            ).count()
            total_vouchers = AccountingVoucher.objects.filter(company=company).count()
            posted_count = AccountingVoucher.objects.filter(
                company=company, status__gte=AccountingVoucher.Status.LEDGER
            ).count()
            draft_count = AccountingVoucher.objects.filter(
                company=company, status=AccountingVoucher.Status.DRAFT
            ).count()
            recent_vouchers = (
                AccountingVoucher.objects.filter(company=company)
                .select_related("company")
                .order_by("-voucher_date", "-id")[:10]
            )

        # ===== AR Aging =====
        ar_aging = {
            "current": Decimal("0"),
            "d1_30": Decimal("0"),
            "d31_60": Decimal("0"),
            "d60_plus": Decimal("0"),
            "total": Decimal("0"),
            "customer_count": 0,
        }
        if company:
            unpaid = SalesInvoice.objects.filter(company=company, status__gte=2).exclude(
                payment_status=2
            )
            for inv in unpaid:
                amount = (inv.total_amount or 0) - (inv.paid_amount or 0)
                if amount <= 0:
                    continue
                ar_aging["total"] += amount
                if inv.invoice_date:
                    days_overdue = (today - inv.invoice_date).days
                    if days_overdue <= 30:
                        ar_aging["current"] += amount
                    elif days_overdue <= 60:
                        ar_aging["d1_30"] += amount
                    elif days_overdue <= 90:
                        ar_aging["d31_60"] += amount
                    else:
                        ar_aging["d60_plus"] += amount
            ar_aging["customer_count"] = unpaid.values("customer").distinct().count()

        # ===== Cash Position =====
        cash_total = Decimal("0")
        cash_breakdown = []
        if company:
            balance_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
            )
            for prefix, label in [("111", "Tiền mặt"), ("112", "Ngân hàng")]:
                qs = balance_qs.filter(account_code__startswith=prefix)
                amount = (qs.aggregate(d=Sum("closing_debit"))["d"] or 0) - (
                    qs.aggregate(c=Sum("closing_credit"))["c"] or 0
                )
                if amount > 0:
                    cash_breakdown.append({"label": label, "amount": amount})
                    cash_total += amount

        # ===== Simple P&L (current month) =====
        pnl = {"revenue": Decimal("0"), "expense": Decimal("0"), "profit": Decimal("0")}
        if company:
            balance_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
            )
            revenue = balance_qs.filter(account_code__startswith="511").aggregate(
                s=Sum("period_credit")
            )["s"] or Decimal("0")
            expense_qs = balance_qs.filter(account_code__startswith="6")
            expense = expense_qs.aggregate(s=Sum("period_debit"))["s"] or Decimal("0")
            pnl = {
                "revenue": revenue,
                "expense": expense,
                "profit": revenue - expense,
            }

        # ===== AP Total =====
        ap_total = Decimal("0")
        if company:
            balance_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
            )
            ap_qs = balance_qs.filter(account_code__startswith="331")
            ap_total = (ap_qs.aggregate(c=Sum("closing_credit"))["c"] or 0) - (
                ap_qs.aggregate(d=Sum("closing_debit"))["d"] or 0
            )

        # ===== Inventory =====
        inventory_value = Decimal("0")
        if company:
            inv_qs = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=today.year,
                period=today.month,
                account_code__startswith="15",
            )
            inventory_value = (inv_qs.aggregate(v=Sum("closing_debit"))["v"] or 0) - (
                inv_qs.aggregate(c=Sum("closing_credit"))["c"] or 0
            )

        # ===== Tax Deadlines =====
        tax_deadlines = self._get_tax_deadlines(today)

        # ===== Unpaid invoice count (for quick link) =====
        unpaid_invoices = 0
        if company:
            unpaid_invoices = (
                SalesInvoice.objects.filter(company=company, status__gte=2)
                .exclude(payment_status=2)
                .count()
            )

        # ===== Pending approvals count (for mobile quick action) =====
        pending_approvals = 0
        if company:
            from apps.approvals.models import ApprovalRequest

            pending_approvals = ApprovalRequest.objects.filter(
                company=company, status=ApprovalRequest.Status.PENDING
            ).count()

        ctx.update(
            {
                # View mode
                "view_mode": view_mode,
                # Common
                "vouchers_today": vouchers_today,
                "total_vouchers": total_vouchers,
                "posted_count": posted_count,
                "draft_count": draft_count,
                "recent_vouchers": recent_vouchers,
                # CEO dashboard
                "cash_total": cash_total,
                "cash_breakdown": cash_breakdown,
                "pnl": pnl,
                "ar_aging": ar_aging,
                "ap_total": ap_total,
                "inventory_value": inventory_value,
                "unpaid_invoices": unpaid_invoices,
                "pending_approvals": pending_approvals,
                "tax_deadlines": tax_deadlines,
                # Stock
                "stock_vouchers_today": (
                    StockVoucher.objects.filter(company=company, voucher_date=today).count()
                    if company
                    else 0
                ),
            }
        )
        return ctx

    def _get_tax_deadlines(self, today):
        """Generate upcoming tax deadlines for dashboard widget."""
        deadlines = []
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1

        # VAT — 20th of next month
        vat_date = date(next_year, next_month, 20)
        days_left = (vat_date - today).days
        deadlines.append(
            {
                "type": "VAT (GTGT)",
                "due_date": vat_date,
                "days_left": days_left,
                "url": "/modern/reports/vat-return/",
                "urgent": days_left <= 7,
            }
        )

        # PIT — 20th of next month (same as VAT for monthly filers)
        deadlines.append(
            {
                "type": "TNCN (khấu trừ)",
                "due_date": vat_date,
                "days_left": days_left,
                "url": "/modern/reports/pit-monthly/",
                "urgent": days_left <= 7,
            }
        )

        # BHXH — last day of current month
        if today.month == 12:
            bhxh_date = date(today.year, 12, 31)
        else:
            bhxh_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        bhxh_days = (bhxh_date - today).days
        deadlines.append(
            {
                "type": "BHXH + D62",
                "due_date": bhxh_date,
                "days_left": bhxh_days,
                "url": "/modern/reports/d62/",
                "urgent": bhxh_days <= 7,
            }
        )

        # Sort by days left
        deadlines.sort(key=lambda d: d["days_left"])
        return deadlines[:4]

    def _get_dnsn_metrics(self, company, today):
        """Compute DNSN-relevant dashboard metrics from DnsnLedgerBalance.

        Returns a dict with six key widgets:
        - doanh thu hôm nay (today's revenue from DnsnLedgerEntry)
        - chi phí (current period cost)
        - lợi nhuận (revenue - cost)
        - thuế phải nộp (VAT payable + TNDN)
        - công nợ (receivables from S4a optional ledger)
        - tồn kho (inventory value from S2c ledger)

        Advanced enterprise metrics (project profitability, multi-entity
        consolidation, advanced costing) are intentionally excluded.
        """
        fiscal_year = today.year
        period = today.month

        # Revenue today — sum of revenue_amount from posted entries dated today
        revenue_today = Decimal("0")
        entries_today = DnsnLedgerEntry.objects.filter(
            company=company,
            entry_date=today,
            ledger_type__in=["s1", "s2a", "s2b", "s3a"],
        ).aggregate(s=Sum("revenue_amount"))["s"]
        if entries_today:
            revenue_today = entries_today

        # Period revenue, cost, and profit from DnsnLedgerBalance
        revenue_ledger_types = ["s1", "s2a", "s2b", "s3a"]
        cost_ledger_types = ["s2b"]
        balance_qs = DnsnLedgerBalance.objects.filter(
            company=company, fiscal_year=fiscal_year, period=period
        )

        period_revenue = balance_qs.filter(ledger_type__in=revenue_ledger_types).aggregate(
            s=Sum("period_revenue")
        )["s"] or Decimal("0")
        period_cost = balance_qs.filter(ledger_type__in=cost_ledger_types).aggregate(
            s=Sum("period_cost")
        )["s"] or Decimal("0")
        period_profit = period_revenue - period_cost

        # Tax payable — VAT closing balance from S3b + TNDN from entries
        vat_payable = balance_qs.filter(ledger_type="s3b").aggregate(s=Sum("closing_vat"))[
            "s"
        ] or Decimal("0")
        # TNDN amount from ledger entries (actual tax accrued)
        tndn_from_entries = DnsnLedgerEntry.objects.filter(
            company=company,
            fiscal_year=fiscal_year,
            period=period,
            ledger_type__in=["s2b"],
        ).aggregate(s=Sum("tndn_amount"))["s"] or Decimal("0")
        tax_payable = vat_payable + tndn_from_entries

        # Receivables (công nợ) — from S4a optional ledger if enabled
        receivable_total = Decimal("0")
        s4a_balance = balance_qs.filter(ledger_type="s4a").first()
        if s4a_balance:
            receivable_total = s4a_balance.closing_cash  # S4a uses cash column for net AR

        # Also compute from DnsnVoucher partner info as fallback
        if receivable_total == 0:
            # Sum unpaid sales-type vouchers
            received = DnsnVoucher.objects.filter(
                company=company,
                voucher_type=DnsnVoucher.VoucherType.PHIEU_THU,
                status__in=[DnsnVoucher.Status.POSTED, DnsnVoucher.Status.LOCKED],
                voucher_date__year=today.year,
            ).aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
            invoiced = DnsnVoucher.objects.filter(
                company=company,
                voucher_type=DnsnVoucher.VoucherType.HOA_DON_BAN_HANG,
                status__in=[DnsnVoucher.Status.POSTED, DnsnVoucher.Status.LOCKED],
                voucher_date__year=today.year,
            ).aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
            receivable_total = invoiced - received

        # Payables (công nợ phải trả)
        payable_total = Decimal("0")
        s4a_payable = DnsnLedgerEntry.objects.filter(
            company=company,
            ledger_type="s4a",
            entry_date__year=today.year,
        ).aggregate(s=Sum("cash_out"))["s"] or Decimal("0")
        if s4a_payable:
            payable_total = s4a_payable

        # Inventory value — from S2c ledger closing balance
        inventory_value = Decimal("0")
        s2c_balance = balance_qs.filter(ledger_type="s2c").first()
        if s2c_balance:
            # S2c uses total_amount for inventory value
            inventory_value = s2c_balance.closing_cash  # cash column repurposed for inventory
        else:
            # Fallback: sum of inventory entries (in - out)
            inv_in = DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type="s2c",
                entry_date__year=today.year,
            ).aggregate(s=Sum("cash_in"))["s"] or Decimal("0")
            inv_out = DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type="s2c",
                entry_date__year=today.year,
            ).aggregate(s=Sum("cash_out"))["s"] or Decimal("0")
            inventory_value = inv_in - inv_out

        # Cash total — from S2d ledger
        cash_total = Decimal("0")
        s2d_balance = balance_qs.filter(ledger_type="s2d").first()
        if s2d_balance:
            cash_total = s2d_balance.closing_cash
        else:
            cash_in = DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type="s2d",
                entry_date__year=today.year,
            ).aggregate(s=Sum("cash_in") + Sum("bank_in"))["s"] or Decimal("0")
            cash_out = DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type="s2d",
                entry_date__year=today.year,
            ).aggregate(s=Sum("cash_out") + Sum("bank_out"))["s"] or Decimal("0")
            cash_total = cash_in - cash_out

        # Recent DNSN vouchers
        recent_dnsn_vouchers = DnsnVoucher.objects.filter(company=company).order_by(
            "-voucher_date", "-id"
        )[:10]

        # DNSN vouchers today count
        dnsn_vouchers_today = DnsnVoucher.objects.filter(
            company=company, voucher_date=today
        ).count()

        # Tax deadlines (reuse existing method for simplicity)
        tax_deadlines = self._get_tax_deadlines(today)

        return {
            "view_mode": "dnsn",
            "dnsn_revenue_today": revenue_today,
            "dnsn_period_revenue": period_revenue,
            "dnsn_period_cost": period_cost,
            "dnsn_period_profit": period_profit,
            "dnsn_tax_payable": tax_payable,
            "dnsn_vat_payable": vat_payable,
            "dnsn_tndn_payable": tndn_from_entries,
            "dnsn_receivable_total": receivable_total,
            "dnsn_payable_total": payable_total,
            "dnsn_inventory_value": inventory_value,
            "dnsn_cash_total": cash_total,
            "dnsn_recent_vouchers": recent_dnsn_vouchers,
            "dnsn_vouchers_today": dnsn_vouchers_today,
            "dnsn_tax_deadlines": tax_deadlines,
            # Keep common context keys for template compatibility
            "cash_total": cash_total,
            "cash_breakdown": [],
            "pnl": {
                "revenue": period_revenue,
                "expense": period_cost,
                "profit": period_profit,
            },
            "ar_aging": {
                "current": receivable_total,
                "d1_30": Decimal("0"),
                "d31_60": Decimal("0"),
                "d60_plus": Decimal("0"),
                "total": receivable_total,
                "customer_count": 0,
            },
            "ap_total": payable_total,
            "inventory_value": inventory_value,
            "unpaid_invoices": 0,
            "pending_approvals": 0,
            "vouchers_today": dnsn_vouchers_today,
            "total_vouchers": DnsnVoucher.objects.filter(company=company).count(),
            "posted_count": DnsnVoucher.objects.filter(
                company=company,
                status__in=[DnsnVoucher.Status.POSTED, DnsnVoucher.Status.LOCKED],
            ).count(),
            "draft_count": DnsnVoucher.objects.filter(
                company=company, status=DnsnVoucher.Status.DRAFT
            ).count(),
            "recent_vouchers": [],
            "tax_deadlines": tax_deadlines,
            "stock_vouchers_today": 0,
        }


class QuickExpenseView(LoginRequiredMixin, TemplateView):
    """Quick expense: 1-line form → auto-generate voucher."""

    template_name = "modern/dashboard/quick_expense.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ghi chi nhanh"
        ctx["expense_categories"] = [
            ("641", "Chi phí bán hàng"),
            ("642", "Chi phí quản lý DN"),
            ("635", "Chi phí tài chính"),
            ("622", "Chi phí nhân công"),
            ("632", "Giá vốn hàng bán"),
            ("242", "Chi phí trả trước"),
            ("1331", "Thuế GTGT được khấu trừ"),
        ]
        return ctx

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty.")
            return redirect("ui_modern:dashboard")

        amount_str = request.POST.get("amount", "0").strip()
        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Số tiền không hợp lệ.")
            return redirect("ui_modern:dashboard_quick_expense")

        if amount < 1000:
            messages.error(request, "Số tiền tối thiểu 1.000đ.")
            return redirect("ui_modern:dashboard_quick_expense")

        expense_account = request.POST.get("expense_account", "642")
        payment_account = request.POST.get("payment_account", "111")
        description = request.POST.get("description", "").strip() or "Chi phí"
        has_vat = request.POST.get("has_vat") == "on"
        today = date.today()

        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=today.year,
            period=today.month,
            voucher_no=f"QEXP-{today.strftime('%y%m%d')}-{AccountingVoucher.objects.filter(company=company, voucher_no__startswith='QEXP').count() + 1:04d}",
            voucher_type=AccountingVoucher.VoucherType.CASH_PAYMENT,
            voucher_date=today,
            description=f"[Chi nhanh] {description}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=amount,
            status=AccountingVoucher.Status.DRAFT,
            created_by=request.user,
        )

        line_no = 1
        if has_vat:
            net_amount = (amount / Decimal("1.1")).quantize(Decimal("0.0001"))
            vat_amount = amount - net_amount
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=expense_account,
                debit_vnd=net_amount,
                description=description,
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="1331",
                debit_vnd=vat_amount,
                description=f"VAT (10%) — {description}",
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=payment_account,
                credit_vnd=amount,
                description=description,
            )
        else:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=expense_account,
                debit_vnd=amount,
                description=description,
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=payment_account,
                credit_vnd=amount,
                description=description,
            )

        try:
            VoucherPostingService().post(voucher)
            messages.success(
                request,
                f"Đã ghi chi {amount:,.0f}đ → TK {expense_account}. Phiếu {voucher.voucher_no} đã ghi sổ.",
            )
        except Exception as e:
            messages.warning(request, f"Phiếu đã tạo nhưng chưa ghi sổ: {e}")
        return redirect("ui_modern:dashboard")
