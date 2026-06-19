"""Product master data views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.inventory.models import StockLedger
from apps.master_data.models import Product

from ._delete_views import MasterDataDeleteView
from ._export_utils import autosize, new_workbook, style_header, xlsx_response

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


class ProductExportView(LoginRequiredMixin, View):
    """Export all products to .xlsx."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        wb, ws = new_workbook("Hàng hóa")
        headers = [
            "Mã",
            "Tên",
            "Barcode",
            "Loại",
            "ĐVT",
            "PP tính giá",
            "TK kho",
            "TK giá vốn",
            "TK doanh thu",
            "VAT mặc định",
            "Đơn giá",
            "Tồn tối thiểu",
            "Tồn tối đa",
            "Trạng thái",
        ]
        ws.append(headers)
        style_header(ws, len(headers))
        for p in Product.objects.select_related("company").order_by("code"):
            ws.append(
                [
                    p.code,
                    p.name,
                    p.barcode or "",
                    p.get_product_type_display() if p.product_type else "",
                    p.unit_id or "",
                    p.get_cost_method_display() if p.cost_method else "",
                    p.gl_account_inv or "",
                    p.gl_account_cogs or "",
                    p.gl_account_revenue or "",
                    p.default_vat_rate or "",
                    p.default_unit_price or 0,
                    p.min_stock or 0,
                    p.max_stock or 0,
                    "Đang dùng" if p.is_active else "Ngừng",
                ]
            )
        autosize(ws)
        return xlsx_response(wb, "products.xlsx")

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


class ProductDeleteView(MasterDataDeleteView):
    model = Product
    redirect_name = "ui_modern:product_list"


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Product detail — tabs: Info | Stock | Prices | Variants."""

    model = Product
    template_name = "modern/products/product_detail.html"
    context_object_name = "product"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        stock = (
            StockLedger.objects.filter(product=product)
            .select_related("warehouse")
            .order_by("warehouse__code")
        )
        total_qty = stock.aggregate(t=Sum("quantity"))["t"] or 0
        total_value = stock.aggregate(v=Sum("amount"))["v"] or 0
        from apps.documents.services.attachment_service import AttachmentService

        ctx.update(
            {
                "page_title": f"{product.code} - {product.name}",
                "stock_lines": stock,
                "total_qty": total_qty,
                "total_value": total_value,
                "prices": product.prices.all().order_by("min_quantity"),
                "variants": product.variants.all().order_by("code"),
                "attachments": AttachmentService.get_for_object(product),
                "object_type": "master_data.product",
                "object_id": product.pk,
            }
        )
        return ctx
