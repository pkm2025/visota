"""Period closing view."""

from datetime import date as dt

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.ledger.models import AccountingVoucher
from apps.ledger.services import PeriodClosingService, VoucherPostingService
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class PeriodClosingView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "modern/ledger/closing.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Kết chuyển cuối kỳ"
        today = dt.today()
        ctx["default_year"] = today.year
        ctx["default_month"] = today.month
        ctx["year_choices"] = [2024, 2025, 2026, 2027]
        ctx["period_choices"] = list(range(1, 13))

        # TT58 BCTC status for display
        company = require_current_company(self.request)
        if company and company.accounting_regime == "tt58":
            from apps.reporting.services.dnsn_report_service import DnsnReportService

            svc = DnsnReportService(company)
            ctx["dnsn_bctc"] = svc.is_bctc_mandatory()
            ctx["dnsn_bctc_label"] = "Bắt buộc" if ctx["dnsn_bctc"] else "Tùy chọn"
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        if not company:
            messages.error(request, "No company")
            return redirect("ui_modern:period_closing")

        year = int(request.POST.get("fiscal_year"))
        month = int(request.POST.get("period"))

        # TT58 BCTC mandatory check for year-end close
        # VAL-TT58-035: BCTC mandatory for Group 2 companies
        # VAL-TT58-036: BCTC optional for Group 1 companies
        # VAL-TT58-037: BCTC mandatory for Group 4, optional for Group 3
        if company.accounting_regime == "tt58":
            from apps.reporting.services.dnsn_report_service import DnsnReportService

            svc = DnsnReportService(company)
            bctc_check = svc.check_bctc_for_period_close(year, month)
            if not bctc_check["can_close"]:
                messages.error(request, bctc_check["message"])
                return redirect("ui_modern:period_closing")

        service = PeriodClosingService(company=company)
        result = service.close_period(fiscal_year=year, period=month)

        if result.get("skipped"):
            messages.info(request, f"Kỳ {month}/{year} đã kết chuyển hoặc không có dữ liệu")
        else:
            messages.success(
                request,
                f"Kết chuyển {month}/{year}: DT={result['total_revenue']:,.0f} "
                f"CP={result['total_expense']:,.0f} "
                f"Lãi/Lỗ={result['profit']:,.0f}",
            )
        return redirect("ui_modern:period_closing")


class PeriodReopenView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Mở khóa kỳ/năm — xóa voucher kết chuyển (KC) để mở lại kỳ.

    Finds and deletes the closing voucher (source='closing') for the
    selected period. This reverses the KC entries (unposts the voucher,
    which reverts 5xx→911, 6xx→911, 911→421 transfers) then deletes it.
    After reopening, users can post new vouchers to that period and
    re-run closing when done.
    """

    template_name = "modern/ledger/reopen_period.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Mở khóa kỳ/năm"
        ctx["year_choices"] = [2024, 2025, 2026, 2027]
        ctx["period_choices"] = list(range(1, 13))
        company = require_current_company(self.request)

        # Show currently closed periods (periods with KC vouchers)
        closed_periods = []
        if company:
            kc_vouchers = AccountingVoucher.objects.filter(
                company=company,
                source="closing",
                status__gte=AccountingVoucher.Status.LEDGER,
            ).order_by("-fiscal_year", "-period")
            for v in kc_vouchers:
                closed_periods.append(
                    {
                        "id": v.id,
                        "voucher_no": v.voucher_no,
                        "fiscal_year": v.fiscal_year,
                        "period": v.period,
                        "description": v.description,
                    }
                )
        ctx["closed_periods"] = closed_periods
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        if not company:
            messages.error(request, "No company")
            return redirect("ui_modern:period_reopen")

        fiscal_year = int(request.POST.get("fiscal_year"))
        period = int(request.POST.get("period"))

        # Find the KC voucher for this period
        kc_voucher = AccountingVoucher.objects.filter(
            company=company,
            source="closing",
            fiscal_year=fiscal_year,
            period=period,
        ).first()

        if not kc_voucher:
            messages.info(
                request,
                f"Kỳ {period}/{fiscal_year} chưa kết chuyển (không có voucher KC). "
                "Không cần mở khóa.",
            )
            return redirect("ui_modern:period_reopen")

        voucher_no = kc_voucher.voucher_no

        # Unpost (reverses 5xx→911, 6xx→911, 911→421 entries)
        try:
            if kc_voucher.is_posted:
                VoucherPostingService().unpost(kc_voucher)
        except Exception as exc:  # noqa: BLE001 — surface, don't crash
            import logging

            logging.getLogger("apps.ui_modern").exception(
                "unpost failed for KC voucher %s: %s", voucher_no, exc
            )
            messages.error(
                request,
                f"Không thể bỏ ghi sổ voucher KC {voucher_no}. Lỗi: {exc}",
            )
            return redirect("ui_modern:period_reopen")

        # Delete the KC voucher
        kc_voucher.delete()
        messages.success(
            request,
            f"Đã mở khóa kỳ {period}/{fiscal_year} (xóa voucher {voucher_no}). "
            "Giờ có thể nhập/sửa chứng từ trong kỳ này. "
            "Khi xong, chạy lại kết chuyển để đóng kỳ.",
        )
        return redirect("ui_modern:period_reopen")
