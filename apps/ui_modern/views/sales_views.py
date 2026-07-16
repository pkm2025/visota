"""Sales invoice views."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice
from apps.sales.services import SalesInvoiceService
from apps.ui_modern.mixins import require_current_company


class SalesInvoiceListView(LoginRequiredMixin, ListView):
    template_name = "modern/sales/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return (
            SalesInvoice.objects.filter(company=company)
            .select_related("customer")
            .order_by("-invoice_date", "-id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hóa đơn bán hàng"
        return ctx


class SalesInvoiceCreateView(LoginRequiredMixin, TemplateView):
    """Custom POST handling that delegates to SalesInvoiceService.create()."""

    template_name = "modern/sales/invoice_form.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = require_current_company(self.request)
        ctx["page_title"] = "Tạo hóa đơn bán"
        ctx["customers"] = Customer.objects.filter(company=company, is_active=True).order_by("code")
        ctx["products"] = Product.objects.filter(company=company, is_active=True).order_by("code")
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)

        customer_id = request.POST.get("customer_id")
        invoice_no = request.POST.get("invoice_no")
        invoice_date = request.POST.get("invoice_date")

        if not (customer_id and invoice_no and invoice_date):
            messages.error(request, "Vui lòng nhập đầy đủ khách hàng, số hóa đơn và ngày.")
            return redirect("ui_modern:sales_invoice_create")

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
            messages.error(request, "Hóa đơn cần ít nhất một dòng hàng.")
            return redirect("ui_modern:sales_invoice_create")

        try:
            service = SalesInvoiceService(company=company)
            invoice = service.create(
                {
                    "invoice_no": invoice_no,
                    "invoice_date": datetime.strptime(invoice_date, "%Y-%m-%d").date(),
                    "customer_id": int(customer_id),
                    "lines": lines,
                    "post": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 — surface any service error to the UI
            messages.error(request, f"Lỗi khi tạo hóa đơn: {exc}")
            return redirect("ui_modern:sales_invoice_create")

        messages.success(request, f"Đã tạo hóa đơn {invoice.invoice_no}")
        return redirect("ui_modern:sales_invoice_list")
