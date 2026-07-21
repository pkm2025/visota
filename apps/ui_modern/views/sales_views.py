"""Sales invoice views."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.master_data.models import Customer, Product
from apps.sales.models import SalesInvoice
from apps.sales.services import SalesInvoiceService
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


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


class SalesInvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Custom POST handling that delegates to SalesInvoiceService.create()."""

    template_name = "modern/sales/invoice_form.html"
    login_url = "/auth/login/"
    required_permission = "sales.access"

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


class SalesInvoiceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Delete a sales invoice and reverse its ledger entries.

    Unposts the linked accounting/DNSN voucher (reversing ledger entries),
    deletes the voucher, then deletes the invoice. Any unpost failure is
    surfaced to the user.
    """

    login_url = "/auth/login/"
    required_permission = "sales.access"

    def post(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        invoice = get_object_or_404(SalesInvoice, pk=pk, company=company)
        service = SalesInvoiceService(company=company)
        invoice_no = invoice.invoice_no

        try:
            service.unpost(invoice)
        except Exception as exc:  # noqa: BLE001 — surface, don't crash
            import logging

            logging.getLogger("apps.ui_modern").exception(
                "unpost failed for sales invoice %s: %s", invoice_no, exc
            )
            messages.error(
                request,
                f"Không thể bỏ ghi sổ hóa đơn {invoice_no}. "
                f"Vui lòng kiểm tra kỳ kế toán hoặc liên hệ quản trị viên.",
            )
            return redirect("ui_modern:sales_invoice_list")

        # Delete linked vouchers (unpost already reversed ledger entries)
        if invoice.gl_voucher_id:
            invoice.gl_voucher.delete()
        if invoice.dnsn_voucher_id:
            invoice.dnsn_voucher.delete()

        invoice.delete()
        messages.success(request, f"Đã xóa hóa đơn {invoice_no}")
        return redirect("ui_modern:sales_invoice_list")

    def get(self, request, pk, *args, **kwargs):
        return redirect("ui_modern:sales_invoice_list")
