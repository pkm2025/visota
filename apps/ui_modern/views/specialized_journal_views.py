"""Specialized journal views — S03a1/a2/a3/a4-DN + T-account summary.

These are filtered views of the general journal that show only vouchers
relevant to a specific cash/sales/purchase flow, as per Vietnamese
accounting regulation (Circular 200/TT133).
"""

from collections import OrderedDict
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ui_modern.views.report_views import _common_period_choices, _parse_period_kwargs


def _get_company(request):
    return getattr(request, "current_company", None) or Company.objects.first()


class _BaseSpecializedJournal(LoginRequiredMixin, TemplateView):
    """Base class for specialized journals (S03a1/a2/a3/a4-DN)."""

    login_url = "/auth/login/"
    page_title = ""
    form_code = ""
    account_prefixes = []  # e.g. ["111", "112"] for cash/bank
    debit_side = True  # True = filter where these accounts are debited
    voucher_types = None  # None = all types, or list like ["sales_invoice"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = _get_company(self.request)

        lines_qs = VoucherLine.objects.select_related("voucher").filter(
            voucher__company=company,
            voucher__fiscal_year=fy,
            voucher__period=period,
            voucher__status__gte=AccountingVoucher.Status.LEDGER,
        )

        if self.voucher_types:
            lines_qs = lines_qs.filter(voucher__voucher_type__in=self.voucher_types)

        account_filter = Q()
        for prefix in self.account_prefixes:
            kw = {"account_code__startswith": prefix}
            if self.debit_side:
                account_filter |= Q(**kw, debit_vnd__gt=0)
            else:
                account_filter |= Q(**kw, credit_vnd__gt=0)
        lines_qs = lines_qs.filter(account_filter).order_by(
            "voucher__voucher_date", "voucher__voucher_no", "line_no"
        )

        rows = []
        total_amount = Decimal("0")
        for line in lines_qs:
            amount = line.debit_vnd if self.debit_side else line.credit_vnd
            if not amount or amount == 0:
                amount = line.debit_vnd or line.credit_vnd or Decimal("0")
            rows.append(
                {
                    "voucher_date": line.voucher.voucher_date,
                    "voucher_no": line.voucher.voucher_no,
                    "description": line.description or line.voucher.description,
                    "account_code": line.account_code,
                    "object_code": line.object_code,
                    "object_name": line.object_name,
                    "amount": amount,
                }
            )
            total_amount += amount

        ctx.update(
            {
                "page_title": f"{self.page_title} ({self.form_code})",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                "total_amount": total_amount,
                **_common_period_choices(),
            }
        )
        return ctx


class CashReceiptJournalView(_BaseSpecializedJournal):
    """Sổ nhật ký thu tiền (S03a1-DN) — cash/bank receipts.

    Shows all transactions where TK 111 (cash) or 112 (bank) is debited.
    """

    template_name = "modern/reporting/specialized_journal.html"
    page_title = "Sổ nhật ký thu tiền"
    form_code = "S03a1-DN"
    account_prefixes = ["111", "112"]
    debit_side = True


class CashPaymentJournalView(_BaseSpecializedJournal):
    """Sổ nhật ký chi tiền (S03a2-DN) — cash/bank payments.

    Shows all transactions where TK 111 (cash) or 112 (bank) is credited.
    """

    template_name = "modern/reporting/specialized_journal.html"
    page_title = "Sổ nhật ký chi tiền"
    form_code = "S03a2-DN"
    account_prefixes = ["111", "112"]
    debit_side = False


class SalesJournalView(_BaseSpecializedJournal):
    """Sổ nhật ký bán hàng (S03a4-DN) — sales journal.

    Shows all transactions where revenue accounts (TK 511) are credited
    or sales invoices are recorded.
    """

    template_name = "modern/reporting/specialized_journal.html"
    page_title = "Sổ nhật ký bán hàng"
    form_code = "S03a4-DN"
    account_prefixes = ["511", "5111"]
    debit_side = False


class PurchaseJournalView(_BaseSpecializedJournal):
    """Sổ nhật ký mua hàng (S03a3-DN) — purchases journal.

    Shows all transactions where purchase accounts (TK 5111/1331/152/156)
    are debited via purchase invoices.
    """

    template_name = "modern/reporting/specialized_journal.html"
    page_title = "Sổ nhật ký mua hàng"
    form_code = "S03a3-DN"
    account_prefixes = ["152", "156", "1331", "611"]
    debit_side = True
    voucher_types = ["purchase_invoice", "journal"]


class TAccountSummaryView(LoginRequiredMixin, TemplateView):
    """Sổ tổng hợp chữ T của tài khoản — T-account summary.

    Displays each account as a T-shape with debit entries on the left
    and credit entries on the right, with running balance.
    """

    template_name = "modern/reporting/t_account.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = _get_company(self.request)

        account_code = self.request.GET.get("account_code", "").strip()

        lines_qs = VoucherLine.objects.select_related("voucher").filter(
            voucher__company=company,
            voucher__fiscal_year=fy,
            voucher__period=period,
            voucher__status__gte=AccountingVoucher.Status.LEDGER,
        )
        if account_code:
            lines_qs = lines_qs.filter(account_code__startswith=account_code)

        accounts = OrderedDict()
        for line in lines_qs.order_by("account_code", "voucher__voucher_date"):
            code = line.account_code
            if code not in accounts:
                accounts[code] = {
                    "debit_entries": [],
                    "credit_entries": [],
                    "total_debit": Decimal("0"),
                    "total_credit": Decimal("0"),
                }
            debit = line.debit_vnd or Decimal("0")
            credit = line.credit_vnd or Decimal("0")
            entry = {
                "voucher_no": line.voucher.voucher_no,
                "voucher_date": line.voucher.voucher_date,
                "description": line.description or line.voucher.description,
                "amount": debit or credit,
            }
            if debit > 0:
                accounts[code]["debit_entries"].append(entry)
                accounts[code]["total_debit"] += debit
            elif credit > 0:
                accounts[code]["credit_entries"].append(entry)
                accounts[code]["total_credit"] += credit

        for acc in accounts.values():
            acc["balance"] = acc["total_debit"] - acc["total_credit"]

        ctx.update(
            {
                "page_title": "Sổ tổng hợp chữ T",
                "fiscal_year": fy,
                "period": period,
                "account_code": account_code,
                "accounts": accounts,
                **_common_period_choices(),
            }
        )
        return ctx
