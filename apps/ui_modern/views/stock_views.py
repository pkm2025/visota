"""Stock voucher views."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.shortcuts import redirect, render
from django.views.generic import ListView, TemplateView

from apps.core.models import Company
from apps.inventory.models import (
    StockAdjustment,
    StockAdjustmentLine,
    StockLedger,
    StockVoucher,
)
from apps.inventory.services import StockDashboardService, StockService
from apps.master_data.models import Product, Warehouse


class StockVoucherListView(LoginRequiredMixin, ListView):
    template_name = "modern/inventory/stock_list.html"
    context_object_name = "vouchers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        return StockVoucher.objects.select_related("warehouse").order_by("-voucher_date", "-id")

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


class StockDashboardView(LoginRequiredMixin, TemplateView):
    """Overview of all warehouses: total value, low stock alerts."""

    template_name = "modern/inventory/stock_dashboard.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = Company.objects.first()
        if company:
            summary = StockDashboardService.get_summary(company)
            low_stock = StockDashboardService.get_low_stock_products(company)
            valuation = StockDashboardService.get_stock_valuation(company)
        else:
            summary = low_stock = valuation = []
        grand_qty = sum(s["total_quantity"] for s in summary) if summary else Decimal("0")
        grand_value = sum(s["total_value"] for s in summary) if summary else Decimal("0")
        ctx.update(
            {
                "page_title": "Tổng quan kho",
                "summary": summary,
                "low_stock": low_stock,
                "valuation": valuation,
                "grand_qty": grand_qty,
                "grand_value": grand_value,
            }
        )
        return ctx


class StockAdjustmentListView(LoginRequiredMixin, ListView):
    template_name = "modern/inventory/stock_adjustment_list.html"
    context_object_name = "adjustments"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        return StockAdjustment.objects.select_related("warehouse").order_by(
            "-adjustment_date", "-id"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Phiếu kiểm kê"
        return ctx


class StockAdjustmentCreateView(LoginRequiredMixin, TemplateView):
    """Create a stock count/adjustment. POST: per-product system vs counted qty."""

    template_name = "modern/inventory/stock_adjustment_form.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tạo phiếu kiểm kê"
        ctx["warehouses"] = Warehouse.objects.filter(is_active=True).order_by("code")
        return ctx

    def post(self, request, *args, **kwargs):
        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa có công ty nào được cấu hình.")
            return redirect("ui_modern:stock_adjustment_list")

        adjustment_no = request.POST.get("adjustment_no")
        adjustment_date = request.POST.get("adjustment_date")
        warehouse_id = request.POST.get("warehouse_id")
        reason = request.POST.get("reason", "")

        if not (adjustment_no and adjustment_date and warehouse_id):
            messages.error(request, "Vui lòng nhập số phiếu, ngày và kho.")
            return redirect("ui_modern:stock_adjustment_create")

        try:
            warehouse = Warehouse.objects.get(pk=warehouse_id, company=company)
        except Warehouse.DoesNotExist:
            messages.error(request, "Kho không hợp lệ.")
            return redirect("ui_modern:stock_adjustment_create")

        product_ids = request.POST.getlist("product_id[]")
        counted_qtys = request.POST.getlist("counted_quantity[]")

        if not product_ids:
            messages.error(request, "Cần ít nhất một dòng kiểm kê.")
            return redirect("ui_modern:stock_adjustment_create")

        try:
            with db_transaction.atomic():
                adj = StockAdjustment.objects.create(
                    company=company,
                    adjustment_no=adjustment_no,
                    adjustment_date=datetime.strptime(adjustment_date, "%Y-%m-%d").date(),
                    warehouse=warehouse,
                    reason=reason,
                    status="posted",
                )
                line_no = 0
                for i, pid in enumerate(product_ids):
                    if not pid:
                        continue
                    try:
                        product = Product.objects.get(pk=pid, company=company)
                    except Product.DoesNotExist:
                        continue
                    counted = Decimal("0")
                    if i < len(counted_qtys) and counted_qtys[i]:
                        try:
                            counted = Decimal(counted_qtys[i])
                        except InvalidOperation:
                            continue
                    ledger = StockLedger.objects.filter(
                        company=company, product=product, warehouse=warehouse
                    ).first()
                    system_qty = ledger.quantity if ledger else Decimal("0")
                    unit_cost = ledger.avg_cost if ledger else Decimal("0")
                    diff = counted - system_qty
                    if diff == 0:
                        continue  # no diff, skip
                    StockAdjustmentLine.objects.create(
                        adjustment=adj,
                        product=product,
                        system_quantity=system_qty,
                        counted_quantity=counted,
                        difference=diff,
                        unit_cost=unit_cost,
                    )
                    line_no += 1
                    # Apply diff to ledger
                    if ledger:
                        ledger.quantity += diff
                        ledger.amount += diff * unit_cost
                        ledger.recalculate_avg_cost()
                        ledger.save()
                    else:
                        StockLedger.objects.create(
                            company=company,
                            product=product,
                            warehouse=warehouse,
                            quantity=counted,
                            amount=counted * unit_cost,
                            avg_cost=unit_cost,
                            last_transaction_date=adj.adjustment_date,
                            transaction_count=1,
                        )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Lỗi khi tạo phiếu kiểm kê: {exc}")
            return redirect("ui_modern:stock_adjustment_create")

        messages.success(request, f"Đã tạo phiếu kiểm kê {adj.adjustment_no}")
        return redirect("ui_modern:stock_adjustment_list")


class StockCardView(LoginRequiredMixin, TemplateView):
    """Thẻ kho report — running ledger per product + warehouse."""

    template_name = "modern/inventory/stock_card_report.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thẻ kho"
        ctx["products"] = Product.objects.filter(is_active=True).order_by("code")
        ctx["warehouses"] = Warehouse.objects.filter(is_active=True).order_by("code")
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        product_id = request.GET.get("product_id")
        warehouse_id = request.GET.get("warehouse_id")
        if product_id:
            company = Company.objects.first()
            rows = StockDashboardService.get_stock_card(
                company, int(product_id), warehouse_id or None
            )
            ctx["rows"] = rows
            ctx["selected_product"] = product_id
            ctx["selected_warehouse"] = warehouse_id or ""
        else:
            ctx["rows"] = []
        return render(request, self.template_name, ctx)
