"""Reporting views — trial balance, etc."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import YtdBalanceService
from apps.reporting.services import (
    BalanceSheetService,
    PnLService,
    VATReturnService,
)
from apps.reporting.services.hr_reports import (
    D62ReportService,
    LaborUsageReportService,
    PITMonthlyReportService,
    SalaryFundReportService,
)
from apps.ui_modern.mixins import require_current_company


class TrialBalanceView(LoginRequiredMixin, TemplateView):
    """Bảng cân đối tài khoản (S06-DN).

    Computes YTD opening / period / closing using ``YtdBalanceService``
    so that selecting period N shows cumulative year-to-date balances
    (period-0 opening + movements of periods 1..N).
    """

    template_name = "modern/reporting/trial_balance.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)
        rows = YtdBalanceService(company=company, fiscal_year=fiscal_year, period=period).fetch()

        total_opening_d = Decimal("0")
        total_opening_c = Decimal("0")
        total_period_d = Decimal("0")
        total_period_c = Decimal("0")
        total_closing_d = Decimal("0")
        total_closing_c = Decimal("0")

        active_rows = []
        for r in rows:
            if not r.has_activity():
                continue
            active_rows.append(r)
            total_opening_d += r.opening_debit
            total_opening_c += r.opening_credit
            total_period_d += r.period_debit
            total_period_c += r.period_credit
            total_closing_d += r.closing_debit
            total_closing_c += r.closing_credit

        ctx.update(
            {
                "page_title": "Bảng cân đối tài khoản",
                "fiscal_year": fiscal_year,
                "period": period,
                "balances": active_rows,
                "total_opening_debit": total_opening_d,
                "total_opening_credit": total_opening_c,
                "total_period_debit": total_period_d,
                "total_period_credit": total_period_c,
                "total_closing_debit": total_closing_d,
                "total_closing_credit": total_closing_c,
                "is_balanced": total_closing_d == total_closing_c,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class BalanceSheetView(LoginRequiredMixin, TemplateView):
    """Báo cáo tình hình tài chính (B01a-DN)."""

    template_name = "modern/reporting/balance_sheet.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)
        if company:
            data = BalanceSheetService(company=company).generate(fiscal_year, period)
            ctx.update(data)

        ctx.update(
            {
                "page_title": "Báo cáo tình hình tài chính (B01-DN)",
                "fiscal_year": fiscal_year,
                "period": period,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class PnLView(LoginRequiredMixin, TemplateView):
    """Báo cáo kết quả hoạt động kinh doanh (B02a-DN)."""

    template_name = "modern/reporting/pnl.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)
        if company:
            data = PnLService(company=company).generate(fiscal_year, period)
            ctx.update(data)

        ctx.update(
            {
                "page_title": "Kết quả hoạt động kinh doanh (B02-DN)",
                "fiscal_year": fiscal_year,
                "period": period,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class VATReturnView(LoginRequiredMixin, TemplateView):
    """Tờ khai thuế GTGT (01/GTGT)."""

    template_name = "modern/reporting/vat_return.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)
        # Compute unconditionally so empty periods render zeros (VAL-M2-011)
        # and the recalculate button always re-runs the engine (VAL-M2-010).
        data = VATReturnService(company=company).generate(fiscal_year, period)
        ctx.update(data)

        ctx.update(
            {
                "page_title": "Tờ khai thuế GTGT (01/GTGT)",
                "fiscal_year": fiscal_year,
                "period": period,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class GeneralJournalView(LoginRequiredMixin, TemplateView):
    """Sổ nhật ký chung (S03a-DN)."""

    template_name = "modern/reporting/general_journal.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)
        vouchers_qs = AccountingVoucher.objects.all()
        if company:
            vouchers_qs = vouchers_qs.filter(company=company)
        vouchers = (
            vouchers_qs.filter(fiscal_year=fiscal_year, period=period)
            .prefetch_related("lines")
            .order_by("voucher_date", "voucher_no")
        )

        # Flatten into rows: each line -> one row
        rows = []
        total_amount = Decimal("0")
        for v in vouchers:
            lines = list(v.lines.all())
            if not lines:
                rows.append(
                    {
                        "voucher_date": v.voucher_date,
                        "voucher_no": v.voucher_no,
                        "description": v.description,
                        "debit_account": "",
                        "credit_account": "",
                        "amount": Decimal("0"),
                    }
                )
                continue
            for line in lines:
                amount = line.debit_vnd or line.credit_vnd or Decimal("0")
                if line.debit_vnd and line.debit_vnd > 0:
                    debit_acc = line.account_code
                    credit_acc = ""
                else:
                    debit_acc = ""
                    credit_acc = line.account_code
                rows.append(
                    {
                        "voucher_date": v.voucher_date,
                        "voucher_no": v.voucher_no,
                        "description": line.description or v.description,
                        "debit_account": debit_acc,
                        "credit_account": credit_acc,
                        "amount": amount,
                    }
                )
                total_amount += amount

        ctx.update(
            {
                "page_title": "Sổ nhật ký chung (S03a-DN)",
                "fiscal_year": fiscal_year,
                "period": period,
                "rows": rows,
                "vouchers": vouchers,
                "total_amount": total_amount,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class GeneralLedgerView(LoginRequiredMixin, TemplateView):
    """Sổ cái tài khoản (S03b-DN)."""

    template_name = "modern/reporting/general_ledger.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        account_code = self.request.GET.get("account_code", "").strip()

        company = require_current_company(self.request)
        lines_qs = VoucherLine.objects.select_related("voucher")
        if company:
            lines_qs = lines_qs.filter(voucher__company=company)
        if account_code:
            # Prefix match: 131 -> 131, 1311, 1312...
            lines_qs = lines_qs.filter(account_code__startswith=account_code)

        lines_qs = lines_qs.filter(
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
        ).order_by("voucher__voucher_date", "voucher__voucher_no", "line_no")

        # Determine if account is debit-natured (assets, expenses: 1, 6)
        # vs credit-natured (liabilities, equity, revenue: 2, 3, 4, 5)
        opening_balance = Decimal("0")
        if account_code and account_code[0] in ("1", "6"):
            # Debit natured — opening is debit
            opening_balance = self._compute_opening(
                company, account_code, fiscal_year, period, debit_natured=True
            )
        elif account_code and account_code[0] in ("2", "3", "4", "5"):
            opening_balance = self._compute_opening(
                company, account_code, fiscal_year, period, debit_natured=False
            )

        # Compute running balance per row
        rows = []
        running = opening_balance
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for line in lines_qs:
            debit = line.debit_vnd or Decimal("0")
            credit = line.credit_vnd or Decimal("0")
            total_debit += debit
            total_credit += credit
            # Determine sign based on account nature (first digit)
            if account_code and account_code[0] in ("2", "3", "4", "5"):
                running = running - debit + credit
            else:
                running = running + debit - credit
            rows.append(
                {
                    "voucher_no": line.voucher.voucher_no,
                    "voucher_date": line.voucher.voucher_date,
                    "description": line.description or line.voucher.description,
                    "offset_account": "",  # Could be enriched later
                    "debit": debit,
                    "credit": credit,
                    "running": running,
                }
            )

        ctx.update(
            {
                "page_title": f"Sổ cái TK {account_code}" if account_code else "Sổ cái",
                "fiscal_year": fiscal_year,
                "period": period,
                "account_code": account_code,
                "opening_balance": opening_balance,
                "closing_balance": running,
                "rows": rows,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "period_choices": list(range(1, 13)),
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx

    def _compute_opening(self, company, account_code, fiscal_year, period, debit_natured):
        """Compute opening balance for account up to (but not including) the period."""
        prior_lines = VoucherLine.objects.filter(
            account_code__startswith=account_code,
            voucher__fiscal_year=fiscal_year,
        )
        if company:
            prior_lines = prior_lines.filter(voucher__company=company)
        # Lines from periods 1..period-1 of the same fiscal year
        prior_lines = prior_lines.filter(voucher__period__lt=period)
        totals = prior_lines.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
        d = totals["d"] or Decimal("0")
        c = totals["c"] or Decimal("0")
        if debit_natured:
            return d - c
        return c - d


# --- HR Reports (Task 4) ---


def _parse_period_kwargs(request):
    """Extract fiscal_year + period (int) from query params."""
    today = date.today()
    try:
        fiscal_year = int(request.GET.get("fiscal_year", today.year))
    except (TypeError, ValueError):
        fiscal_year = today.year
    try:
        period = int(request.GET.get("period", today.month))
    except (TypeError, ValueError):
        period = today.month
    return fiscal_year, period


def _common_period_choices():
    return {
        "period_choices": list(range(1, 13)),
        "year_choices": [2024, 2025, 2026, 2027],
    }


class D62ReportView(LoginRequiredMixin, TemplateView):
    """Báo cáo D62 — Bảng kê đóng BHXH hàng tháng."""

    template_name = "modern/reporting/d62.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fiscal_year, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)
        if company:
            ctx.update(D62ReportService(company=company).generate(fiscal_year, period))
        ctx.update(
            {
                "page_title": "Báo cáo D62 — Bảng kê BHXH",
                "fiscal_year": fiscal_year,
                "period": period,
                **_common_period_choices(),
            }
        )
        return ctx


class LaborUsageReportView(LoginRequiredMixin, TemplateView):
    """Tình hình sử dụng lao động theo phòng ban."""

    template_name = "modern/reporting/labor_usage.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        company = require_current_company(self.request)
        if company:
            ctx.update(LaborUsageReportService(company=company).generate(fiscal_year))
        ctx.update(
            {
                "page_title": "Tình hình sử dụng lao động",
                "fiscal_year": fiscal_year,
                "year_choices": [2024, 2025, 2026, 2027],
            }
        )
        return ctx


class SalaryFundReportView(LoginRequiredMixin, TemplateView):
    """Quỹ lương kỳ — tổng hợp PayrollRun."""

    template_name = "modern/reporting/salary_fund.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fiscal_year, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)
        if company:
            ctx.update(SalaryFundReportService(company=company).generate(fiscal_year, period))
        ctx.update(
            {
                "page_title": "Quỹ lương kỳ",
                "fiscal_year": fiscal_year,
                "period": period,
                **_common_period_choices(),
            }
        )
        return ctx


class PITMonthlyReportView(LoginRequiredMixin, TemplateView):
    """Tờ khai thuế TNCN hàng tháng."""

    template_name = "modern/reporting/pit_monthly.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fiscal_year, period = _parse_period_kwargs(self.request)
        company = require_current_company(self.request)
        if company:
            ctx.update(PITMonthlyReportService(company=company).generate(fiscal_year, period))
        ctx.update(
            {
                "page_title": "Tờ khai thuế TNCN (tháng)",
                "fiscal_year": fiscal_year,
                "period": period,
                **_common_period_choices(),
            }
        )
        return ctx


class SubLedgerView(LoginRequiredMixin, TemplateView):
    """Sổ chi tiết tài khoản — chi tiết công nợ KH (131) / NCC (331)."""

    template_name = "modern/reporting/sub_ledger.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month
        account_code = self.request.GET.get("account_code", "131").strip()
        # template=vnd|fc — fc adds foreign-currency columns
        tmpl = (self.request.GET.get("template") or "vnd").strip().lower()
        tmpl = "fc" if tmpl == "fc" else "vnd"

        company = require_current_company(self.request)

        # Build lines grouped by object_code (customer/vendor)
        lines_qs = (
            VoucherLine.objects.select_related("voucher")
            .filter(
                voucher__company=company,
                account_code__startswith=account_code,
                voucher__fiscal_year=fiscal_year,
            )
            .order_by("object_code", "voucher__voucher_date", "voucher__voucher_no")
        )

        # Group by object_code
        from collections import OrderedDict

        parties = OrderedDict()
        totals = {
            "debit": Decimal("0"),
            "credit": Decimal("0"),
            "debit_fc": Decimal("0"),
            "credit_fc": Decimal("0"),
        }
        for line in lines_qs:
            code = line.object_code or "(không rõ)"
            if code not in parties:
                parties[code] = {
                    "name": line.object_name or code,
                    "lines": [],
                    "debit": Decimal("0"),
                    "credit": Decimal("0"),
                    "debit_fc": Decimal("0"),
                    "credit_fc": Decimal("0"),
                    "balance": Decimal("0"),
                }
            parties[code]["lines"].append(line)
            debit = line.debit_vnd or Decimal("0")
            credit = line.credit_vnd or Decimal("0")
            debit_fc = line.debit_fc or Decimal("0")
            credit_fc = line.credit_fc or Decimal("0")
            parties[code]["debit"] += debit
            parties[code]["credit"] += credit
            parties[code]["debit_fc"] += debit_fc
            parties[code]["credit_fc"] += credit_fc
            totals["debit"] += debit
            totals["credit"] += credit
            totals["debit_fc"] += debit_fc
            totals["credit_fc"] += credit_fc

        # Compute running balance per party
        for p in parties.values():
            if account_code.startswith("1") or account_code.startswith("6"):
                # Debit-natured: balance = debit - credit
                p["balance"] = p["debit"] - p["credit"]
            else:
                # Credit-natured: balance = credit - debit
                p["balance"] = p["credit"] - p["debit"]

        ctx.update(
            {
                "page_title": f"Sổ chi tiết TK {account_code}",
                "fiscal_year": fiscal_year,
                "period": period,
                "account_code": account_code,
                "template": tmpl,
                "is_fc": tmpl == "fc",
                "parties": parties,
                "totals": totals,
                **_common_period_choices(),
            }
        )
        return ctx


class BookEntryRegisterView(LoginRequiredMixin, TemplateView):
    """Sổ đăng ký chứng từ ghi sổ (S02a-DN) — alternate bookkeeping form.

    In the "chứng từ ghi sổ" method, transactions are first recorded in
    subsidiary books, then summarized into "chứng từ ghi sổ" entries which
    are posted to the general ledger. This register lists all vouchers
    in CTGS format: sequential number, date, description, debit/credit totals.
    """

    template_name = "modern/reporting/book_entry_register.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(self.request)

        vouchers = AccountingVoucher.objects.filter(
            company=company,
            fiscal_year=fiscal_year,
            period=period,
            status__gte=AccountingVoucher.Status.LEDGER,
        ).order_by("voucher_date", "voucher_no")

        rows = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        seq = 0
        for v in vouchers:
            seq += 1
            line_totals = v.lines.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
            debit = line_totals["d"] or Decimal("0")
            credit = line_totals["c"] or Decimal("0")
            total_debit += debit
            total_credit += credit
            rows.append(
                {
                    "seq": seq,
                    "voucher_no": v.voucher_no,
                    "voucher_date": v.voucher_date,
                    "voucher_type": v.get_voucher_type_display(),
                    "description": v.description,
                    "debit": debit,
                    "credit": credit,
                }
            )

        ctx.update(
            {
                "page_title": "Sổ đăng ký CTGS (S02a-DN)",
                "fiscal_year": fiscal_year,
                "period": period,
                "rows": rows,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "is_balanced": total_debit == total_credit,
                **_common_period_choices(),
            }
        )
        return ctx
