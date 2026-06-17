"""DocumentService — upload, generate print, link to voucher."""

from apps.documents.models import VoucherDocument


class DocumentService:
    """Service for managing voucher documents (scans, prints, external files)."""

    def __init__(self, company):
        self.company = company

    def upload(
        self,
        voucher,
        title,
        file,
        document_type="scanned_upload",
        notes="",
        user=None,
    ):
        """Upload a scanned/external file and link to voucher."""
        return VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type=document_type,
            title=title,
            file=file,
            status="scanned" if document_type == "scanned_upload" else "draft",
            notes=notes,
            uploaded_by=user,
        )

    def generate_print(self, voucher, title=None):
        """Generate a placeholder DB record for a printed document.

        The actual PDF generation happens in PrintService (Task 2).
        This creates the DB record only.
        """
        if not title:
            title = f"{voucher.get_voucher_type_display()} {voucher.voucher_no}"

        return VoucherDocument.objects.create(
            company=self.company,
            voucher=voucher,
            document_type="print_template",
            title=title,
            file=None,  # will be set by PrintService
            status="printed",
        )

    def get_voucher_documents(self, voucher):
        """Get all documents linked to a voucher, newest first."""
        return VoucherDocument.objects.filter(
            company=self.company,
            voucher=voucher,
        ).order_by("-created_at")
