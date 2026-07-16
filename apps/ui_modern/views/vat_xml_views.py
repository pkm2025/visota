"""VAT Return XML export (TT80/2021).

Endpoint: ``GET /modern/reports/vat-return-xml/?fiscal_year=Y&period=P``

Produces a well-formed XML document following the TT80/2021 schema with
``HSoKhaiThue`` root element and TT80 namespace.  The ``<LTinh>`` node
contains one ``<ctXX>`` element per line code ([21]-[33]) so the numeric
values mirror the HTML view exactly.

The response sets:

- ``Content-Type: application/xml; charset=utf-8``
- ``Content-Disposition: attachment; filename="01GTKT-YYYYMM.xml"``
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape, quoteattr

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from apps.reporting.services.vat_return import VATReturnService
from apps.ui_modern.mixins import require_current_company

# TT80/2021 namespace for the HSoKhaiThue root element.
_TT80_NS = "http://kekhaithue.gdt.gov.vn/TKhaiThue"

# Line codes [21]-[33] emitted in the <LTinh> node.  These mirror the
# HTML view's TT80 layout and must all be present per VAL-M2-017.
_LINE_CODES = [str(c) for c in range(21, 34)]


class VATXmlView(LoginRequiredMixin, View):
    """Return the VAT return as an XML download (01GTKT-YYYYMM.xml)."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        today = date.today()
        try:
            fiscal_year = int(request.GET.get("fiscal_year", today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(request.GET.get("period", today.month))
        except (TypeError, ValueError):
            period = today.month

        company = require_current_company(request)
        data = VATReturnService(company=company).generate(fiscal_year, period)
        values_by_code: dict[str, Decimal] = data["values_by_code"]

        xml_body = self._build_xml(fiscal_year, period, values_by_code)

        response = HttpResponse(xml_body, content_type="application/xml; charset=utf-8")
        filename = f"01GTKT-{fiscal_year}{period:02d}.xml"
        response["Content-Disposition"] = f"attachment; filename={quoteattr(filename)}"
        return response

    @staticmethod
    def _fmt(value: Decimal | None) -> str:
        """Format a Decimal as an integer-like XML text value."""
        if value is None:
            return "0"
        # Normalize and strip trailing zeros for clean output.
        quantized = value.quantize(Decimal("1"))
        return str(quantized)

    def _build_xml(
        self,
        fiscal_year: int,
        period: int,
        values_by_code: dict[str, Decimal],
    ) -> str:
        """Build the TT80/2021 XML string.

        Structure::

            <HSoKhaiThue xmlns="...">
              <TTinTKhaiThue>
                <TTin>
                  <maTKhai>920</maTKhai>
                  <kyTKhai>P06_2026</kyTKhai>
                </TTin>
              </TTinTKhaiThue>
              <PLuc>
                <LTinh>
                  <ct21>0</ct21>
                  ...
                  <ct33>0</ct33>
                </LTinh>
              </PLuc>
            </HSoKhaiThue>
        """
        ky_tkhai = f"P{period:02d}_{fiscal_year}"

        lines: list[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(f'<HSoKhaiThue xmlns="{_TT80_NS}">')
        lines.append("  <TTinTKhaiThue>")
        lines.append("    <TTin>")
        lines.append("      <maTKhai>920</maTKhai>")
        lines.append(f"      <kyTKhai>{escape(ky_tkhai)}</kyTKhai>")
        lines.append("    </TTin>")
        lines.append("  </TTinTKhaiThue>")
        lines.append("  <PLuc>")
        lines.append('    <LTinh id="T_KH_GTGT">')

        for code in _LINE_CODES:
            value = values_by_code.get(code, Decimal("0"))
            lines.append(f"      <ct{code}>{self._fmt(value)}</ct{code}>")

        lines.append("    </LTinh>")
        lines.append("  </PLuc>")
        lines.append("</HSoKhaiThue>")
        return "\n".join(lines) + "\n"
