"""Stock voucher views."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from apps.inventory.models import StockVoucher
from apps.inventory.services import StockService
from apps.master_data.models import Product, Warehouse


class StockVoucherListView(LoginRequiredMixin, ListView):
    template_name = "modern/inventory/stock_list.html"
    context_object_name = "vouchers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        return StockVoucher.objects.select_related("warehouse").order_by(
            "-voucher_date", "-id"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Phiếu nhập/xuất/ chuyển kho"
        return ctx


class StockVoucherCreateView(LoginRequiredMixin, TemplateView):
    """Custom POST handling that delegates to StockService.create_receipt() / create_issue()."""

    template_name = "modern/inventory/stock_form.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tạo phiếu nhập/xuất kho"
        ctx["warehouses"] = Warehouse.objects.filter(is_active=True).order_by("code")
        ctx["products"] = Product.objects.filter(is_active=True).order_by("code")
        ctx["voucher_types"] = StockVoucher.VoucherType.choices
        return ctx

    def post(self, request, *args, **kwargs):
        from apps.core.models import Company

        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty nào được cấu hình.")
            return redirect("ui_modern:stock_voucher_list")

        voucher_type = request.POST.get("voucher_type", StockVoucher.VoucherType.RECEIPT)
        voucher_no = request.POST.get("voucher_no")
        voucher_date = request.POST.get("voucher_date")
        warehouse_id = request.POST.get("warehouse_id")

        if not (voucher_no and voucher_date and warehouse_id):
            messages.error(request, "Vui lòng nhập số phiếu, ngày và kho.")
            return redirect("ui_modern:stock_voucher_create")

        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        unit_costs = request.POST.getlist("unit_cost[]")

        lines = []
        for i, pid in enumerate(product_ids):
            if not pid:
                continue
            try:
                qty = Decimal(quantities[i]) if i < len(quantities) else Decimal("0")
                cost = Decimal(unit_costs[i]) if i < len(unit_costs) else Decimal("0")
            except (InvalidOperation, IndexError):
                continue
            lines.append(
                {
                    "product_id": int(pid),
                    "quantity": qty,
                    "unit_cost": cost,
                }
            )

        if not lines:
            messages.error(request, "Phiếu cần ít nhất một dòng hàng.")
            return redirect("ui_modern:stock_voucher_create")

        common = {
            "voucher_no": voucher_no,
            "voucher_date": datetime.strptime(voucher_date, "%Y-%m-%d").date(),
            "warehouse_id": int(warehouse_id),
            "lines": lines,
        }

        try:
            service = StockService(company=company)
            if voucher_type == StockVoucher.VoucherType.ISSUE:
                voucher = service.create_issue(common)
            else:
                voucher = service.create_receipt(common)
        except Exception as exc:  # noqa: BLE001 — surface any service error to the UI
            messages.error(request, f"Lỗi khi tạo phiếu: {exc}")
            return redirect("ui_modern:stock_voucher_create")

        messages.success(request, f"Đã tạo phiếu {voucher.voucher_no}")
        return redirect("ui_modern:stock_voucher_list")
