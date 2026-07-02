"""E-invoice UI views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.models import Company

from .models import EInvoice
from .services import EInvoiceReportService, EInvoiceService


class EInvoiceListView(LoginRequiredMixin, ListView):
    template_name = "modern/einvoice/list.html"
    context_object_name = "einvoices"
    paginate_by = 50
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        qs = EInvoice.objects.filter(company=company).select_related("sales_invoice")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hóa đơn điện tử"
        ctx["status_choices"] = EInvoice.Status.choices
        return ctx


class EInvoiceDetailView(LoginRequiredMixin, DetailView):
    template_name = "modern/einvoice/detail.html"
    context_object_name = "einvoice"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        # ponytail: scope by current_company — IDOR guard, mirrors XML/JSON views.
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        return EInvoice.objects.filter(company=company).select_related(
            "sales_invoice", "company", "issued_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"HĐĐT {self.object.invoice_no or self.object.transaction_id}"
        return ctx


class EInvoiceIssueFromSalesView(LoginRequiredMixin, View):
    """POST: create draft EInvoice from a SalesInvoice."""

    login_url = "/auth/login/"

    def post(self, request, sales_invoice_id, *args, **kwargs):
        from apps.sales.models import SalesInvoice

        si = get_object_or_404(SalesInvoice, pk=sales_invoice_id)
        ei = EInvoiceService.issue_from_sales_invoice(si, issued_by=request.user)
        messages.success(
            request,
            f"Đã tạo HĐĐT nháp #{ei.transaction_id} cho hóa đơn {si.invoice_no}.",
        )
        return redirect("ui_modern:einvoice_detail", pk=ei.pk)


class EInvoicePublishView(LoginRequiredMixin, View):
    """POST: mark as issued — assigns invoice_no + (optionally) calls provider API."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        # ponytail: scope by current_company — IDOR guard.
        company = getattr(request, "current_company", None) or Company.objects.first()
        ei = get_object_or_404(EInvoice, pk=pk, company=company)
        invoice_no = request.POST.get("invoice_no", "").strip()
        try:
            EInvoiceService.publish(ei, invoice_no=invoice_no or None)
            messages.success(request, f"Đã phát hành HĐĐT {ei.invoice_no}")
        except Exception as e:
            messages.error(request, f"Lỗi phát hành: {e}")
        return redirect("ui_modern:einvoice_detail", pk=pk)


class EInvoiceCancelView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        # ponytail: scope by current_company — IDOR guard.
        company = getattr(request, "current_company", None) or Company.objects.first()
        ei = get_object_or_404(EInvoice, pk=pk, company=company)
        reason = request.POST.get("reason", "")
        if not reason.strip():
            messages.error(request, "Cần nhập lý do hủy.")
            return redirect("ui_modern:einvoice_detail", pk=pk)
        EInvoiceService.cancel(ei, reason)
        messages.warning(request, f"Đã hủy HĐĐT {ei.invoice_no}")
        return redirect("ui_modern:einvoice_detail", pk=pk)


class EInvoiceXmlDownloadView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def get(self, request, pk, *args, **kwargs):
        # ponytail: scope by current_company — same IDOR guard as PDF view.
        company = getattr(request, "current_company", None) or Company.objects.first()
        ei = get_object_or_404(EInvoice, pk=pk, company=company)
        if not ei.xml_file:
            return HttpResponse("No XML", status=404)
        response = HttpResponse(ei.xml_file.read(), content_type="application/xml")
        # ponytail: sanitize filename for Content-Disposition — header injection guard.
        raw = ei.invoice_no or str(ei.transaction_id)
        safe = (
            raw.replace('"', "")
            .replace("/", "-")
            .replace("\\", "-")
            .replace("\r", "")
            .replace("\n", "")
        )
        response["Content-Disposition"] = f'attachment; filename="einvoice_{safe}.xml"'
        return response


class EInvoiceJsonDownloadView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def get(self, request, pk, *args, **kwargs):
        # ponytail: scope by current_company — same IDOR guard as PDF view.
        company = getattr(request, "current_company", None) or Company.objects.first()
        ei = get_object_or_404(EInvoice, pk=pk, company=company)
        if not ei.json_file:
            return HttpResponse("No JSON", status=404)
        response = HttpResponse(ei.json_file.read(), content_type="application/json")
        # ponytail: sanitize filename for Content-Disposition — header injection guard.
        raw = ei.invoice_no or str(ei.transaction_id)
        safe = (
            raw.replace('"', "")
            .replace("/", "-")
            .replace("\\", "-")
            .replace("\r", "")
            .replace("\n", "")
        )
        response["Content-Disposition"] = f'attachment; filename="einvoice_{safe}.json"'
        return response


class EInvoiceReportView(LoginRequiredMixin, View):
    """POST: generate BC01 report for given period."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))
        batch = EInvoiceReportService.generate_bc01(company, month, year, submitted_by=request.user)
        messages.success(
            request,
            f"Đã tạo BC01 {month:02d}/{year}: {batch.invoice_count} HĐ, "
            f"{batch.total_amount:,.0f} VND",
        )
        if batch.xml_file:
            return redirect(batch.xml_file.url)
        return redirect("ui_modern:einvoice_list")
