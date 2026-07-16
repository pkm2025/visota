"""Chart of accounts list view — TT133 account tree."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View

from apps.ledger.models import AccountPeriodBalance, VoucherLine
from apps.master_data.models import ChartOfAccounts
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class ChartOfAccountsListView(LoginRequiredMixin, ListView):
    """List all TT133 accounts for the current company."""

    template_name = "modern/ledger/chart_of_accounts_list.html"
    context_object_name = "accounts"
    paginate_by = 200
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        qs = (
            ChartOfAccounts.objects.filter(company=company)
            .select_related("company")
            .order_by("account_code")
        )
        account_type = self.request.GET.get("account_type")
        if account_type:
            qs = qs.filter(account_type=account_type)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(account_code__icontains=search) | qs.filter(
                account_name__icontains=search
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = require_current_company(self.request)
        ctx["page_title"] = "Hệ thống tài khoản"
        ctx["account_type_choices"] = (
            ChartOfAccounts.objects.values_list("account_type", flat=True)
            .filter(company=company)
            .distinct()
            .order_by("account_type")
        )
        return ctx


class ChartOfAccountsChangeCodeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Đổi mã tài khoản (Change account code).

    GET renders a form with a ``new_code`` field showing the current code.
    POST validates ``new_code`` (non-empty and unique within the company) and,
    inside a single transaction, cascades the change to:

    * ``ChartOfAccounts.account_code`` (and ``parent_account_code`` references
      from children)
    * ``VoucherLine.account_code`` — scoped to ``voucher__company`` so other
      tenants' lines are untouched (VAL-SEC-003 / HIGH-03).
    * ``AccountPeriodBalance.account_code`` — scoped to ``company``.

    URL: /modern/chart-of-accounts/<pk>/change-code/
    """

    login_url = "/auth/login/"
    template_name = "modern/ledger/change_account_code.html"
    required_permission = "master_data.access"

    def _get_account(self, request: HttpRequest, pk: int) -> ChartOfAccounts:
        company = require_current_company(request)
        return get_object_or_404(ChartOfAccounts, pk=pk, company=company)

    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        account = self._get_account(request, pk)
        return self._render_form(request, account, error=None)

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        account = self._get_account(request, pk)
        new_code = (request.POST.get("new_code") or "").strip()

        # ── Validations ───────────────────────────────────────────────
        if not new_code:
            return self._render_form(
                request, account, error="Mã tài khoản mới không được để trống."
            )

        if new_code == account.account_code:
            # No-op: stay on the form without error.
            return self._render_form(request, account, error=None)

        if (
            ChartOfAccounts.objects.filter(company_id=account.company_id, account_code=new_code)
            .exclude(pk=account.pk)
            .exists()
        ):
            return self._render_form(
                request,
                account,
                error=f"Mã tài khoản '{new_code}' đã tồn tại trong công ty.",
            )

        # ── Cascade update in single transaction ──────────────────────
        old_code = account.account_code
        with transaction.atomic():
            # 1. Update VoucherLine.account_code — scoped to the account's company
            # so the same code in another tenant's chart is left untouched.
            VoucherLine.objects.filter(
                voucher__company_id=account.company_id,
                account_code=old_code,
            ).update(account_code=new_code)
            # 2. Update AccountPeriodBalance.account_code (same company scope)
            AccountPeriodBalance.objects.filter(
                company_id=account.company_id, account_code=old_code
            ).update(account_code=new_code)
            # 3. Update child ChartOfAccounts.parent_account_code references
            ChartOfAccounts.objects.filter(
                company_id=account.company_id, parent_account_code=old_code
            ).update(parent_account_code=new_code)
            # 4. Finally update the account itself
            account.account_code = new_code
            account.save(update_fields=["account_code", "updated_at"])

        # Recompute running balances for the new code to keep S07/S08 consistent.
        try:
            from apps.ledger.services import VoucherPostingService

            VoucherPostingService._recompute_running_balances_for_codes(account.company, [new_code])
        except Exception:  # noqa: BLE001 — best-effort, do not block the change
            pass

        messages.success(
            request,
            f"Đã đổi mã tài khoản từ '{old_code}' thành '{new_code}'.",
        )
        return redirect("ui_modern:chart_of_accounts_list")

    # ------------------------------------------------------------------
    def _render_form(
        self,
        request: HttpRequest,
        account: ChartOfAccounts,
        error: str | None,
    ) -> HttpResponse:
        from django.shortcuts import render

        return render(
            request,
            self.template_name,
            {
                "account": account,
                "page_title": "Đổi mã tài khoản",
                "error": error,
            },
        )
