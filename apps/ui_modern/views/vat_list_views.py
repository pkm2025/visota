"""VAT Input/Output List views (M2.7, VAL-M2-021..032).

Two list views display voucher lines carrying tax metadata in the TT80
"bảng kê" (schedule) format:

- ``VATInputList`` at ``/modern/reports/vat-input-list/`` filters
  ``invoice_group_code='4'`` (INPUT).
- ``VATOutputList`` at ``/modern/reports/vat-output-list/`` filters
  ``invoice_group_code='5'`` (OUTPUT).

Both render the same 13-column TT80 layout and support Excel export via
``?format=xlsx``.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic import View

from apps.ledger.models import VoucherLine

# 13 TT80 columns displayed (Vietnamese labels, in order).
VAT_LIST_COLUMNS: list[str] = [
    "STT",
    "Ngày HĐ",
    "Số HĐ",
    "Ký hiệu",
    "Mẫu số",
    "Tên KH",
    "MST",
    "Tiền hàng",
    "Thuế suất",
    "Tiền thuế",
    "Tổng tiền",
    "Tk nợ",
    "Tk có",
]


def _parse_period(request) -> tuple[int, int]:
    """Extract ``(fiscal_year, period)`` integers from query params."""
    today = date.today()
    try:
        fiscal_year = int(request.GET.get("fiscal_year", today.year))
    except (TypeError, ValueError):
        fiscal_year = today.year
    try:
        period = int(request.GET.get("period", today.month))
    except (TypeError, ValueError):
        period = today.month
    return fiscal_year, period


def _queryset_for(invoice_group_code: str, fiscal_year: int, period: int):
    """Return VoucherLines for the given invoice_group + period, posted only."""
    return (
        VoucherLine.objects.select_related("voucher", "tax_code", "invoice_group_code")
        .filter(
            invoice_group_code_id=invoice_group_code,
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
            voucher__status__gte=2,
        )
        .order_by("voucher__voucher_date", "voucher__voucher_no", "line_no")
    )


def _build_row(idx: int, line: VoucherLine) -> dict:
    """Map a VoucherLine to a TT80 row dict.

    Keys use ASCII identifiers so they can be referenced inside Django
    template variable syntax (which cannot handle Vietnamese diacritics
    or spaces).  The displayed Vietnamese column labels live in
    ``VAT_LIST_COLUMNS``.
    """
    goods = line.goods_amount_vnd or Decimal("0")
    tax_amt = line.tax_amount_vnd or Decimal("0")
    total = goods + tax_amt
    return {
        "stt": idx,
        "invoice_date": line.invoice_date or line.voucher.voucher_date,
        "invoice_no": line.invoice_no or "",
        "invoice_symbol": line.invoice_symbol or "",
        "invoice_form": line.invoice_form or "",
        "object_name": line.object_name or "",
        "mst": line.object_code or "",
        "goods_amount": goods,
        "tax_rate": line.tax_rate or Decimal("0"),
        "tax_amount": tax_amt,
        "total_amount": total,
        "debit_account": line.account_code or "",
        "credit_account": line.offset_account_code or "",
    }


class _BaseVATListView(LoginRequiredMixin, View):
    """Shared logic for VAT input/output list (HTML + Excel)."""

    login_url = "/auth/login/"
    invoice_group_code: str = ""
    page_title: str = ""
    template_name: str = ""

    # -- queryset -------------------------------------------------------

    def _rows(self, fiscal_year: int, period: int) -> list[dict]:
        qs = _queryset_for(self.invoice_group_code, fiscal_year, period)
        return [_build_row(i, line) for i, line in enumerate(qs, start=1)]

    # -- response dispatch ---------------------------------------------

    def get(self, request, *args, **kwargs):
        fiscal_year, period = _parse_period(request)
        rows = self._rows(fiscal_year, period)
        fmt = (request.GET.get("format") or "").strip().lower()
        if fmt == "xlsx":
            return self._render_xlsx(rows, fiscal_year, period)
        return self._render_html(request, rows, fiscal_year, period)

    # -- HTML -----------------------------------------------------------

    def _render_html(
        self, request, rows: list[dict], fiscal_year: int, period: int
    ) -> HttpResponse:
        from django.shortcuts import render

        totals = {
            "goods": sum((r["goods_amount"] for r in rows), Decimal("0")),
            "tax": sum((r["tax_amount"] for r in rows), Decimal("0")),
            "total": sum((r["total_amount"] for r in rows), Decimal("0")),
        }
        context = {
            "page_title": self.page_title,
            "fiscal_year": fiscal_year,
            "period": period,
            "columns": VAT_LIST_COLUMNS,
            "rows": rows,
            "totals": totals,
            "period_choices": list(range(1, 13)),
            "year_choices": [2024, 2025, 2026, 2027],
        }
        return render(request, self.template_name, context)

    # -- Excel ----------------------------------------------------------

    def _render_xlsx(self, rows: list[dict], fiscal_year: int, period: int) -> HttpResponse:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = self.page_title[:31] or "VAT"
        ws.append(VAT_LIST_COLUMNS)
        for r in rows:
            ws.append(
                [
                    r["stt"],
                    r["invoice_date"].strftime("%d/%m/%Y") if r["invoice_date"] else "",
                    r["invoice_no"],
                    r["invoice_symbol"],
                    r["invoice_form"],
                    r["object_name"],
                    r["mst"],
                    float(r["goods_amount"]),
                    float(r["tax_rate"]),
                    float(r["tax_amount"]),
                    float(r["total_amount"]),
                    r["debit_account"],
                    r["credit_account"],
                ]
            )
        # Totals row
        ws.append(
            [
                "",
                "",
                "",
                "",
                "",
                "",
                "Tổng cộng",
                float(sum((r["goods_amount"] for r in rows), Decimal("0"))),
                "",
                float(sum((r["tax_amount"] for r in rows), Decimal("0"))),
                float(sum((r["total_amount"] for r in rows), Decimal("0"))),
                "",
                "",
            ]
        )

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        filename = (
            f"{'vat-input' if self.invoice_group_code == '4' else 'vat-output'}"
            f"-{fiscal_year}{period:02d}.xlsx"
        )
        resp = HttpResponse(
            buf.getvalue(),
            content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp


class VATInputListView(_BaseVATListView):
    """Bảng kê hóa đơn đầu vào (invoice_group=#4, INPUT)."""

    invoice_group_code = "4"
    page_title = "Bảng kê hóa đơn GTGT đầu vào"
    template_name = "modern/reporting/vat_input_list.html"


class VATOutputListView(_BaseVATListView):
    """Bảng kê hóa đơn đầu ra (invoice_group=#5, OUTPUT)."""

    invoice_group_code = "5"
    page_title = "Bảng kê hóa đơn GTGT đầu ra"
    template_name = "modern/reporting/vat_output_list.html"
