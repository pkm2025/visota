"""Utility accounting views — period tools and opening balance management.

Features:
  - Chuyển số dư sang năm sau (year-end carry-forward)
  - Phân bổ cuối kỳ (period allocation)
  - Khai báo kết chuyển cuối kỳ (closing entry declaration)
  - Đánh lại số chứng từ (voucher renumbering)
  - Số dư ban đầu KH (customer opening balances)
  - Số dư ban đầu HĐ (invoice opening balances)
  - Bộ phận hạch toán (department/cost center master)
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance
from apps.ui_modern.views.report_views import _common_period_choices, _parse_period_kwargs


class YearEndCarryForwardView(LoginRequiredMixin, TemplateView):
    """Chuyển số dư sang năm sau — carry forward closing balances to next year."""

    template_name = "modern/tools/year_end_carry_forward.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, _ = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        balances = AccountPeriodBalance.objects.filter(
            company=company, fiscal_year=fy, period=12
        ).order_by("account_code")

        # Determine carry-forward closing balances
        rows = []
        for b in balances:
            closing_d = b.closing_debit or Decimal("0")
            closing_c = b.closing_credit or Decimal("0")
            if closing_d == 0 and closing_c == 0:
                continue
            rows.append(
                {
                    "account_code": b.account_code,
                    "account_name": getattr(b, "account_name", b.account_code),
                    "closing_debit": closing_d,
                    "closing_credit": closing_c,
                    "next_year_opening_debit": closing_d,
                    "next_year_opening_credit": closing_c,
                }
            )

        ctx.update(
            {
                "page_title": "Chuyển số dư sang năm sau",
                "fiscal_year": fy,
                "next_year": fy + 1,
                "rows": rows,
                **_common_period_choices(),
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        fy, _ = _parse_period_kwargs(request)
        next_year = fy + 1
        company = Company.objects.first()

        balances = AccountPeriodBalance.objects.filter(company=company, fiscal_year=fy, period=12)
        created = 0
        with transaction.atomic():
            for b in balances:
                closing_d = b.closing_debit or Decimal("0")
                closing_c = b.closing_credit or Decimal("0")
                if closing_d == 0 and closing_c == 0:
                    continue
                obj, created_flag = AccountPeriodBalance.objects.update_or_create(
                    company=company,
                    fiscal_year=next_year,
                    period=0,
                    account_code=b.account_code,
                    defaults={
                        "opening_debit": closing_d,
                        "opening_credit": closing_c,
                        "period_debit": Decimal("0"),
                        "period_credit": Decimal("0"),
                        "closing_debit": closing_d,
                        "closing_credit": closing_c,
                    },
                )
                if created_flag:
                    created += 1

        messages.success(
            request,
            f"Đã chuyển số dư sang năm {next_year}: {created} tài khoản mới.",
        )
        return redirect("ui_modern:year_end_carry_forward")


class PeriodAllocationView(LoginRequiredMixin, TemplateView):
    """Phân bổ cuối kỳ — allocate prepaid expenses / accrued costs across periods.

    Shows TK 242 (prepaid expenses) balances that need allocation.
    """

    template_name = "modern/tools/period_allocation.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        balances = (
            AccountPeriodBalance.objects.filter(company=company, fiscal_year=fy, period=period)
            .filter(Q(account_code__startswith="242") | Q(account_code__startswith="335"))
            .order_by("account_code")
        )

        rows = []
        for b in balances:
            debit = b.closing_debit or Decimal("0")
            credit = b.closing_credit or Decimal("0")
            if debit == 0 and credit == 0:
                continue
            remaining_periods = 12 - period
            monthly_amount = (
                (debit or credit) / remaining_periods
                if remaining_periods > 0
                else (debit or credit)
            )
            rows.append(
                {
                    "account_code": b.account_code,
                    "balance": debit or credit,
                    "remaining_periods": remaining_periods,
                    "monthly_amount": monthly_amount,
                    "is_debit": debit > 0,
                }
            )

        ctx.update(
            {
                "page_title": "Phân bổ cuối kỳ",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                **_common_period_choices(),
            }
        )
        return ctx


class ClosingEntryDeclarationView(LoginRequiredMixin, TemplateView):
    """Khai báo kết chuyển cuối kỳ — declare which accounts to close at period end.

    Shows the standard closing entries (KK): N911/C511, N632,641,642,635,811/C911, etc.
    """

    template_name = "modern/tools/closing_entry_declaration.html"
    login_url = "/auth/login/"

    # Standard TT133 closing entries
    CLOSING_ENTRIES = [
        {
            "step": 1,
            "description": "Kết chuyển doanh thu",
            "debit_account": "511",
            "credit_account": "911",
            "account_filter": "511",
        },
        {
            "step": 2,
            "description": "Kết chuyển GTCL hàng tồn kho",
            "debit_account": "911",
            "credit_account": "632",
            "account_filter": "632",
        },
        {
            "step": 3,
            "description": "Kết chuyển chi phí bán hàng",
            "debit_account": "911",
            "credit_account": "641",
            "account_filter": "641",
        },
        {
            "step": 4,
            "description": "Kết chuyển CP quản lý DN",
            "debit_account": "911",
            "credit_account": "642",
            "account_filter": "642",
        },
        {
            "step": 5,
            "description": "Kết chuyển chi phí TC",
            "debit_account": "911",
            "credit_account": "635",
            "account_filter": "635",
        },
        {
            "step": 6,
            "description": "Kết chuyển thu nhập khác",
            "debit_account": "711",
            "credit_account": "911",
            "account_filter": "711",
        },
        {
            "step": 7,
            "description": "Kết chuyển chi phí khác",
            "debit_account": "911",
            "credit_account": "811",
            "account_filter": "811",
        },
        {
            "step": 8,
            "description": "Xác định & kết chuyển TNDN",
            "debit_account": "911",
            "credit_account": "821",
            "account_filter": "821",
        },
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        rows = []
        for entry in self.CLOSING_ENTRIES:
            balances = AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=fy,
                period=period,
                account_code__startswith=entry["account_filter"],
            )
            total = Decimal("0")
            for b in balances:
                total += b.period_debit or Decimal("0")
                total += b.period_credit or Decimal("0")
            rows.append({**entry, "amount": total})

        ctx.update(
            {
                "page_title": "Khai báo kết chuyển cuối kỳ",
                "fiscal_year": fy,
                "period": period,
                "entries": rows,
                **_common_period_choices(),
            }
        )
        return ctx


class VoucherRenumberView(LoginRequiredMixin, TemplateView):
    """Đánh lại số chứng từ — renumber vouchers sequentially."""

    template_name = "modern/tools/voucher_renumber.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, period = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        vouchers = (
            AccountingVoucher.objects.filter(company=company, fiscal_year=fy, period=period)
            .order_by("voucher_date", "id")
            .values_list("id", "voucher_no", "voucher_date", "voucher_type")
        )

        rows = []
        for seq, (vid, vno, vdate, vtype) in enumerate(vouchers, 1):
            prefix_map = {
                "journal": "PK",
                "cash_receipt": "PT",
                "cash_payment": "PC",
                "sales_invoice": "BH",
                "purchase_invoice": "MH",
                "stock_voucher": "PX",
            }
            prefix = prefix_map.get(vtype, "CT")
            new_no = f"{prefix}{fy}{period:02d}-{seq:04d}"
            rows.append(
                {
                    "id": vid,
                    "old_no": vno,
                    "new_no": new_no,
                    "date": vdate,
                    "type": vtype,
                }
            )

        ctx.update(
            {
                "page_title": "Đánh lại số chứng từ",
                "fiscal_year": fy,
                "period": period,
                "rows": rows,
                **_common_period_choices(),
            }
        )
        return ctx

    def post(self, request, *args, **kwargs):
        fy, period = _parse_period_kwargs(request)
        company = Company.objects.first()

        vouchers = AccountingVoucher.objects.filter(
            company=company, fiscal_year=fy, period=period
        ).order_by("voucher_date", "id")

        prefix_map = {
            "journal": "PK",
            "cash_receipt": "PT",
            "cash_payment": "PC",
            "sales_invoice": "BH",
            "purchase_invoice": "MH",
            "stock_voucher": "PX",
        }
        updated = 0
        with transaction.atomic():
            for seq, v in enumerate(vouchers, 1):
                prefix = prefix_map.get(v.voucher_type, "CT")
                v.voucher_no = f"{prefix}{fy}{period:02d}-{seq:04d}"
                v.save(update_fields=["voucher_no"])
                updated += 1

        messages.success(request, f"Đã đánh lại số cho {updated} chứng từ.")
        return redirect("ui_modern:voucher_renumber")


class CustomerOpeningBalanceView(LoginRequiredMixin, TemplateView):
    """Vào số dư ban đầu của các khách hàng — customer AR opening balances."""

    template_name = "modern/tools/opening_balances.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, _ = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        # Aggregate TK 131 by object_code at period 0
        balances = AccountPeriodBalance.objects.filter(
            company=company,
            fiscal_year=fy,
            period=0,
            account_code__startswith="131",
        ).order_by("account_code")

        rows = []
        for b in balances:
            debit = b.opening_debit or Decimal("0")
            credit = b.opening_credit or Decimal("0")
            if debit == 0 and credit == 0:
                continue
            rows.append(
                {
                    "account_code": b.account_code,
                    "debit": debit,
                    "credit": credit,
                }
            )

        ctx.update(
            {
                "page_title": "Số dư ban đầu khách hàng",
                "fiscal_year": fy,
                "rows": rows,
                "balance_type": "customer",
                **_common_period_choices(),
            }
        )
        return ctx


class InvoiceOpeningBalanceView(LoginRequiredMixin, TemplateView):
    """Vào số dư ban đầu của các hoá đơn — invoice opening balances."""

    template_name = "modern/tools/opening_balances.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fy, _ = _parse_period_kwargs(self.request)
        company = Company.objects.first()

        # Aggregate TK 131/331 by invoice reference at period 0
        balances = (
            AccountPeriodBalance.objects.filter(
                company=company,
                fiscal_year=fy,
                period=0,
            )
            .filter(Q(account_code__startswith="131") | Q(account_code__startswith="331"))
            .order_by("account_code")
        )

        rows = []
        for b in balances:
            debit = b.opening_debit or Decimal("0")
            credit = b.opening_credit or Decimal("0")
            if debit == 0 and credit == 0:
                continue
            rows.append(
                {
                    "account_code": b.account_code,
                    "debit": debit,
                    "credit": credit,
                }
            )

        ctx.update(
            {
                "page_title": "Số dư ban đầu hoá đơn",
                "fiscal_year": fy,
                "rows": rows,
                "balance_type": "invoice",
                **_common_period_choices(),
            }
        )
        return ctx
