"""EInvoice PDF download view."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.views import View

from apps.core.models import Company
from apps.einvoice.models import EInvoice
from apps.einvoice.services.einvoice_pdf_service import (
    EInvoicePDFError,
    EInvoicePDFService,
)

logger = logging.getLogger(__name__)


class EinvoicePDFView(LoginRequiredMixin, View):
    """Serve the human-readable PDF for an EInvoice.

    GET /modern/einvoices/<pk>/download/pdf/?force=1
    """

    login_url = "/auth/login/"

    def get(self, request, pk):
        # ponytail: mirror apps/einvoice/views.py company resolution —
        # request.current_company (session-driven) with first() fallback.
        company = getattr(request, "current_company", None) or Company.objects.first()
        try:
            einvoice = EInvoice.objects.get(pk=pk, company=company)
        except EInvoice.DoesNotExist:
            raise Http404("EInvoice not found")

        force = request.GET.get("force") == "1"
        try:
            pdf_bytes = EInvoicePDFService().get_or_generate(einvoice, force=force)
        except EInvoicePDFError:
            logger.exception("PDF generation failed for einvoice pk=%s", pk)
            return HttpResponse(
                "Lỗi tạo PDF. Vui lòng thử lại hoặc liên hệ quản trị viên.",
                status=500,
                content_type="text/plain",
            )

        # ponytail: truncate at first CR/LF, then allowlist filename chars — header injection guard.
        # CRLF is the real injection vector; truncate before it so the injected header token
        # never reaches the response. Then drop quotes/separators from the surviving prefix.
        import re

        raw = einvoice.invoice_no or str(einvoice.pk)
        raw = re.split(r"[\r\n]", raw, maxsplit=1)[0]  # drop injected payload after CRLF
        raw = raw.replace('"', "").replace("/", "-").replace("\\", "-")
        safe_invoice_no = re.sub(r"[^A-Za-z0-9._-]", "", raw)
        filename = f"einvoice_{safe_invoice_no}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
