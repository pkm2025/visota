"""HTMX views for TT58 DnsnVoucher CRUD.

Provides list, create, detail, edit, and delete views for DNSN
(DNSN) simplified vouchers. These views are only relevant for
companies with accounting_regime='tt58'.

Unlike the standard AccountingVoucher views, these forms do NOT
contain account_code, debit, or credit fields.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.models import Company
from apps.ledger.models import DnsnVoucher
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


def _get_company(request) -> Company:
    """Get the current company from request or fall back to first."""
    company = getattr(request, "current_company", None)
    if company:
        return company
    return require_current_company(request)


def _parse_decimal(val: str) -> Decimal:
    """Parse a string to Decimal, defaulting to 0 on error."""
    try:
        return Decimal(val)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _parse_date(val: str) -> date | None:
    """Parse ISO date string."""
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


class DnsnVoucherListView(LoginRequiredMixin, ListView):
    """List DNSN vouchers with filtering by type and date range."""

    template_name = "modern/dnsn/voucher_list.html"
    context_object_name = "vouchers"
    paginate_by = 20
    login_url = "/auth/login/"

    def get_queryset(self):
        company = _get_company(self.request)
        qs = DnsnVoucher.objects.filter(company=company)

        voucher_type = self.request.GET.get("voucher_type")
        if voucher_type:
            qs = qs.filter(voucher_type=voucher_type)

        date_from = self.request.GET.get("date_from")
        if date_from:
            d = _parse_date(date_from)
            if d:
                qs = qs.filter(voucher_date__gte=d)

        date_to = self.request.GET.get("date_to")
        if date_to:
            d = _parse_date(date_to)
            if d:
                qs = qs.filter(voucher_date__lte=d)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        search = self.request.GET.get("search")
        if search:
            qs = (
                qs.filter(voucher_no__icontains=search)
                | qs.filter(description__icontains=search)
                | qs.filter(partner_name__icontains=search)
            )

        return qs.order_by("-voucher_date", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Chứng từ DNSN"
        ctx["voucher_type_choices"] = DnsnVoucher.VoucherType.choices
        ctx["status_choices"] = DnsnVoucher.Status.choices
        company = _get_company(self.request)
        ctx["is_tt58"] = company.accounting_regime == "tt58"
        # Preserve filter params for pagination links
        get_params = self.request.GET.copy()
        get_params.pop("page", None)
        ctx["filter_params"] = get_params.urlencode()
        return ctx


class DnsnVoucherCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create a new DNSN voucher (phiếu thu/chi/nhập/xuất etc.).

    The form does NOT contain account_code, debit, or credit fields.
    Only simplified fields: voucher_type, date, amount, partner, description.
    """

    template_name = "modern/dnsn/voucher_form.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def get(self, request, *args, **kwargs):
        company = _get_company(request)
        ctx = {
            "page_title": "Tạo chứng từ DNSN",
            "voucher_type_choices": DnsnVoucher.VoucherType.choices,
            "is_new": True,
            "is_tt58": company.accounting_regime == "tt58",
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        company = _get_company(request)
        voucher_date = _parse_date(request.POST.get("voucher_date", ""))
        if not voucher_date:
            messages.error(request, "Ngày chứng từ không hợp lệ.")
            ctx = {
                "page_title": "Tạo chứng từ DNSN",
                "voucher_type_choices": DnsnVoucher.VoucherType.choices,
                "is_new": True,
                "is_tt58": company.accounting_regime == "tt58",
            }
            return render(request, self.template_name, ctx, status=200)

        voucher_type = request.POST.get("voucher_type", "chung_tu_khac")
        voucher_no = request.POST.get("voucher_no", "").strip()
        if not voucher_no:
            # Auto-generate based on type
            prefix_map = {
                "phieu_thu": "PT",
                "phieu_chi": "PC",
                "phieu_nhap": "PN",
                "phieu_xuat": "PX",
                "hoa_don_ban_hang": "HDB",
                "hoa_don_mua_hang": "HDM",
                "chung_tu_khac": "CT",
            }
            prefix = prefix_map.get(voucher_type, "CT")
            count = DnsnVoucher.objects.filter(
                company=company,
                fiscal_year=voucher_date.year,
                voucher_type=voucher_type,
            ).count()
            voucher_no = f"{prefix}{count + 1:04d}"

        total_amount = _parse_decimal(request.POST.get("total_amount", "0"))

        voucher = DnsnVoucher.objects.create(
            company=company,
            fiscal_year=voucher_date.year,
            period=voucher_date.month,
            voucher_no=voucher_no,
            voucher_type=voucher_type,
            voucher_date=voucher_date,
            posting_date=None,
            description=request.POST.get("description", "").strip(),
            partner_name=request.POST.get("partner_name", "").strip(),
            partner_tax_code=request.POST.get("partner_tax_code", "").strip(),
            partner_address=request.POST.get("partner_address", "").strip(),
            invoice_no=request.POST.get("invoice_no", "").strip(),
            invoice_date=_parse_date(request.POST.get("invoice_date", "")),
            invoice_form=request.POST.get("invoice_form", "").strip(),
            invoice_serial=request.POST.get("invoice_serial", "").strip(),
            total_amount=total_amount,
            status=DnsnVoucher.Status.DRAFT,
        )
        messages.success(request, f"Đã tạo chứng từ {voucher.voucher_no}.")
        return redirect("ui_modern:dnsn_voucher_detail", pk=voucher.pk)


class DnsnVoucherDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a single DNSN voucher."""

    template_name = "modern/dnsn/voucher_detail.html"
    context_object_name = "voucher"
    login_url = "/auth/login/"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        company = _get_company(self.request)
        return DnsnVoucher.objects.filter(company=company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Chứng từ {self.object.voucher_no}"
        company = _get_company(self.request)
        ctx["is_tt58"] = company.accounting_regime == "tt58"
        return ctx


class DnsnVoucherEditView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Edit a DRAFT DNSN voucher.

    Only DRAFT vouchers can be edited. POSTED or LOCKED vouchers
    cannot be edited.
    """

    template_name = "modern/dnsn/voucher_form.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def get_voucher(self, request, pk):
        company = _get_company(request)
        return get_object_or_404(DnsnVoucher, pk=pk, company=company)

    def get(self, request, pk, *args, **kwargs):
        voucher = self.get_voucher(request, pk)
        company = _get_company(request)
        ctx = {
            "page_title": f"Sửa chứng từ {voucher.voucher_no}",
            "voucher": voucher,
            "voucher_type_choices": DnsnVoucher.VoucherType.choices,
            "is_new": False,
            "is_tt58": company.accounting_regime == "tt58",
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        voucher = self.get_voucher(request, pk)

        if voucher.is_posted:
            messages.error(
                request,
                f"Không thể sửa chứng từ {voucher.voucher_no}: "
                "chỉ sửa được chứng từ ở trạng thái Lưu tạm.",
            )
            return redirect("ui_modern:dnsn_voucher_detail", pk=voucher.pk)

        voucher_date = _parse_date(request.POST.get("voucher_date", ""))
        if not voucher_date:
            messages.error(request, "Ngày chứng từ không hợp lệ.")
            return redirect("ui_modern:dnsn_voucher_edit", pk=voucher.pk)

        voucher.voucher_type = request.POST.get("voucher_type", voucher.voucher_type)
        voucher.voucher_date = voucher_date
        voucher.fiscal_year = voucher_date.year
        voucher.period = voucher_date.month
        voucher.description = request.POST.get("description", "").strip()
        voucher.partner_name = request.POST.get("partner_name", "").strip()
        voucher.partner_tax_code = request.POST.get("partner_tax_code", "").strip()
        voucher.partner_address = request.POST.get("partner_address", "").strip()
        voucher.invoice_no = request.POST.get("invoice_no", "").strip()
        invoice_date = _parse_date(request.POST.get("invoice_date", ""))
        voucher.invoice_date = invoice_date
        voucher.invoice_form = request.POST.get("invoice_form", "").strip()
        voucher.invoice_serial = request.POST.get("invoice_serial", "").strip()
        voucher.total_amount = _parse_decimal(request.POST.get("total_amount", "0"))
        voucher.save()

        messages.success(request, f"Đã cập nhật chứng từ {voucher.voucher_no}.")
        return redirect("ui_modern:dnsn_voucher_detail", pk=voucher.pk)


class DnsnVoucherDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Delete a DRAFT DNSN voucher.

    POSTED or LOCKED vouchers cannot be deleted.
    """

    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def post(self, request, pk, *args, **kwargs):
        company = _get_company(request)
        voucher = get_object_or_404(DnsnVoucher, pk=pk, company=company)

        if voucher.is_posted:
            messages.error(
                request,
                f"Không thể xóa chứng từ {voucher.voucher_no}: "
                "chỉ xóa được chứng từ ở trạng thái Lưu tạm.",
            )
            return redirect("ui_modern:dnsn_voucher_detail", pk=voucher.pk)

        voucher_no = voucher.voucher_no
        voucher.delete()
        messages.success(request, f"Đã xóa chứng từ {voucher_no}.")
        return redirect("ui_modern:dnsn_voucher_list")

    def get(self, request, pk, *args, **kwargs):
        return redirect("ui_modern:dnsn_voucher_detail", pk=pk)
