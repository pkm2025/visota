"""Asset UI views — list, create, depreciation run, dispose, transfer."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.assets.models import (
    AssetCategory,
    AssetTransaction,
    AssetUsingDepartment,
    FixedAsset,
)
from apps.assets.services import AssetLifecycleService, DepreciationService
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class AssetListView(LoginRequiredMixin, ListView):
    """List of fixed assets (TSCĐ + CCDC) for the current company."""

    template_name = "modern/assets/asset_list.html"
    context_object_name = "assets"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        qs = (
            FixedAsset.objects.filter(company=company)
            .select_related("category", "using_department")
            .order_by("asset_code")
        )
        is_tool = self.request.GET.get("is_tool")
        if is_tool in ("0", "1"):
            qs = qs.filter(is_tool=(is_tool == "1"))
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(asset_code__icontains=search) | qs.filter(asset_name__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tài sản"
        return ctx


class AssetCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create a fixed asset. Custom POST pulls default GL accounts from the
    selected category and using_department."""

    template_name = "modern/assets/asset_form.html"
    login_url = "/auth/login/"
    required_permission = "assets.access"

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            self._build_context(),
        )

    def post(self, request, *args, **kwargs):
        ctx = self._build_context()
        company = require_current_company(request)
        required = [
            "asset_code",
            "asset_name",
            "category",
            "using_department",
            "original_cost",
            "start_date",
        ]
        missing = [f for f in required if not request.POST.get(f)]
        if missing:
            messages.error(request, f"Thiếu trường bắt buộc: {', '.join(missing)}")
            ctx["post_data"] = request.POST
            return render(request, self.template_name, ctx, status=200)

        try:
            category = AssetCategory.objects.get(pk=request.POST.get("category"), company=company)
        except AssetCategory.DoesNotExist:
            messages.error(request, "Loại tài sản không hợp lệ")
            ctx["post_data"] = request.POST
            return render(request, self.template_name, ctx, status=200)

        try:
            dept = AssetUsingDepartment.objects.get(
                pk=request.POST.get("using_department"), company=company
            )
        except AssetUsingDepartment.DoesNotExist:
            messages.error(request, "Bộ phận sử dụng không hợp lệ")
            ctx["post_data"] = request.POST
            return render(request, self.template_name, ctx, status=200)

        # Pull default GL accounts from selected category / department
        gl_account = request.POST.get("gl_account") or category.default_gl_account
        depreciation_account = (
            request.POST.get("depreciation_account") or category.default_depreciation_account
        )
        expense_account = (
            request.POST.get("expense_account")
            or dept.default_expense_account
            or category.default_expense_account
            or "642"
        )
        dep_rate = request.POST.get("depreciation_rate") or (
            category.default_depreciation_rate or Decimal("0")
        )
        useful_life = request.POST.get("useful_life_months") or (
            category.default_useful_life_months or 0
        )

        try:
            cost = Decimal(str(request.POST.get("original_cost")))
        except Exception:
            cost = Decimal("0")

        # Build code lookup
        if FixedAsset.objects.filter(
            company=company, asset_code=request.POST.get("asset_code")
        ).exists():
            messages.error(request, "Mã tài sản đã tồn tại")
            ctx["post_data"] = request.POST
            return render(request, self.template_name, ctx, status=200)

        asset = FixedAsset.objects.create(
            company=company,
            asset_code=request.POST.get("asset_code"),
            asset_name=request.POST.get("asset_name"),
            asset_name_en=request.POST.get("asset_name_en", ""),
            category=category,
            using_department=dept,
            gl_account=gl_account,
            depreciation_account=depreciation_account,
            expense_account=expense_account,
            original_cost=cost,
            depreciation_method=FixedAsset.DepreciationMethod.STRAIGHT_LINE,
            depreciation_rate=dep_rate,
            useful_life_months=useful_life,
            start_date=request.POST.get("start_date"),
            is_tool=category.is_for_tool,
            status=FixedAsset.Status.ACTIVE,
            description=request.POST.get("description", ""),
        )

        messages.success(request, f"Đã tạo tài sản {asset.asset_code} - {asset.asset_name}")
        return redirect("ui_modern:asset_list")

    def _build_context(self):
        company = require_current_company(self.request)
        categories_qs = AssetCategory.objects.filter(company=company, is_active=True).order_by(
            "code"
        )
        departments_qs = AssetUsingDepartment.objects.filter(
            company=company, is_active=True
        ).order_by("code")
        return {
            "page_title": "Thêm tài sản",
            "categories": categories_qs,
            "departments": departments_qs,
            "is_new": True,
            "post_data": None,
        }


class DepreciationRunView(LoginRequiredMixin, View):
    """GET shows form; POST runs DepreciationService.calculate_period."""

    template_name = "modern/assets/depreciation_run.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        from datetime import date

        today = date.today()
        return render(
            request,
            self.template_name,
            {
                "page_title": "Tính khấu hao kỳ",
                "default_year": today.year,
                "default_month": today.month,
            },
        )

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)

        try:
            year = int(request.POST.get("year"))
            month = int(request.POST.get("month"))
        except (TypeError, ValueError):
            messages.error(request, "Năm/tháng không hợp lệ")
            return redirect("ui_modern:depreciation_run")

        if not (1 <= month <= 12) or year < 2000:
            messages.error(request, "Năm/tháng không hợp lệ")
            return redirect("ui_modern:depreciation_run")

        result = DepreciationService(company).calculate_period(year, month)

        messages.success(
            request,
            f"Đã tính khấu hao {year}-{month:02d}: "
            f"{result.get('assets_processed', 0)} tài sản, "
            f"tổng {result.get('total_depreciation', 0)} VND",
        )
        return redirect("ui_modern:asset_list")


class AssetDisposeView(LoginRequiredMixin, View):
    """POST handler: dispose/liquidate an asset. Optionally HTMX-rendered modal form."""

    template_name = "modern/assets/asset_dispose.html"
    login_url = "/auth/login/"

    def get(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        asset = get_object_or_404(FixedAsset, pk=pk, company=company)
        return render(
            request,
            self.template_name,
            {"page_title": "Thanh lý tài sản", "asset": asset},
        )

    def post(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        asset = get_object_or_404(FixedAsset, pk=pk, company=company)
        try:
            disposal_value = Decimal(str(request.POST.get("disposal_value") or "0"))
        except Exception:
            disposal_value = Decimal("0")
        reason = request.POST.get("reason", "")

        try:
            txn = AssetLifecycleService().dispose(
                asset, disposal_value=disposal_value, reason=reason
            )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Lỗi khi thanh lý: {exc}")
            return redirect("ui_modern:asset_list")

        messages.success(request, f"Đã thanh lý {asset.asset_code}. Phiếu {txn.transaction_no}.")
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f"<div class='alert alert-success'>Đã thanh lý {asset.asset_code}</div>"
            )
        return redirect("ui_modern:asset_list")


class AssetTransferView(LoginRequiredMixin, View):
    """GET shows form; POST transfers asset to new department."""

    template_name = "modern/assets/asset_transfer.html"
    login_url = "/auth/login/"

    def get(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        asset = get_object_or_404(FixedAsset, pk=pk, company=company)
        departments = AssetUsingDepartment.objects.filter(company=company, is_active=True).order_by(
            "code"
        )
        return render(
            request,
            self.template_name,
            {
                "page_title": "Điều chuyển tài sản",
                "asset": asset,
                "departments": departments,
            },
        )

    def post(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        asset = get_object_or_404(FixedAsset, pk=pk, company=company)
        dept_id = request.POST.get("to_department")
        new_expense = request.POST.get("new_expense_account") or None
        if not dept_id:
            messages.error(request, "Chọn bộ phận nhận.")
            return redirect("ui_modern:asset_transfer", pk=pk)
        try:
            to_dept = AssetUsingDepartment.objects.get(pk=dept_id, company=company)
        except AssetUsingDepartment.DoesNotExist:
            messages.error(request, "Bộ phận không hợp lệ.")
            return redirect("ui_modern:asset_transfer", pk=pk)

        try:
            AssetLifecycleService().transfer(
                asset, to_department=to_dept, new_expense_account=new_expense
            )
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Lỗi khi điều chuyển: {exc}")
            return redirect("ui_modern:asset_list")

        messages.success(request, f"Đã điều chuyển {asset.asset_code} → {to_dept.name}.")
        return redirect("ui_modern:asset_list")


class AssetTransactionListView(LoginRequiredMixin, ListView):
    """History of asset transactions."""

    template_name = "modern/assets/asset_transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        return (
            AssetTransaction.objects.filter(asset__company=company)
            .select_related("asset", "from_department", "to_department")
            .order_by("-transaction_date", "-id")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Lịch sử giao dịch tài sản"
        return ctx


class AssetCategoryMasterView(LoginRequiredMixin, TemplateView):
    """Module quản lý loại tài sản (Asset Categories).

    Lists all categories for the current company and allows creating new ones
    via POST.  Needed because AssetCreateView requires a category FK — users
    must be able to create categories before they can create assets.
    """

    template_name = "modern/assets/category_master.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = require_current_company(self.request)
        ctx["page_title"] = "Loại tài sản"
        ctx["categories"] = AssetCategory.objects.filter(
            company=company, is_active=True
        ).order_by("code")
        ctx["departments"] = AssetUsingDepartment.objects.filter(
            company=company, is_active=True
        ).order_by("code")
        return ctx

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        form_type = request.POST.get("form_type", "category")

        if form_type == "department":
            return self._handle_department_post(request, company)
        return self._handle_category_post(request, company)

    def _handle_category_post(self, request, company):
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        level = request.POST.get("level", "group").strip()
        is_for_tool = request.POST.get("is_for_tool") == "1"

        if not code or not name:
            messages.error(request, "Vui lòng nhập mã và tên loại tài sản.")
            return redirect("ui_modern:asset_category_master")

        if AssetCategory.objects.filter(company=company, code=code).exists():
            messages.error(request, f"Mã loại tài sản '{code}' đã tồn tại.")
            return redirect("ui_modern:asset_category_master")

        valid_levels = [c[0] for c in AssetCategory.Level.choices]
        if level not in valid_levels:
            level = "group"

        AssetCategory.objects.create(
            company=company,
            code=code,
            name=name,
            level=level,
            is_for_tool=is_for_tool,
            default_gl_account=request.POST.get("default_gl_account", ""),
            default_depreciation_account=request.POST.get("default_depreciation_account", ""),
            default_expense_account=request.POST.get("default_expense_account", ""),
        )
        messages.success(request, f"Đã tạo loại tài sản {code} - {name}")
        return redirect("ui_modern:asset_category_master")

    def _handle_department_post(self, request, company):
        code = request.POST.get("dept_code", "").strip()
        name = request.POST.get("dept_name", "").strip()
        expense_account = request.POST.get("dept_expense_account", "642").strip()

        if not code or not name:
            messages.error(request, "Vui lòng nhập mã và tên bộ phận sử dụng.")
            return redirect("ui_modern:asset_category_master")

        if AssetUsingDepartment.objects.filter(company=company, code=code).exists():
            messages.error(request, f"Mã bộ phận '{code}' đã tồn tại.")
            return redirect("ui_modern:asset_category_master")

        AssetUsingDepartment.objects.create(
            company=company,
            code=code,
            name=name,
            default_expense_account=expense_account,
        )
        messages.success(request, f"Đã tạo bộ phận sử dụng {code} - {name}")
        return redirect("ui_modern:asset_category_master")
