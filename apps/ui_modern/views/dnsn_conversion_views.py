"""HTMX views for TT58 balance conversion (TT132/TT133 → TT58 DNSN).

Provides:
- DnsnConversionView: Trigger and preview balance conversion from
  TT133/TT200 account balances to TT58 DNSN ledger opening balances.
- DnsnConversionResultView: Display conversion summary after conversion.

These views are accessible for any company. The conversion service
maps AccountPeriodBalance rows to DnsnLedgerBalance opening entries.
"""

from datetime import date as date_type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.core.models import Company
from apps.ledger.services.balance_conversion_service import BalanceConversionService


def _get_company(request) -> Company:
    """Get the current company from request or fall back to first."""
    company = getattr(request, "current_company", None)
    if company:
        return company
    return Company.objects.first()


def _parse_period(request):
    """Extract fiscal_year and period from query params."""
    today = date_type.today()
    try:
        fy = int(request.GET.get("fiscal_year", today.year))
    except (TypeError, ValueError):
        fy = today.year
    try:
        period = int(request.GET.get("period", today.month))
    except (TypeError, ValueError):
        period = today.month
    return fy, period


class DnsnConversionView(LoginRequiredMixin, View):
    """Balance conversion page: TT132/TT133 → TT58 DNSN.

    GET: Show the conversion form with a preview of source balances.
    POST: Execute the conversion and redirect to the result page.

    VAL-CROSS-005: Conversion flow TT133 to TT58 with Visota branding.
    """

    template_name = "modern/dnsn/conversion.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        company = _get_company(request)
        fy, period = _parse_period(request)

        service = BalanceConversionService()
        # Preview: show what would be converted (non-destructive)
        summary = service.get_conversion_summary(company, fy, period)

        # Also check if there are source balances to convert
        from apps.ledger.models import AccountPeriodBalance

        source_balances = AccountPeriodBalance.objects.filter(
            company=company,
            fiscal_year=fy,
            period=period,
        ).order_by("account_code")

        ctx = {
            "page_title": "Chuyển đổi số dư sang TT58/2026",
            "company": company,
            "fiscal_year": fy,
            "period": period,
            "summary": summary,
            "source_balances": source_balances,
            "is_tt58": company.accounting_regime == "tt58",
            "has_source_data": source_balances.exists(),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        company = _get_company(request)
        fy, period = _parse_period(request)

        service = BalanceConversionService()
        summary = service.convert(company, fiscal_year=fy, source_period=period)

        # Switch the company to TT58 regime after conversion
        if company.accounting_regime != "tt58":
            company.accounting_regime = "tt58"
            company.save(update_fields=["accounting_regime"])

        messages.success(
            request,
            f"Đã chuyển đổi số dư thành công: {summary.converted_count} sổ DNSN được tạo. "
            f"Tổng số dư nguồn: {summary.total_source:,.0f} VNĐ.",
        )
        return redirect("ui_modern:dnsn_conversion_result")


class DnsnConversionResultView(LoginRequiredMixin, View):
    """Display the result of a balance conversion.

    Shows the mapping from source account codes to DNSN ledger types
    and the resulting opening balances.
    """

    template_name = "modern/dnsn/conversion_result.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        company = _get_company(request)
        fy, period = _parse_period(request)

        service = BalanceConversionService()
        summary = service.get_conversion_summary(company, fy, period)

        ctx = {
            "page_title": "Kết quả chuyển đổi số dư TT58",
            "company": company,
            "fiscal_year": fy,
            "period": period,
            "summary": summary,
            "is_tt58": company.accounting_regime == "tt58",
        }
        return render(request, self.template_name, ctx)
