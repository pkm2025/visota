"""Ledger views — voucher list, form, detail."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.ledger.services.voucher_posting_service import VoucherNotBalancedError
from apps.ui_modern.forms import VoucherHeaderForm, VoucherLineFormSet

from ._export_utils import autosize, new_workbook, style_header, xlsx_response


class VoucherListView(LoginRequiredMixin, ListView):
    """List of accounting vouchers for the current company."""

    template_name = "modern/ledger/voucher_list.html"
    context_object_name = "vouchers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = AccountingVoucher.objects.select_related("company")
        ordering = self.request.GET.get("ordering", "-voucher_date")
        valid_fields = [
            "voucher_date",
            "-voucher_date",
            "voucher_no",
            "-voucher_no",
            "total_vnd",
            "-total_vnd",
            "status",
            "-status",
        ]
        if ordering in valid_fields:
            qs = qs.order_by(ordering, "-id")
        else:
            qs = qs.order_by("-voucher_date", "-id")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(voucher_no__icontains=search) | qs.filter(description__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Phiếu kế toán"
        ctx["status_choices"] = AccountingVoucher.Status.choices
        return ctx


class VoucherCreateView(LoginRequiredMixin, View):
    """Create a new accounting voucher (Standard style — full form)."""

    template_name = "modern/ledger/voucher_form.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm()
        line_formset = VoucherLineFormSet(prefix="lines")
        from apps.core.models import Company
        from apps.master_data.models import ChartOfAccounts

        company = Company.objects.first()
        accounts = []
        if company:
            accounts = list(
                ChartOfAccounts.objects.filter(
                    company=company, is_active=True, is_posting_account=True
                )
                .order_by("account_code")
                .values_list("account_code", "account_name")[:200]
            )
        return render(
            request,
            self.template_name,
            {
                "page_title": "Tạo phiếu kế toán",
                "header_form": header_form,
                "line_formset": line_formset,
                "accounts": accounts,
                "is_new": True,
            },
        )

    def post(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm(request.POST)
        line_formset = VoucherLineFormSet(request.POST, prefix="lines")

        from apps.core.models import Company
        from apps.master_data.models import ChartOfAccounts

        company = Company.objects.first()
        accounts = []
        if company:
            accounts = list(
                ChartOfAccounts.objects.filter(
                    company=company, is_active=True, is_posting_account=True
                )
                .order_by("account_code")
                .values_list("account_code", "account_name")[:200]
            )

        ctx_base = {
            "page_title": "Tạo phiếu kế toán",
            "header_form": header_form,
            "line_formset": line_formset,
            "accounts": accounts,
            "is_new": True,
        }

        if not header_form.is_valid() or not line_formset.is_valid():
            return render(request, self.template_name, ctx_base, status=200)

        # Filter to non-empty lines (skip rows without account_code)
        valid_lines = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for line_form in line_formset:
            cd_line = line_form.cleaned_data
            if cd_line.get("DELETE"):
                continue
            acc = cd_line.get("account_code", "")
            if not acc:
                continue  # skip empty rows
            valid_lines.append(cd_line)
            d = cd_line.get("debit_vnd") or Decimal("0")
            c = cd_line.get("credit_vnd") or Decimal("0")
            total_debit += d
            total_credit += c

        if not valid_lines:
            messages.error(request, "Phải có ít nhất 1 dòng bút toán có tài khoản.")
            return render(request, self.template_name, ctx_base, status=200)

        if abs(total_debit - total_credit) > Decimal("0.01"):
            messages.error(
                request,
                f"Chứng từ không cân đối: Nợ={total_debit} Có={total_credit}",
            )
            ctx_base.update(
                {
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                }
            )
            return render(request, self.template_name, ctx_base, status=200)

        # Get the company — for now use first company (TODO: request.current_company)
        from apps.core.models import Company

        company = Company.objects.first()
        if not company:
            messages.error(request, "No company configured.")
            return redirect("ui_modern:voucher_list")

        cd = header_form.cleaned_data
        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=cd["voucher_date"].year,
            period=cd["voucher_date"].month,
            voucher_no=cd.get("voucher_no") or f"AUTO-{AccountingVoucher.objects.count() + 1:04d}",
            voucher_type=cd["voucher_type"],
            voucher_date=cd["voucher_date"],
            description=cd.get("description", ""),
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=total_debit,
            status=AccountingVoucher.Status.DRAFT,
            created_by=request.user,
        )

        line_no = 1
        for cd_line in valid_lines:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=cd_line["account_code"],
                object_code=cd_line.get("object_code") or "",
                debit_vnd=cd_line.get("debit_vnd") or Decimal("0"),
                credit_vnd=cd_line.get("credit_vnd") or Decimal("0"),
                description=cd_line.get("description") or "",
            )
            line_no += 1

        # Auto-post
        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f"Đã ghi sổ phiếu {voucher.voucher_no}")
        except VoucherNotBalancedError as e:
            messages.error(request, str(e))

        return redirect("ui_modern:voucher_list")


class VoucherDetailView(LoginRequiredMixin, DetailView):
    """Detail view of a single accounting voucher with its lines."""

    template_name = "modern/ledger/voucher_detail.html"
    context_object_name = "voucher"
    login_url = "/auth/login/"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return AccountingVoucher.objects.prefetch_related("lines")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.documents.services.attachment_service import AttachmentService

        ctx["page_title"] = f"Phiếu {self.object.voucher_no}"
        # Related vouchers: same company/fiscal_year/period, exclude self
        related_qs = AccountingVoucher.objects.filter(
            company=self.object.company,
            fiscal_year=self.object.fiscal_year,
            period=self.object.period,
        )
        ctx["related_vouchers"] = related_qs.exclude(id=self.object.id).distinct()[:10]
        ctx["voucher"] = self.object  # for right sidebar
        ctx["attachments"] = AttachmentService.get_for_object(self.object)
        ctx["object_type"] = "ledger.accountingvoucher"
        ctx["object_id"] = self.object.pk
        return ctx


class VoucherExportView(LoginRequiredMixin, View):
    """Export all vouchers (with their lines) to .xlsx."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        wb, ws = new_workbook("Phiếu kế toán")
        headers = [
            "Ngày",
            "Số CT",
            "Loại",
            "Diễn giải",
            "Kỳ",
            "Năm",
            "Tổng tiền (VND)",
            "Trạng thái",
            "#",
            "TK",
            "Đối tượng",
            "Nợ",
            "Có",
            "Diễn giải dòng",
        ]
        ws.append(headers)
        style_header(ws, len(headers))

        status_map = dict(AccountingVoucher.Status.choices)
        qs = (
            AccountingVoucher.objects.select_related("company")
            .prefetch_related("lines")
            .order_by("-voucher_date", "-id")
        )
        # Honor current search filter so users can export a filtered subset.
        search = request.GET.get("search")
        if search:
            qs = qs.filter(voucher_no__icontains=search) | qs.filter(description__icontains=search)
        status = request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        for v in qs:
            ws.append(
                [
                    v.voucher_date.isoformat(),
                    v.voucher_no,
                    v.get_voucher_type_display(),
                    v.description or "",
                    v.period,
                    v.fiscal_year,
                    float(v.total_vnd or 0),
                    status_map.get(v.status, v.status),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            for line in v.lines.all():
                ws.append(
                    [
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        line.line_no,
                        line.account_code,
                        line.object_code or "",
                        float(line.debit_vnd or 0),
                        float(line.credit_vnd or 0),
                        line.description or "",
                    ]
                )
        autosize(ws)
        return xlsx_response(wb, "vouchers.xlsx")


class VoucherDeleteView(LoginRequiredMixin, View):
    """Delete a DRAFT voucher and reverse its ledger entries."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        voucher = get_object_or_404(AccountingVoucher, pk=pk)
        if voucher.status != AccountingVoucher.Status.DRAFT:
            messages.error(
                request,
                f"Không thể xóa phiếu {voucher.voucher_no}: chỉ xóa được phiếu ở trạng thái Lưu tạm.",
            )
            return redirect("ui_modern:voucher_detail", pk=pk)
        try:
            # Reverse any posted ledger entries first (best-effort).
            VoucherPostingService().unpost(voucher)
        except Exception:
            pass
        voucher_no = voucher.voucher_no
        voucher.delete()
        messages.success(request, f"Đã xóa phiếu {voucher_no}")
        return redirect("ui_modern:voucher_list")

    def get(self, request, pk, *args, **kwargs):
        # No GET confirm page — confirm via JS in template; redirect if hit directly.
        return redirect("ui_modern:voucher_detail", pk=pk)
