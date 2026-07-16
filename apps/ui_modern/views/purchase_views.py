"""Purchase invoice views."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from apps.master_data.models import Product, Vendor
from apps.purchasing.models import PurchaseInvoice
from apps.purchasing.services import PurchaseInvoiceService
from apps.ui_modern.mixins import require_current_company


class PurchaseInvoiceListView(LoginRequiredMixin, ListView):
    template_name = "modern/purchasing/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return (
            PurchaseInvoice.objects.filter(company=company)
            .select_related("vendor")
            .order_by("-invoice_date", "-id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Phiếu nhập mua"
        return ctx


class PurchaseInvoiceCreateView(LoginRequiredMixin, TemplateView):
    """Custom POST handling that delegates to PurchaseInvoiceService.create()."""

    template_name = "modern/purchasing/invoice_form.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = require_current_company(self.request)
        ctx["page_title"] = "Tạo phiếu nhập mua"
        ctx["vendors"] = Vendor.objects.filter(company=company, is_active=True).order_by("code")
        ctx["products"] = Product.objects.filter(company=company, is_active=True).order_by("code")
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)

        vendor_id = request.POST.get("vendor_id")
        invoice_no = request.POST.get("invoice_no")
        invoice_date = request.POST.get("invoice_date")

        if not (vendor_id and invoice_no and invoice_date):
            messages.error(request, "Vui lòng nhập đầy đủ NCC, số hóa đơn và ngày.")
            return redirect("ui_modern:purchase_invoice_create")

        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        prices = request.POST.getlist("unit_price[]")

        lines = []
        for i, pid in enumerate(product_ids):
            if not pid:
                continue
            try:
                qty = Decimal(quantities[i]) if i < len(quantities) else Decimal("0")
                price = Decimal(prices[i]) if i < len(prices) else Decimal("0")
            except (InvalidOperation, IndexError):
                continue
            lines.append(
                {
                    "product_id": int(pid),
                    "quantity": qty,
                    "unit_price": price,
                    "vat_rate": Decimal("0.10"),
                }
            )

        if not lines:
            messages.error(request, "Phiếu cần ít nhất một dòng hàng.")
            return redirect("ui_modern:purchase_invoice_create")

        try:
            service = PurchaseInvoiceService(company=company)
            invoice = service.create(
                {
                    "invoice_no": invoice_no,
                    "invoice_date": datetime.strptime(invoice_date, "%Y-%m-%d").date(),
                    "vendor_id": int(vendor_id),
                    "lines": lines,
                    "post": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 — surface any service error to the UI
            messages.error(request, f"Lỗi khi tạo phiếu: {exc}")
            return redirect("ui_modern:purchase_invoice_create")

        messages.success(request, f"Đã tạo phiếu nhập {invoice.invoice_no}")
        return redirect("ui_modern:purchase_invoice_list")
