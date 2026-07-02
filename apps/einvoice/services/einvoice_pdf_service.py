"""EInvoice PDF generation service — render Vietnamese-standard HĐĐT PDF."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import get_valid_filename

from apps.einvoice.models import EInvoice
from apps.einvoice.services import amount_in_words

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


class EInvoicePDFError(Exception):
    """Raised when PDF generation fails."""


class EInvoicePDFService:
    """Generate human-readable PDF for an EInvoice with company branding."""

    TEMPLATE_NAME = "modern/einvoice/pdf_template.html"

    def generate_pdf(self, einvoice: EInvoice) -> bytes:
        """Render invoice to PDF bytes via WeasyPrint.

        Raises EInvoicePDFError on any failure.
        """
        if not WEASYPRINT_AVAILABLE:
            raise EInvoicePDFError("WeasyPrint not available")
        context = self._build_context(einvoice)
        try:
            html_str = render_to_string(self.TEMPLATE_NAME, context)
            base_url = getattr(settings, "BASE_URL", "http://127.0.0.1:8900")
            return HTML(string=html_str, base_url=base_url).write_pdf()
        except Exception as exc:
            raise EInvoicePDFError(f"Failed to render PDF: {exc}") from exc

    def _build_context(self, einvoice: EInvoice) -> dict:
        company = einvoice.company
        sales_invoice = einvoice.sales_invoice
        items = list(sales_invoice.lines.all().order_by("line_no")) if sales_invoice else []
        amount_text = einvoice.total_in_words or amount_in_words(einvoice.total_amount)
        return {
            "company": company,
            "einvoice": einvoice,
            "sales_invoice": sales_invoice,
            "items": items,
            "subtotal": einvoice.subtotal,
            "vat_rate": einvoice.vat_rate,
            "vat_amount": einvoice.vat_amount,
            "total": einvoice.total_amount,
            "amount_in_words": amount_text,
            "today": timezone.now().date(),
        }

    def get_or_generate(self, einvoice: EInvoice, force: bool = False) -> bytes:
        """Return cached pdf_file if exists, else generate + cache.

        Pass force=True to regenerate.
        """
        if not force and einvoice.pdf_file:
            try:
                return einvoice.pdf_file.read()
            except Exception:
                # File missing from storage; fall through to regenerate
                pass
        pdf_bytes = self.generate_pdf(einvoice)
        self._save_to_einvoice(einvoice, pdf_bytes)
        return pdf_bytes

    def _save_to_einvoice(self, einvoice: EInvoice, pdf_bytes: bytes) -> None:
        """Save bytes to einvoice.pdf_file with deterministic, safe filename."""
        identifier = einvoice.invoice_no or f"pk-{einvoice.pk}"
        safe_name = get_valid_filename(identifier)
        filename = f"einvoice_{safe_name}.pdf"
        einvoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
