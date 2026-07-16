"""Sub-ledger book views — S07-DN (cash book), S08-DN (bank book), S35-DN (sales detail).

These are specialized account detail reports following Vietnamese
accounting regulation forms.

Each view accepts a ``template=vnd|fc`` query parameter. When ``fc`` is
selected, three additional foreign-currency columns are rendered:
"Ps nợ n.tệ", "Ps có n.tệ", "Tỷ giá". The default (``vnd``) preserves
backward compatibility.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.views.generic import TemplateView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ui_modern.mixins import require_current_company
from apps.ui_modern.views.report_views import _common_period_choices, _parse_period_kwargs


def _get_company(request):
    return require_current_company(request)


def _parse_template(request) -> str:
    """Return the selected template: ``vnd`` (default) or ``fc``."""
    raw = (request.GET.get("template") or "vnd").strip().lower()
    return "fc" if raw == "fc" else "vnd"


def _parse_date_range(request):
    """Parse optional ``from_date`` / ``to_date`` query params.

    Returns ``(from_date, to_date)`` as ``date | None``. When supplied,
    these override the fiscal_year + period filter so callers can narrow
    rows to an arbitrary window (VAL-M3-022).
    """
    from_str = (request.GET.get("from_date") or "").strip()
    to_str = (request.GET.get("to_date") or "").strip()
    parsed_from: date | None = None
    parsed_to: date | None = None
    if from_str:
        try:
            parsed_from = date.fromisoformat(from_str)
        except ValueError:
            parsed_from = None
    if to_str:
        try:
            parsed_to = date.fromisoformat(to_str)
        except ValueError:
            parsed_to = None
    return parsed_from, parsed_to


def _has_date_filter(request) -> bool:
    """True if either from_date or to_date was supplied."""
    return bool((request.GET.get("from_date") or "").strip()) or bool(
        (request.GET.get("to_date") or "").strip()
    )


def _line_filter_kwargs(company, fy, period, request):
    """Build the base voucher filter kwargs.

    When from_date/to_date are present, the period filter is dropped in
    favor of the explicit date window so callers can span periods.
    """
    base = {
        "voucher__company": company,
        "voucher__status__gte": AccountingVoucher.Status.LEDGER,
    }
    if _has_date_filter(request):
        from_d, to_d = _parse_date_range(request)
        if from_d:
            base["voucher__voucher_date__gte"] = from_d
        if to_d:
            base["voucher__voucher_date__lte"] = to_d
        # When a date window is supplied we still pin the fiscal year so
        # multi-year windows don't silently pull historical data.
        base["voucher__fiscal_year"] = fy
    else:
        base["voucher__fiscal_year"] = fy
        base["voucher__period"] = period
    return base


def _build_detail_book(request, account_prefixes, page_title, form_code, template):
    """Build a detail book for given account prefixes (cash/bank/sales).

    Running balance is read directly from VoucherLine.running_balance_debit and
    VoucherLine.running_balance_credit (computed by VoucherPostingService on
    post/unpost) instead of being computed in the view.

    Honors ``template=vnd|fc`` (fc adds foreign-currency columns) and an
    optional ``from_date`` / ``to_date`` window.
    """
    fy, period = _parse_period_kwargs(request)
    company = _get_company(request)
    tmpl = _parse_template(request)

    acc_filter = Q()
    for prefix in account_prefixes:
        acc_filter |= Q(account_code__startswith=prefix)

    # Get prior period opening balance (period-based, even when a date window
    # is applied to the current rows, the opening reflects prior periods).
    prior_qs = VoucherLine.objects.filter(
        voucher__company=company,
        voucher__fiscal_year=fy,
        voucher__period__lt=period,
        voucher__status__gte=AccountingVoucher.Status.LEDGER,
    ).filter(acc_filter)
    prior_totals = prior_qs.aggregate(d=Sum("debit_vnd"), c=Sum("credit_vnd"))
    opening = (prior_totals["d"] or Decimal("0")) - (prior_totals["c"] or Decimal("0"))

    # Current period (or date-window) lines
    base_kwargs = _line_filter_kwargs(company, fy, period, request)
    lines_qs = (
        VoucherLine.objects.select_related("voucher")
        .filter(**base_kwargs)
        .filter(acc_filter)
        .order_by("voucher__voucher_date", "voucher__voucher_no", "line_no")
    )

    rows = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    total_debit_fc = Decimal("0")
    total_credit_fc = Decimal("0")
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
        debit_fc = line.debit_fc or Decimal("0")
        credit_fc = line.credit_fc or Decimal("0")
        total_debit_fc += debit_fc
        total_credit_fc += credit_fc
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
                "debit_fc": debit_fc,
                "credit_fc": credit_fc,
                "exchange_rate": line.voucher.exchange_rate or Decimal("1"),
                "currency_code": line.voucher.currency_code or "VND",
            }
        )

    return {
        "page_title": f"{page_title} ({form_code})",
        "fiscal_year": fy,
        "period": period,
        "template": tmpl,
        "is_fc": tmpl == "fc",
        "opening_balance": opening,
        "closing_balance": last_running,
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "total_debit_fc": total_debit_fc,
        "total_credit_fc": total_credit_fc,
        "from_date": request.GET.get("from_date", ""),
        "to_date": request.GET.get("to_date", ""),
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
        tmpl = _parse_template(self.request)

        base_kwargs = _line_filter_kwargs(company, fy, period, self.request)
        lines_qs = (
            VoucherLine.objects.select_related("voucher")
            .filter(**base_kwargs)
            .filter(account_code__startswith="511")
            .order_by("voucher__voucher_date", "voucher__voucher_no")
        )

        rows = []
        total_revenue = Decimal("0")
        total_revenue_fc = Decimal("0")
        for line in lines_qs:
            amount = line.credit_vnd or Decimal("0")
            amount_fc = line.credit_fc or Decimal("0")
            rows.append(
                {
                    "voucher_no": line.voucher.voucher_no,
                    "voucher_date": line.voucher.voucher_date,
                    "description": line.description or line.voucher.description,
                    "object_code": line.object_code,
                    "object_name": line.object_name,
                    "amount": amount,
                    "debit_fc": line.debit_fc or Decimal("0"),
                    "credit_fc": amount_fc,
                    "exchange_rate": line.voucher.exchange_rate or Decimal("1"),
                    "currency_code": line.voucher.currency_code or "VND",
                }
            )
            total_revenue += amount
            total_revenue_fc += amount_fc

        ctx.update(
            {
                "page_title": "Sổ chi tiết bán hàng (S35-DN)",
                "fiscal_year": fy,
                "period": period,
                "template": tmpl,
                "is_fc": tmpl == "fc",
                "rows": rows,
                "total_revenue": total_revenue,
                "total_revenue_fc": total_revenue_fc,
                "is_sales_detail": True,
                "from_date": self.request.GET.get("from_date", ""),
                "to_date": self.request.GET.get("to_date", ""),
                **_common_period_choices(),
            }
        )
        return ctx
