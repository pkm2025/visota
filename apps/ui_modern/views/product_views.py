"""Product master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.master_data.models import Product

_PRODUCT_FIELDS = [
    "code",
    "name",
    "name_en",
    "barcode",
    "product_type",
    "unit_id",
    "product_group_code",
    "weight",
    "volume",
    "cost_method",
    "gl_account_inv",
    "gl_account_cogs",
    "gl_account_revenue",
    "default_vat_rate",
    "default_unit_price",
    "min_stock",
    "max_stock",
    "is_active",
    "notes",
]


class ProductListView(LoginRequiredMixin, ListView):
    template_name = "modern/master_data/product_list.html"
    context_object_name = "products"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        return Product.objects.select_related("company").order_by("code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hàng hóa"
        return ctx


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    template_name = "modern/master_data/product_form.html"
    fields = _PRODUCT_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm hàng hóa"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        from apps.core.models import Company

        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:product_list")


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    template_name = "modern/master_data/product_form.html"
    fields = _PRODUCT_FIELDS
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sửa: {self.object.code} - {self.object.name}"
        ctx["is_new"] = False
        return ctx

    def get_success_url(self):
        return reverse_lazy("ui_modern:product_list")
