"""Vendor master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.master_data.models import Vendor

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
        return Vendor.objects.select_related("company").order_by("code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Nhà cung cấp"
        return ctx


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
        from apps.core.models import Company

        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:vendor_list")


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    template_name = "modern/master_data/vendor_form.html"
    fields = _VENDOR_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sửa: {self.object.code} - {self.object.name}"
        ctx["is_new"] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy("ui_modern:vendor_list")
