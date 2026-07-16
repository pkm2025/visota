"""Customer master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.master_data.models import Customer

from ..mixins import require_current_company
from ._delete_views import MasterDataDeleteView
from ._export_utils import autosize, new_workbook, style_header, xlsx_response

_CUSTOMER_FIELDS = [
    "code",
    "name",
    "name_en",
    "short_name",
    "tax_code",
    "address",
    "phone",
    "email",
    "customer_group_code",
    "sales_staff_code",
    "payment_terms",
    "credit_limit",
    "currency_code",
    "default_vat_rate",
    "gl_account_receivable",
    "is_supplier",
    "is_active",
    "notes",
]


class CustomerListView(LoginRequiredMixin, ListView):
    template_name = "modern/master_data/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return Customer.objects.filter(company=company).select_related("company").order_by("code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Khách hàng"
        return ctx


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = "modern/master_data/customer_form.html"
    fields = _CUSTOMER_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm khách hàng"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = require_current_company(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:customer_list")


class CustomerExportView(LoginRequiredMixin, View):
    """Export all customers to .xlsx."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        company = require_current_company(request)
        wb, ws = new_workbook("Khách hàng")
        headers = [
            "Mã",
            "Tên",
            "Tên EN",
            "MST",
            "Địa chỉ",
            "Điện thoại",
            "Email",
            "Hạn thanh toán",
            "Hạn mức tín dụng",
            "Nhóm",
            "Trạng thái",
        ]
        ws.append(headers)
        style_header(ws, len(headers))
        for c in (
            Customer.objects.filter(company=company).select_related("company").order_by("code")
        ):
            ws.append(
                [
                    c.code,
                    c.name,
                    c.name_en or "",
                    c.tax_code or "",
                    c.address or "",
                    c.phone or "",
                    c.email or "",
                    c.payment_terms or "",
                    c.credit_limit or 0,
                    c.customer_group_code or "",
                    "Đang dùng" if c.is_active else "Ngừng",
                ]
            )
        autosize(ws)
        return xlsx_response(wb, "customers.xlsx")


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = "modern/master_data/customer_form.html"
    fields = _CUSTOMER_FIELDS
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return Customer.objects.filter(company=company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sửa: {self.object.code} - {self.object.name}"
        ctx["is_new"] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy("ui_modern:customer_list")


class CustomerDeleteView(MasterDataDeleteView):
    model = Customer
    redirect_name = "ui_modern:customer_list"
