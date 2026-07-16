"""Vendor master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.master_data.models import Vendor

from ..mixins import require_current_company
from ._delete_views import MasterDataDeleteView
from ._export_utils import autosize, new_workbook, style_header, xlsx_response

_VENDOR_FIELDS = [
    "code",
    "name",
    "name_en",
    "short_name",
    "tax_code",
    "address",
    "phone",
    "email",
    "vendor_group_code",
    "payment_terms",
    "currency_code",
    "gl_account_payable",
    "is_supplier",
    "is_contractor",
    "is_active",
    "notes",
]


class VendorListView(LoginRequiredMixin, ListView):
    template_name = "modern/master_data/vendor_list.html"
    context_object_name = "vendors"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return Vendor.objects.filter(company=company).select_related("company").order_by("code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Nhà cung cấp"
        return ctx


class VendorExportView(LoginRequiredMixin, View):
    """Export all vendors to .xlsx."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        company = require_current_company(request)
        wb, ws = new_workbook("Nhà cung cấp")
        headers = [
            "Mã",
            "Tên",
            "Tên EN",
            "MST",
            "Địa chỉ",
            "Điện thoại",
            "Email",
            "Hạn thanh toán",
            "Nhóm",
            "Loại",
            "Trạng thái",
        ]
        ws.append(headers)
        style_header(ws, len(headers))
        for v in Vendor.objects.filter(company=company).select_related("company").order_by("code"):
            kind = "Nhà thầu" if v.is_contractor else "Hàng hóa"
            ws.append(
                [
                    v.code,
                    v.name,
                    v.name_en or "",
                    v.tax_code or "",
                    v.address or "",
                    v.phone or "",
                    v.email or "",
                    v.payment_terms or "",
                    v.vendor_group_code or "",
                    kind,
                    "Đang dùng" if v.is_active else "Ngừng",
                ]
            )
        autosize(ws)
        return xlsx_response(wb, "vendors.xlsx")


class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    template_name = "modern/master_data/vendor_form.html"
    fields = _VENDOR_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm nhà cung cấp"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = require_current_company(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:vendor_list")


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    template_name = "modern/master_data/vendor_form.html"
    fields = _VENDOR_FIELDS
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return Vendor.objects.filter(company=company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sửa: {self.object.code} - {self.object.name}"
        ctx["is_new"] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy("ui_modern:vendor_list")


class VendorDeleteView(MasterDataDeleteView):
    model = Vendor
    redirect_name = "ui_modern:vendor_list"
