"""Input invoice UI views — list, upload, process."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, TemplateView, View

from apps.core.models import Company
from apps.input_docs.models import InputInvoice
from apps.input_docs.services import InvoiceExtractionService


class InputInvoiceListView(LoginRequiredMixin, ListView):
    """List of input invoices with status badges."""

    template_name = "modern/input_docs/input_invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        return InputInvoice.objects.select_related("purchase_invoice", "processed_by").order_by(
            "-created_at", "-id"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hóa đơn đầu vào"
        ctx["status_badge"] = {
            InputInvoice.ExtractionStatus.PENDING: "warning",
            InputInvoice.ExtractionStatus.EXTRACTED: "info",
            InputInvoice.ExtractionStatus.MATCHED: "success",
            InputInvoice.ExtractionStatus.EXCLUDED: "secondary",
        }
        return ctx


class InputInvoiceUploadView(LoginRequiredMixin, TemplateView):
    """Upload a text/XML invoice file, extract on POST, preview extracted data."""

    template_name = "modern/input_docs/input_invoice_upload.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tải lên hóa đơn đầu vào"
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty nào được cấu hình.")
            return redirect("ui_modern:input_invoice_list")

        raw_text = request.POST.get("raw_text", "") or ""
        xml_text = request.POST.get("xml_text", "") or ""

        uploaded = request.FILES.get("file")
        if uploaded is not None:
            try:
                content = uploaded.read().decode("utf-8", errors="ignore")
            except Exception:
                content = ""
            if uploaded.name.lower().endswith(".xml"):
                xml_text = content
            else:
                raw_text = content

        svc = InvoiceExtractionService(company=company)

        data = {}
        if xml_text:
            data = svc.extract_from_xml(xml_text)
        elif raw_text:
            data = svc.extract_from_text(raw_text)

        if not data:
            messages.error(request, "Không trích xuất được dữ liệu. Hãy dán nội dung XML/text.")
            return redirect("ui_modern:input_invoice_upload")

        inv = InputInvoice.objects.create(
            company=company,
            invoice_no=data.get("invoice_no", ""),
            invoice_date=data.get("invoice_date"),
            seller_tax_code=data.get("seller_tax_code", ""),
            seller_name=data.get("seller_name", ""),
            seller_address=data.get("seller_address", ""),
            amount_before_vat=data.get("amount_before_vat", 0),
            vat_rate=data.get("vat_rate", 0),
            vat_amount=data.get("vat_amount", 0),
            total_amount=data.get("total_amount", 0),
            currency_code=data.get("currency_code", "VND"),
            einvoice_xml=xml_text,
            extracted_data=data,
            extraction_status=InputInvoice.ExtractionStatus.EXTRACTED,
        )

        messages.success(request, f"Đã trích xuất hóa đơn #{inv.id}. Xem trước và xác nhận.")
        return redirect("ui_modern:input_invoice_list")


class InputInvoiceProcessView(LoginRequiredMixin, View):
    """POST triggers extraction + auto-create PI."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        company = Company.objects.first()
        inv = get_object_or_404(InputInvoice, pk=pk, company=company)

        product_id = request.POST.get("product_id")
        if not product_id:
            messages.error(request, "Cần chọn hàng hóa để tạo phiếu nhập mua.")
            return redirect("ui_modern:input_invoice_list")

        svc = InvoiceExtractionService(company=company)
        try:
            svc.auto_create_purchase_invoice(inv, product_id=int(product_id))
            messages.success(request, f"Đã tạo phiếu nhập mua cho hóa đơn {inv.invoice_no}.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Lỗi xử lý: {exc}")
        return redirect("ui_modern:input_invoice_list")
