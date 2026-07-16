"""HTMX views for TT58 DNSN financial reports (B01-DNSN, B02-DNSN).

Provides:
- DnsnB01ReportView: Báo cáo tình hình tài chính (Balance Sheet)
- DnsnB02ReportView: Báo cáo KQHD kinh doanh (P&L)
- DnsnReportExportView: PDF/Excel export for both reports

These views are only accessible for TT58 companies. Non-TT58 companies
get a redirect with a warning message (VAL-TT58-031).
"""

import io
from datetime import date as date_type

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from apps.core.models import Company
from apps.reporting.services.dnsn_report_service import DnsnReportService
from apps.ui_modern.mixins import require_current_company

DNSN_REPORTS = [
    {
        "code": "B01-DNSN",
        "title": "B01-DNSN — Báo cáo tình hình tài chính",
        "short": "B01-DNSN",
        "description": "Báo cáo tình hình tài chính cho DN siêu nhỏ",
        "url_name": "ui_modern:dnsn_report_b01",
    },
    {
        "code": "B02-DNSN",
        "title": "B02-DNSN — Báo cáo KQHD kinh doanh",
        "short": "B02-DNSN",
        "description": "Báo cáo kết quả hoạt động kinh doanh cho DN siêu nhỏ",
        "url_name": "ui_modern:dnsn_report_b02",
    },
]


def _get_company(request) -> Company:
    """Get the current company from request or fall back to first."""
    company = getattr(request, "current_company", None)
    if company:
        return company
    return require_current_company(request)


def _parse_period(request) -> tuple[int, int]:
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


def _period_choices():
    return {
        "period_choices": list(range(1, 13)),
        "year_choices": [2024, 2025, 2026, 2027],
    }


def _check_tt58(request) -> Company | None:
    """Check if the current company is TT58. Returns company or None + redirects."""
    company = _get_company(request)
    if not company or company.accounting_regime != "tt58":
        messages.error(
            request,
            "Báo cáo DNSN chỉ dành cho công ty áp dụng chế độ TT58/2026.",
        )
        return None
    return company


class DnsnReportListView(LoginRequiredMixin, TemplateView):
    """List of available DNSN reports (only for TT58 companies).

    VAL-TT58-031: B01-DNSN not available for non-TT58 companies.
    """

    template_name = "modern/dnsn/report_list.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = _get_company(self.request)
        is_tt58 = company.accounting_regime == "tt58" if company else False

        reports = DNSN_REPORTS if is_tt58 else []
        ctx.update(
            {
                "page_title": "Báo cáo tài chính DNSN",
                "is_tt58": is_tt58,
                "reports": reports,
                "tax_method_group": company.tax_method_group if is_tt58 else None,
                "tax_method_group_label": (company.tax_method_group_label if is_tt58 else None),
            }
        )
        return ctx


class DnsnB01ReportView(LoginRequiredMixin, TemplateView):
    """B01-DNSN: Báo cáo tình hình tài chính (simplified balance sheet).

    VAL-TT58-029: B01-DNSN report renders for TT58 company.
    VAL-TT58-030: B01-DNSN balances correctly from ledger entries.
    VAL-TT58-031: B01-DNSN not available for non-TT58 companies.
    """

    template_name = "modern/dnsn/report_b01.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = _get_company(self.request)

        if not company or company.accounting_regime != "tt58":
            ctx.update(
                {
                    "page_title": "B01-DNSN",
                    "is_tt58": False,
                    "not_available": True,
                }
            )
            return ctx

        fy, period = _parse_period(self.request)
        service = DnsnReportService(company=company)
        report_data = service.generate_b01_dnsn(fy, period)

        ctx.update(report_data)
        ctx.update(
            {
                "page_title": "B01-DNSN — Báo cáo tình hình tài chính",
                "is_tt58": True,
                "not_available": False,
                **_period_choices(),
            }
        )
        return ctx


class DnsnB02ReportView(LoginRequiredMixin, TemplateView):
    """B02-DNSN: Báo cáo kết quả hoạt động kinh doanh (simplified P&L).

    VAL-TT58-032: B02-DNSN report renders for TT58 company.
    VAL-TT58-033: B02-DNSN profit calculation matches ledger totals.
    """

    template_name = "modern/dnsn/report_b02.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = _get_company(self.request)

        if not company or company.accounting_regime != "tt58":
            ctx.update(
                {
                    "page_title": "B02-DNSN",
                    "is_tt58": False,
                    "not_available": True,
                }
            )
            return ctx

        fy, period = _parse_period(self.request)
        service = DnsnReportService(company=company)
        report_data = service.generate_b02_dnsn(fy, period)

        ctx.update(report_data)
        ctx.update(
            {
                "page_title": "B02-DNSN — Báo cáo KQHD kinh doanh",
                "is_tt58": True,
                "not_available": False,
                **_period_choices(),
            }
        )
        return ctx


class DnsnReportExportView(LoginRequiredMixin, View):
    """Export B01-DNSN or B02-DNSN to PDF or Excel.

    VAL-TT58-034: B02-DNSN exports to PDF.
    """

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        report_code = (request.GET.get("report") or "").strip().upper()
        fmt = (request.GET.get("format") or "").strip().lower()

        if report_code not in ("B01-DNSN", "B02-DNSN"):
            return HttpResponse(
                f"Invalid report code: {report_code!r}. Supported: B01-DNSN, B02-DNSN",
                status=400,
            )
        if fmt not in ("pdf", "xlsx"):
            return HttpResponse(
                f"Invalid format: {fmt!r}. Supported: pdf, xlsx",
                status=400,
            )

        company = _get_company(request)
        if not company or company.accounting_regime != "tt58":
            messages.error(request, "Báo cáo DNSN chỉ dành cho công ty TT58.")
            return redirect("ui_modern:dnsn_report_list")

        fy, period = _parse_period(request)
        service = DnsnReportService(company=company)

        if report_code == "B01-DNSN":
            report_title = "Báo cáo tình hình tài chính (B01-DNSN)"
            file_code = "B01-DNSN"
            headers, rows = service.get_b01_export_rows(fy, period)
        else:
            report_title = "Báo cáo kết quả hoạt động kinh doanh (B02-DNSN)"
            file_code = "B02-DNSN"
            headers, rows = service.get_b02_export_rows(fy, period)

        if fmt == "pdf":
            return self._render_pdf(company, report_title, headers, rows, file_code, fy, period)
        return self._render_xlsx(report_title, headers, rows, file_code, fy, period)

    def _render_pdf(
        self, company, report_title, headers, rows, file_code, fy, period
    ) -> HttpResponse:
        company_name = company.name if company else "Công ty"
        period_label = f"Tháng {period:02d} / {fy}"
        html_string = render_to_string(
            "modern/dnsn/report_export_pdf.html",
            {
                "company_name": company_name,
                "report_title": report_title,
                "period_label": period_label,
                "headers": headers,
                "rows": rows,
            },
        )

        from weasyprint import HTML

        pdf_bytes = HTML(string=html_string).write_pdf()

        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        safe_code = file_code.replace("-", "_")
        resp["Content-Disposition"] = f'attachment; filename="{safe_code}_{fy}{period:02d}.pdf"'
        return resp

    def _render_xlsx(self, report_title, headers, rows, file_code, fy, period) -> HttpResponse:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = file_code[:31]

        ws.append(headers)
        for row in rows:
            ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        resp = HttpResponse(
            buf.getvalue(),
            content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        )
        safe_code = file_code.replace("-", "_")
        resp["Content-Disposition"] = f'attachment; filename="{safe_code}_{fy}{period:02d}.xlsx"'
        return resp
