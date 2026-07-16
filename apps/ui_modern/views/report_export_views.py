"""Generic Report Export (M3.9, VAL-M3-008..015).

A single endpoint at ``GET /modern/reports/export/`` that exports any of
the 10 supported report codes to PDF (WeasyPrint) or Excel (openpyxl).

Supported ``report`` codes:

============ ===========================================
Code         Report
============ ===========================================
``S03a``     Sổ nhật ký chung (General Journal)
``S03b``     Sổ cái tài khoản (General Ledger)
``S06``      Bảng cân đối tài khoản (Trial Balance)
``S07``      Sổ quỹ tiền mặt (Cash Book)
``S08``      Sổ tiền gửi ngân hàng (Bank Book)
``S35``      Sổ chi tiết bán hàng (Sales Detail)
``B01``      Bảng cân đối kế toán (Balance Sheet)
``B02``      Kết quả hoạt động kinh doanh (P&L)
``B03_direct``    BC dòng tiền PP trực tiếp (Cash Flow Direct)
``B03_indirect``  BC dòng tiền PP gián tiếp (Cash Flow Indirect)
============ ===========================================

Supported ``format`` values: ``pdf``, ``xlsx``.

The endpoint requires login (``LoginRequiredMixin``).  Filenames follow
the pattern ``<CODE>_<YYYYMM>.<ext>`` (e.g. ``B01_202606.pdf``).
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import Callable

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View

from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.reporting.services import BalanceSheetService, CashFlowService, PnLService
from apps.ui_modern.mixins import require_current_company

# ---------------------------------------------------------------------------
# Report metadata
# ---------------------------------------------------------------------------

#: Mapping of report code -> (Vietnamese title, short code used in filename).
REPORT_META: dict[str, tuple[str, str]] = {
    "S03a": ("Sổ nhật ký chung (S03a-DN)", "S03a"),
    "S03b": ("Sổ cái tài khoản (S03b-DN)", "S03b"),
    "S06": ("Bảng cân đối tài khoản (S06-DN)", "S06"),
    "S07": ("Sổ quỹ tiền mặt (S07-DN)", "S07"),
    "S08": ("Sổ tiền gửi ngân hàng (S08-DN)", "S08"),
    "S35": ("Sổ chi tiết bán hàng (S35-DN)", "S35"),
    "B01": ("Bảng cân đối kế toán (B01-DN)", "B01"),
    "B02": ("Kết quả hoạt động kinh doanh (B02-DN)", "B02"),
    "B03_direct": ("Báo cáo dòng tiền PP trực tiếp (B03-DN)", "B03_direct"),
    "B03_indirect": ("Báo cáo dòng tiền PP gián tiếp (B03-DN)", "B03_indirect"),
}


def _vnd(value) -> str:
    """Format a Decimal/int as a Vietnamese integer string (no decimals)."""
    if value is None:
        return ""
    try:
        d = Decimal(str(value))
    except Exception:
        return str(value)
    quantized = d.quantize(Decimal("1"))
    # Use thousands separator
    return f"{int(quantized):,}".replace(",", ".")


def _period_label(fiscal_year: int, period: int) -> str:
    return f"Tháng {period:02d} / {fiscal_year}"


# ---------------------------------------------------------------------------
# Data extractors — each returns (headers: list[str], rows: list[list[str]])
# ---------------------------------------------------------------------------


def _data_s03a(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """General Journal (S03a-DN) — one row per voucher line."""
    headers = ["Ngày", "Số CT", "Diễn giải", "TK Nợ", "TK Có", "Số tiền"]
    qs = (
        AccountingVoucher.objects.filter(company=company, fiscal_year=fy, period=period)
        .prefetch_related("lines")
        .order_by("voucher_date", "voucher_no")
    )
    rows: list[list[str]] = []
    for v in qs:
        lines = list(v.lines.all())
        if not lines:
            rows.append(
                [
                    v.voucher_date.strftime("%d/%m/%Y"),
                    v.voucher_no,
                    v.description,
                    "",
                    "",
                    "",
                ]
            )
            continue
        for ln in lines:
            amount = ln.debit_vnd or ln.credit_vnd or Decimal("0")
            debit_acc = ln.account_code if (ln.debit_vnd and ln.debit_vnd > 0) else ""
            credit_acc = ln.account_code if not debit_acc else ""
            rows.append(
                [
                    v.voucher_date.strftime("%d/%m/%Y"),
                    v.voucher_no,
                    ln.description or v.description,
                    debit_acc,
                    credit_acc,
                    _vnd(amount),
                ]
            )
    return headers, rows


def _data_s03b(company, fy: int, period: int, request) -> tuple[list[str], list[list[str]]]:
    """General Ledger (S03b-DN) — grouped by account code."""
    headers = ["Số CT", "Ngày", "Diễn giải", "TK Đối ứng", "Nợ", "Có", "Số dư"]
    account_code = request.GET.get("account_code", "").strip()
    lines_qs = VoucherLine.objects.select_related("voucher").filter(
        voucher__company=company, voucher__fiscal_year=fy, voucher__period=period
    )
    if account_code:
        lines_qs = lines_qs.filter(account_code__startswith=account_code)
    lines_qs = lines_qs.order_by("account_code", "voucher__voucher_date", "voucher__voucher_no")
    rows: list[list[str]] = []
    running = Decimal("0")
    for ln in lines_qs:
        debit = ln.debit_vnd or Decimal("0")
        credit = ln.credit_vnd or Decimal("0")
        running += debit - credit
        rows.append(
            [
                ln.voucher.voucher_no,
                ln.voucher.voucher_date.strftime("%d/%m/%Y"),
                ln.description or ln.voucher.description,
                "",
                _vnd(debit),
                _vnd(credit),
                _vnd(running),
            ]
        )
    return headers, rows


def _data_s06(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """Trial Balance (S06-DN)."""
    headers = ["TK", "Tên TK", "Nợ ĐK", "Có ĐK", "PS Nợ", "PS Có", "Nợ CK", "Có CK"]
    balances = AccountPeriodBalance.objects.filter(
        fiscal_year=fy, period=period, company=company
    ).order_by("account_code")
    rows: list[list[str]] = []
    for b in balances:
        od = b.opening_debit or 0
        oc = b.opening_credit or 0
        pd_ = b.period_debit or 0
        pc = b.period_credit or 0
        cd_ = b.closing_debit or 0
        cc = b.closing_credit or 0
        if od == 0 and oc == 0 and pd_ == 0 and pc == 0:
            continue
        rows.append(
            [
                b.account_code,
                "",
                _vnd(od),
                _vnd(oc),
                _vnd(pd_),
                _vnd(pc),
                _vnd(cd_),
                _vnd(cc),
            ]
        )
    return headers, rows


def _data_detail_book(
    company, fy: int, period: int, prefixes: list[str]
) -> tuple[list[str], list[list[str]]]:
    """Cash/Bank detail book — S07 (111), S08 (112)."""
    headers = ["Số CT", "Ngày", "Diễn giải", "Đối tượng", "Nợ", "Có", "Số tồn"]
    from django.db.models import Q

    acc_filter = Q()
    for p in prefixes:
        acc_filter |= Q(account_code__startswith=p)
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
    rows: list[list[str]] = []
    for ln in lines_qs:
        debit = ln.debit_vnd or Decimal("0")
        credit = ln.credit_vnd or Decimal("0")
        running = (ln.running_balance_debit or Decimal("0")) - (
            ln.running_balance_credit or Decimal("0")
        )
        rows.append(
            [
                ln.voucher.voucher_no,
                ln.voucher.voucher_date.strftime("%d/%m/%Y"),
                ln.description or ln.voucher.description,
                f"{ln.object_code or ''} {ln.object_name or ''}".strip(),
                _vnd(debit),
                _vnd(credit),
                _vnd(running),
            ]
        )
    return headers, rows


def _data_s07(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    return _data_detail_book(company, fy, period, ["111"])


def _data_s08(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    return _data_detail_book(company, fy, period, ["112"])


def _data_s35(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """Sales Detail (S35-DN) — revenue from TK 511."""
    headers = ["Số CT", "Ngày", "Diễn giải", "Khách hàng", "MST", "Số tiền"]
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
    rows: list[list[str]] = []
    for ln in lines_qs:
        amount = ln.credit_vnd or Decimal("0")
        rows.append(
            [
                ln.voucher.voucher_no,
                ln.voucher.voucher_date.strftime("%d/%m/%Y"),
                ln.description or ln.voucher.description,
                ln.object_name or "",
                ln.object_code or "",
                _vnd(amount),
            ]
        )
    return headers, rows


def _data_b01(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """Balance Sheet (B01-DN) — from BalanceSheetService."""
    headers = ["STT", "Chỉ tiêu", "Mã số", "Số cuối kỳ"]
    data = BalanceSheetService(company=company).generate(fy, period)
    rows: list[list[str]] = []
    config_lines = data.get("config_lines", [])
    if config_lines:
        for ln in config_lines:
            stt = ln.raw_config.stt if ln.raw_config else ""
            rows.append(
                [
                    stt,
                    ln.chi_tieu or "",
                    ln.ma_so or "",
                    _vnd(ln.value),
                ]
            )
    else:
        for r in data.get("assets", {}).get("rows", []):
            rows.append(["", r.get("account_code", ""), "TS", _vnd(r.get("amount", 0))])
        for r in data.get("liabilities_equity", {}).get("liabilities", []):
            rows.append(["", r.get("account_code", ""), "L", _vnd(r.get("amount", 0))])
        for r in data.get("liabilities_equity", {}).get("equity", []):
            rows.append(["", r.get("account_code", ""), "E", _vnd(r.get("amount", 0))])
    return headers, rows


def _data_b02(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """P&L (B02-DN) — from PnLService."""
    headers = ["STT", "Chỉ tiêu", "Mã số", "Kỳ này"]
    data = PnLService(company=company).generate(fy, period)
    rows: list[list[str]] = []
    config_lines = data.get("config_lines", [])
    if config_lines:
        for ln in config_lines:
            stt = ln.raw_config.stt if ln.raw_config else ""
            rows.append(
                [
                    stt,
                    ln.chi_tieu or "",
                    ln.ma_so or "",
                    _vnd(ln.value),
                ]
            )
    else:
        named_keys = [
            ("01", "Doanh thu", data.get("revenue", 0)),
            ("02", "Giá vốn hàng bán", data.get("cogs", 0)),
            ("03", "Lợi nhuận gộp", data.get("gross_profit", 0)),
            ("04", "Doanh thu tài chính", data.get("financial_income", 0)),
            ("05", "Chi phí tài chính", data.get("financial_expense", 0)),
            ("06", "Chi phí bán hàng", data.get("selling_expense", 0)),
            ("07", "Chi phí quản lý DN", data.get("admin_expense", 0)),
            ("08", "LN HĐKD", data.get("operating_profit", 0)),
            ("09", "Thu nhập khác", data.get("other_income", 0)),
            ("10", "Chi phí khác", data.get("other_expense", 0)),
            ("11", "LN khác", data.get("other_profit", 0)),
            ("12", "LN trước thuế", data.get("profit_before_tax", 0)),
            ("13", "Chi phí TNDN", data.get("pit_expense", 0)),
            ("14", "LN sau thuế", data.get("profit_after_tax", 0)),
        ]
        for ma_so, chi_tieu, value in named_keys:
            rows.append(["", chi_tieu, ma_so, _vnd(value)])
    return headers, rows


def _data_b03_direct(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """Cash Flow Direct (B03-DN) — from CashFlowService.generate_direct()."""
    headers = ["STT", "Chỉ tiêu", "Mã số", "Trong kỳ"]
    data = CashFlowService(company=company).generate_direct(fy, period)
    return _b03_rows(headers, data)


def _data_b03_indirect(company, fy: int, period: int) -> tuple[list[str], list[list[str]]]:
    """Cash Flow Indirect (B03-DN) — from CashFlowService.generate_indirect()."""
    headers = ["STT", "Chỉ tiêu", "Mã số", "Trong kỳ"]
    data = CashFlowService(company=company).generate_indirect(fy, period)
    return _b03_rows(headers, data)


def _b03_rows(headers: list[str], data: dict) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    config_lines = data.get("config_lines", [])
    if config_lines:
        for ln in config_lines:
            stt = ln.raw_config.stt if ln.raw_config else ""
            rows.append(
                [
                    stt,
                    ln.chi_tieu or "",
                    ln.ma_so or "",
                    _vnd(ln.value),
                ]
            )
    else:
        named_keys = [
            ("01", "Tiền thu từ KH", data.get("operating_in", 0)),
            ("02", "Tiền trả cho NCC", data.get("operating_out", 0)),
            ("03", "Dòng tiền HĐHD", data.get("net_operating", 0)),
            ("04", "Tiền thu HĐĐT", data.get("investing_in", 0)),
            ("05", "Tiền chi HĐĐT", data.get("investing_out", 0)),
            ("06", "Dòng tiền HĐĐT", data.get("net_investing", 0)),
            ("07", "Tiền thu HĐTC", data.get("financing_in", 0)),
            ("08", "Tiền chi HĐTC", data.get("financing_out", 0)),
            ("09", "Dòng tiền HĐTC", data.get("net_financing", 0)),
            ("10", "Tăng/Giảm tiền", data.get("net_change", 0)),
        ]
        for ma_so, chi_tieu, value in named_keys:
            rows.append(["", chi_tieu, ma_so, _vnd(value)])
    return headers, rows


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


class ReportExportView(LoginRequiredMixin, View):
    """Generic report export endpoint (PDF via WeasyPrint, Excel via openpyxl)."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        report_code = (request.GET.get("report") or "").strip()
        fmt = (request.GET.get("format") or "").strip().lower()

        if report_code not in REPORT_META:
            return HttpResponse(
                f"Invalid report code: {report_code!r}. "
                f"Supported: {', '.join(sorted(REPORT_META.keys()))}",
                status=400,
            )
        if fmt not in ("pdf", "xlsx"):
            return HttpResponse(
                f"Invalid format: {fmt!r}. Supported: pdf, xlsx",
                status=400,
            )

        fy, period = self._parse_period(request)
        company = require_current_company(request)
        report_title, file_code = REPORT_META[report_code]
        headers, rows = self._gather_data(report_code, company, fy, period, request)

        if fmt == "pdf":
            return self._render_pdf(company, report_title, headers, rows, file_code, fy, period)
        return self._render_xlsx(report_title, headers, rows, file_code, fy, period)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _parse_period(request) -> tuple[int, int]:
        today = date.today()
        try:
            fy = int(request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fy = today.year
        try:
            period = int(request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month
        return fy, period

    def _gather_data(
        self,
        report_code: str,
        company,
        fy: int,
        period: int,
        request,
    ) -> tuple[list[str], list[list[str]]]:
        dispatch: dict[str, Callable] = {
            "S03a": lambda: _data_s03a(company, fy, period),
            "S03b": lambda: _data_s03b(company, fy, period, request),
            "S06": lambda: _data_s06(company, fy, period),
            "S07": lambda: _data_s07(company, fy, period),
            "S08": lambda: _data_s08(company, fy, period),
            "S35": lambda: _data_s35(company, fy, period),
            "B01": lambda: _data_b01(company, fy, period),
            "B02": lambda: _data_b02(company, fy, period),
            "B03_direct": lambda: _data_b03_direct(company, fy, period),
            "B03_indirect": lambda: _data_b03_indirect(company, fy, period),
        }
        return dispatch[report_code]()

    def _render_pdf(
        self,
        company,
        report_title: str,
        headers: list[str],
        rows: list[list[str]],
        file_code: str,
        fy: int,
        period: int,
    ) -> HttpResponse:
        company_name = (company.name if company else "Công ty") or "Công ty"
        period_label = _period_label(fy, period)
        html_string = render_to_string(
            "modern/reporting/report_export_pdf.html",
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
        resp["Content-Disposition"] = f'attachment; filename="{file_code}_{fy}{period:02d}.pdf"'
        return resp

    def _render_xlsx(
        self,
        report_title: str,
        headers: list[str],
        rows: list[list[str]],
        file_code: str,
        fy: int,
        period: int,
    ) -> HttpResponse:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = file_code[:31]

        # Row 1 = headers, Row 2+ = data
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
        resp["Content-Disposition"] = f'attachment; filename="{file_code}_{fy}{period:02d}.xlsx"'
        return resp
