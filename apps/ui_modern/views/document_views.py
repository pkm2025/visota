"""Document views — print, upload, download, delete."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.documents.models import VoucherDocument
from apps.documents.services import DocumentService, PrintService
from apps.ledger.models import AccountingVoucher


class VoucherPrintView(LoginRequiredMixin, View):
    """Generate and download PDF for a voucher."""

    login_url = "/auth/login/"

    def get(self, request, pk):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        company = voucher.company

        service = PrintService(company=company)
        pdf_bytes = service.generate_voucher_pdf(voucher)

        # Also persist a document record (audit trail of printed copies)
        service.generate_and_save(voucher)

        ext = "pdf"
        content_type = "application/pdf"
        if pdf_bytes[:4] != b"%PDF":
            # WeasyPrint not available — fallback HTML
            ext = "html"
            content_type = "text/html; charset=utf-8"

        response = HttpResponse(pdf_bytes, content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{voucher.voucher_no}.{ext}"'
        return response


class VoucherUploadView(LoginRequiredMixin, View):
    """Upload scanned document for a voucher."""

    login_url = "/auth/login/"

    def post(self, request, pk):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        company = voucher.company

        title = request.POST.get("title", f"Scan {voucher.voucher_no}")
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Vui lòng chọn file.")
            return redirect("ui_modern:voucher_detail", pk=pk)

        service = DocumentService(company=company)
        doc = service.upload(
            voucher=voucher,
            title=title,
            file=uploaded_file,
            document_type="scanned_upload",
            user=request.user,
        )
        messages.success(request, f"Đã tải lên: {doc.title}")
        return redirect("ui_modern:voucher_detail", pk=pk)


class DocumentDownloadView(LoginRequiredMixin, View):
    """Download a document file."""

    login_url = "/auth/login/"

    def get(self, request, pk):
        doc = get_object_or_404(VoucherDocument, pk=pk)
        if not doc.file:
            messages.error(request, "File không tồn tại.")
            return redirect("ui_modern:voucher_detail", pk=doc.voucher_id)

        response = HttpResponse(doc.file, content_type="application/octet-stream")
        filename = doc.file.name.split("/")[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DocumentDeleteView(LoginRequiredMixin, View):
    """Delete a document."""

    login_url = "/auth/login/"

    def post(self, request, pk):
        doc = get_object_or_404(VoucherDocument, pk=pk)
        voucher_id = doc.voucher_id
        title = doc.title
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()
        messages.success(request, f"Đã xóa: {title}")
        return redirect("ui_modern:voucher_detail", pk=voucher_id)


class VoucherPrintDocxView(LoginRequiredMixin, View):
    """Export voucher as DOCX."""

    login_url = "/auth/login/"

    def get(self, request, pk):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        from apps.documents.services.docx_export_service import DocxExportService

        service = DocxExportService()
        docx_bytes = service.export_voucher(voucher)

        response = HttpResponse(
            docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{voucher.voucher_no}.docx"'
        return response


class ContractExportDocxView(LoginRequiredMixin, View):
    """Export contract as DOCX."""

    login_url = "/auth/login/"

    def get(self, request, pk):
        from apps.contracts.models import Contract, ContractTemplate
        from apps.documents.services.docx_export_service import DocxExportService

        contract = get_object_or_404(Contract, pk=pk)

        # Find matching template by type
        template = ContractTemplate.objects.filter(
            contract_type=contract.contract_type, is_active=True
        ).first()

        service = DocxExportService()
        if template:
            docx_bytes = service.export_contract_from_template(contract, template)
        else:
            # Fallback: basic export
            template = ContractTemplate(name=contract.description or "Hợp đồng", legal_basis="")
            docx_bytes = service.export_contract_from_template(contract, template)

        response = HttpResponse(
            docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{contract.contract_no}.docx"'
        return response


class TrialBalanceDocxView(LoginRequiredMixin, View):
    """Export trial balance as DOCX."""

    login_url = "/auth/login/"

    def get(self, request):
        from datetime import date
        from decimal import Decimal

        from apps.core.models import Company
        from apps.ledger.models import AccountPeriodBalance

        today = date.today()
        fiscal_year = int(request.GET.get("fiscal_year", today.year))
        period = int(request.GET.get("period", today.month))

        company = Company.objects.first()
        balances = list(
            AccountPeriodBalance.objects.filter(
                company=company, fiscal_year=fiscal_year, period=period
            ).order_by("account_code")
        )

        # Filter non-zero
        balances = [
            b
            for b in balances
            if any(
                [
                    b.opening_debit,
                    b.opening_credit,
                    b.period_debit,
                    b.period_credit,
                    b.closing_debit,
                    b.closing_credit,
                ]
            )
        ]

        totals = {
            "opening_debit": sum((b.opening_debit or 0 for b in balances), Decimal("0")),
            "opening_credit": sum((b.opening_credit or 0 for b in balances), Decimal("0")),
            "period_debit": sum((b.period_debit or 0 for b in balances), Decimal("0")),
            "period_credit": sum((b.period_credit or 0 for b in balances), Decimal("0")),
            "closing_debit": sum((b.closing_debit or 0 for b in balances), Decimal("0")),
            "closing_credit": sum((b.closing_credit or 0 for b in balances), Decimal("0")),
        }

        from apps.documents.services.docx_export_service import DocxExportService

        service = DocxExportService()
        docx_bytes = service.export_trial_balance(balances, fiscal_year, period, totals)

        response = HttpResponse(
            docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = (
            f'attachment; filename="BCDTK_{period}_{fiscal_year}.docx"'
        )
        return response
