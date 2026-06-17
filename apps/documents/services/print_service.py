"""PrintService — generate PDF from voucher data using WeasyPrint."""

from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from apps.documents.models import VoucherDocument

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


class PrintService:
    """Generate printable PDF documents from voucher data."""

    TEMPLATE_MAP = {
        "journal": "documents/print/voucher_print.html",
        "cash_receipt": "documents/print/cash_receipt.html",
        "cash_payment": "documents/print/cash_payment.html",
        "sales_invoice": "documents/print/voucher_print.html",
        "purchase_invoice": "documents/print/voucher_print.html",
        "stock_voucher": "documents/print/voucher_print.html",
        "depreciation": "documents/print/voucher_print.html",
        "allocation": "documents/print/voucher_print.html",
        "closing": "documents/print/voucher_print.html",
        "payroll": "documents/print/voucher_print.html",
    }

    def __init__(self, company):
        self.company = company

    def generate_voucher_pdf(self, voucher) -> bytes:
        """Render voucher to PDF bytes (or HTML bytes if WeasyPrint missing)."""
        template = self.TEMPLATE_MAP.get(
            voucher.voucher_type,
            "documents/print/voucher_print.html",
        )
        html_str = render_to_string(
            template,
            {
                "voucher": voucher,
                "company": voucher.company,
            },
        )

        if not WEASYPRINT_AVAILABLE:
            # Fallback: return HTML as bytes (for dev without WeasyPrint installed)
            return html_str.encode("utf-8")

        return HTML(string=html_str).write_pdf()

    def generate_and_save(self, voucher) -> VoucherDocument:
        """Generate PDF and save as VoucherDocument linked to voucher."""
        pdf_bytes = self.generate_voucher_pdf(voucher)

        ext = "html" if not WEASYPRINT_AVAILABLE else "pdf"
        filename = f"{voucher.voucher_no}_{voucher.voucher_date}.{ext}"
        file_obj = ContentFile(pdf_bytes, name=filename)

        return VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type="print_template",
            title=f"{voucher.get_voucher_type_display()} {voucher.voucher_no}",
            file=file_obj,
            status="printed",
        )
