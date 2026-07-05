"""Sub-ledger book views — S07-DN (cash book), S08-DN (bank book), S35-DN (sales detail).

These are specialized account detail reports following Vietnamese
accounting regulation forms.
"""

from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ui_modern.views.report_views import _common_period_choices, _parse_period_kwargs


def _get_company(request):
    return getattr(request, "current_company", None) or Company.objects.first()


def _build_detail_book(request, account_prefixes, page_title, form_code, template):
    """Build a detail book for given account prefixes (cash/bank/sales).

    Running balance is read directly from VoucherLine.running_balance_debit and
    VoucherLine.running_balance_credit (computed by VoucherPostingService on
    post/unpost) instead of being computed in the view.
    """
    fy, period = _parse_period_kwargs(request)
    company = _get_company(request)

    # Get prior period opening balance
    prior_qs = VoucherLine.objects.filter(
        voucher__company=company,
        voucher__fiscal_year=fy,
        voucher__period__lt=period,
        voucher__status__gte=AccountingVoucher.Status.LEDGER,
    )
    from django.db.models import Q

    acc_filter = Q()
    for prefix in account_prefixes:
        acc_filter |= Q(account_code__startswith=prefix)
    prior_qs = prior_qs.filter(acc_filter)
    prior_totals = prior_qs.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
    opening = (prior_totals["d"] or Decimal("0")) - (prior_totals["c"] or Decimal("0"))

    # Current period lines — running balance comes from VoucherLine fields
    lines_qs = (
        VoucherLine.objects.select_related("voucher")
        .filter(
            voucher__company=company,
            voucher__fiscal_year=fy,
            voucher__period=period,
            voucher__status__gte=AccountingVoucher.Status.LEDGER,
        )
        .filter(acc_filter)
        .order_by("voucher__voucher_date", "voucher__voucher_no", "line_no")
    )

    rows = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    last_running = opening
    for line in lines_qs:
        debit = line.debit_vnd or Decimal("0")
        credit = line.credit_vnd or Decimal("0")
        total_debit += debit
        total_credit += credit
        # Running balance read directly from VoucherLine (computed on post)
        running = (line.running_balance_debit or Decimal("0")) - (
            line.running_balance_credit or Decimal("0")
        )
        last_running = running
        rows.append(
            {
                "voucher_no": line.voucher.voucher_no,
                "voucher_date": line.voucher.voucher_date,
                "description": line.description or line.voucher.description,
                "object_code": line.object_code,
                "object_name": line.object_name,
                "debit": debit,
                "credit": credit,
                "running": running,
            }
        )

    return {
        "page_title": f"{page_title} ({form_code})",
        "fiscal_year": fy,
        "period": period,
        "opening_balance": opening,
        "closing_balance": last_running,
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        **_common_period_choices(),
    }, template


class CashBookView(LoginRequiredMixin, TemplateView):
    """Sổ quỹ tiền mặt (S07-DN) — cash book detail."""

    template_name = "modern/reporting/detail_book.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data, _ = _build_detail_book(
            self.request, ["111"], "Sổ quỹ tiền mặt", "S07-DN", self.template_name
        )
        ctx.update(data)
        return ctx


class BankBookView(LoginRequiredMixin, TemplateView):
    """Sổ tiền gửi ngân hàng (S08-DN) — bank deposit book detail."""

    template_name = "modern/reporting/detail_book.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data, _ = _build_detail_book(
            self.request, ["112"], "Sổ tiền gửi ngân hàng", "S08-DN", self.template_name
        )
        ctx.update(data)
        return ctx


class SalesDetailView(LoginRequiredMixin, TemplateView):
    """Sổ chi tiết bán hàng (S35-DN) — sales detail report.

    Shows revenue entries (TK 511) with customer info and amounts.
    """

    template_name = "modern/reporting/detail_book.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = _get_company(self.request)

        lines_qs = (
            VoucherLine.objects.select_related("voucher")
            .filter(
                voucher__company=company,
                voucher__fiscal_year=fy,
                voucher__period=period,
                voucher__status__gte=AccountingVoucher.Status.LEDGER,
                account_code__startswith="511",
            )
            .order_by("voucher__voucher_date", "voucher__voucher_no")
        )

        rows = []
        total_revenue = Decimal("0")
        for line in lines_qs:
            amount = line.credit_vnd or Decimal("0")
            rows.append(
                {
                    "voucher_no": line.voucher.voucher_no,
                    "voucher_date": line.voucher.voucher_date,
                    "description": line.description or line.voucher.description,
                    "object_code": line.object_code,
                    "object_name": line.object_name,
                    "amount": amount,
                }
            )
            total_revenue += amount

        ctx.update(
            {
                "page_title": "Sổ chi tiết bán hàng (S35-DN)",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                "total_revenue": total_revenue,
                "is_sales_detail": True,
                **_common_period_choices(),
            }
        )
        return ctx
