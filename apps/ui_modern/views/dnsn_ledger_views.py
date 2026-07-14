"""HTMX views for TT58 DNSN ledger listing and detail.

Provides:
- DnsnLedgerListView: Shows all available ledgers for the company's
  tax method group, with period balances.
- DnsnLedgerDetailView: Shows entries for a specific ledger type with
  running balances.
- DnsnLedgerSettingsView: Allows enabling/disabling optional S4 ledgers.
"""

import contextlib
from datetime import date as date_type
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.models import Company
from apps.ledger.dnsn_ledger_types import (
    LEDGER_LABELS,
    LEDGER_SHORT_LABELS,
    OPTIONAL_LEDGER_TYPES,
    get_company_available_ledgers,
    get_required_ledgers,
)
from apps.ledger.models import DnsnLedgerBalance, DnsnLedgerEntry


def _get_company(request) -> Company:
    """Get the current company from request or fall back to first."""
    company = getattr(request, "current_company", None)
    if company:
        return company
    return Company.objects.first()


class DnsnLedgerListView(LoginRequiredMixin, ListView):
    """List all available DNSN ledgers for the current company.

    Only shows ledgers applicable to the company's tax_method_group
    plus any optional S4 ledgers that have been explicitly enabled.
    """

    template_name = "modern/dnsn/ledger_list.html"
    context_object_name = "ledgers"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = _get_company(self.request)
        return get_company_available_ledgers(company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = _get_company(self.request)
        group = company.tax_method_group if company.accounting_regime == "tt58" else None
        ctx["page_title"] = "Sổ kế toán DNSN"
        ctx["is_tt58"] = company.accounting_regime == "tt58"
        ctx["tax_method_group"] = group

        # Build ledger info list with balances
        ledger_infos = []
        for lt in self.get_queryset():
            balance = (
                DnsnLedgerBalance.objects.filter(
                    company=company,
                    fiscal_year=_current_fiscal_year(),
                    ledger_type=lt,
                )
                .order_by("-period")
                .first()
            )
            entry_count = DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type=lt,
            ).count()
            ledger_infos.append(
                {
                    "ledger_type": lt,
                    "label": LEDGER_LABELS.get(lt, lt.upper()),
                    "short_label": LEDGER_SHORT_LABELS.get(lt, lt.upper()),
                    "entry_count": entry_count,
                    "period_revenue": balance.period_revenue if balance else Decimal("0"),
                    "period_cost": balance.period_cost if balance else Decimal("0"),
                    "period_cash": balance.period_cash if balance else Decimal("0"),
                    "period_vat": balance.period_vat if balance else Decimal("0"),
                    "closing_revenue": balance.closing_revenue if balance else Decimal("0"),
                    "closing_cost": balance.closing_cost if balance else Decimal("0"),
                    "closing_cash": balance.closing_cash if balance else Decimal("0"),
                    "closing_vat": balance.closing_vat if balance else Decimal("0"),
                    "last_transaction_date": balance.last_transaction_date if balance else None,
                }
            )
        ctx["ledger_infos"] = ledger_infos
        return ctx


def _current_fiscal_year() -> int:
    """Get the current fiscal year."""
    return date_type.today().year


class DnsnLedgerDetailView(LoginRequiredMixin, View):
    """Show entries for a specific DNSN ledger type with running balances.

    The ledger type must be available for the company's tax_method_group
    (or explicitly enabled as an optional ledger).
    """

    template_name = "modern/dnsn/ledger_detail.html"
    login_url = "/auth/login/"

    def get(self, request, ledger_type, *args, **kwargs):
        company = _get_company(request)
        available = get_company_available_ledgers(company)

        if ledger_type not in available:
            messages.error(
                request,
                f"Sổ {ledger_type.upper()}-DNSN không khả dụng cho nhóm thuế của công ty này.",
            )
            return redirect("ui_modern:dnsn_ledger_list")

        entries = DnsnLedgerEntry.objects.filter(
            company=company,
            ledger_type=ledger_type,
        ).order_by("entry_date", "id", "line_no")

        # Filter by period/year if provided
        fiscal_year = request.GET.get("fiscal_year")
        if fiscal_year:
            with contextlib.suppress(ValueError):
                entries = entries.filter(fiscal_year=int(fiscal_year))

        period = request.GET.get("period")
        if period:
            with contextlib.suppress(ValueError):
                entries = entries.filter(period=int(period))

        date_from = request.GET.get("date_from")
        if date_from:
            entries = entries.filter(entry_date__gte=date_from)

        date_to = request.GET.get("date_to")
        if date_to:
            entries = entries.filter(entry_date__lte=date_to)

        ctx = {
            "page_title": LEDGER_LABELS.get(ledger_type, ledger_type.upper()),
            "ledger_type": ledger_type,
            "ledger_label": LEDGER_LABELS.get(ledger_type, ledger_type.upper()),
            "entries": entries,
            "is_tt58": company.accounting_regime == "tt58",
            "tax_method_group": company.tax_method_group,
        }

        # Compute totals
        total_revenue = sum((e.revenue_amount for e in entries), Decimal("0"))
        total_cost = sum((e.cost_amount for e in entries), Decimal("0"))
        total_cash_in = sum((e.cash_in for e in entries), Decimal("0"))
        total_cash_out = sum((e.cash_out for e in entries), Decimal("0"))
        total_vat_output = sum((e.vat_output for e in entries), Decimal("0"))
        total_vat_input = sum((e.vat_input for e in entries), Decimal("0"))

        ctx["total_revenue"] = total_revenue
        ctx["total_cost"] = total_cost
        ctx["total_cash_in"] = total_cash_in
        ctx["total_cash_out"] = total_cash_out
        ctx["total_vat_output"] = total_vat_output
        ctx["total_vat_input"] = total_vat_input

        return render(request, self.template_name, ctx)


class DnsnLedgerSettingsView(LoginRequiredMixin, View):
    """Settings page for enabling/disabling optional DNSN ledgers (S4a-S4d).

    Optional ledgers are disabled by default and can be enabled
    independently. Only available for TT58 companies.
    """

    template_name = "modern/dnsn/ledger_settings.html"
    login_url = "/auth/login/"

    OPTIONAL_LEDGER_DESCRIPTIONS = {
        "s4a": "Sổ công nợ — Theo dõi công nợ phải thu và phải trả",
        "s4b": "Sổ TSCĐ — Theo dõi tài sản cố định",
        "s4c": "Sổ thuế khác — Theo dõi các loại thuế ngoài GTGT",
        "s4d": "Sổ vốn CSH — Theo dõi vốn chủ sở hữu",
    }

    def get(self, request, *args, **kwargs):
        company = _get_company(request)
        enabled = company.dnsn_optional_ledgers or {}

        optional_ledgers = []
        for lt in OPTIONAL_LEDGER_TYPES:
            optional_ledgers.append(
                {
                    "ledger_type": lt,
                    "label": LEDGER_LABELS.get(lt, lt.upper()),
                    "short_label": LEDGER_SHORT_LABELS.get(lt, lt.upper()),
                    "description": self.OPTIONAL_LEDGER_DESCRIPTIONS.get(lt, ""),
                    "enabled": enabled.get(lt, False),
                }
            )

        ctx = {
            "page_title": "Tùy chọn sổ DNSN",
            "is_tt58": company.accounting_regime == "tt58",
            "optional_ledgers": optional_ledgers,
            "required_ledgers": get_required_ledgers(company.tax_method_group)
            if company.accounting_regime == "tt58"
            else [],
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        company = _get_company(request)

        if company.accounting_regime != "tt58":
            messages.error(request, "Tính năng này chỉ dành cho công ty TT58.")
            return redirect("ui_modern:dnsn_ledger_settings")

        # Read checkbox values for each optional ledger
        enabled = {}
        for lt in OPTIONAL_LEDGER_TYPES:
            enabled[lt] = request.POST.get(f"enable_{lt}") == "on"

        company.dnsn_optional_ledgers = enabled
        company.save(update_fields=["dnsn_optional_ledgers", "updated_at"])

        # Build a summary message
        enabled_count = sum(1 for v in enabled.values() if v)
        if enabled_count:
            messages.success(
                request,
                f"Đã cập nhật tùy chọn sổ DNSN. {enabled_count} sổ tùy chọn đã bật.",
            )
        else:
            messages.success(
                request,
                "Đã cập nhật tùy chọn sổ DNSN. Tất cả sổ tùy chọn đã tắt.",
            )
        return redirect("ui_modern:dnsn_ledger_settings")
