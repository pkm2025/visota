"""Customer master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.master_data.models import Customer

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
        return Customer.objects.select_related("company").order_by("code")

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
        # TODO: use request.current_company once tenant middleware wired into views
        from apps.core.models import Company

        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:customer_list")


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = "modern/master_data/customer_form.html"
    fields = _CUSTOMER_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sửa: {self.object.code} - {self.object.name}"
        ctx["is_new"] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy("ui_modern:customer_list")
