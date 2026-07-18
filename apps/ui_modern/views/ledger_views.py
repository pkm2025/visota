"""Ledger views — voucher list, form, detail, guided mode."""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.ledger.services.voucher_posting_service import VoucherNotBalancedError
from apps.ui_modern.forms import (
    VoucherHeaderForm,
    VoucherLineFormSet,
    VoucherTaxLineFormSet,
)
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company

from ._export_utils import autosize, new_workbook, style_header, xlsx_response


class VoucherListView(LoginRequiredMixin, ListView):
    """List of accounting vouchers for the current company."""

    template_name = "modern/ledger/voucher_list.html"
    context_object_name = "vouchers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        qs = AccountingVoucher.objects.filter(company=company).select_related("company")
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


class VoucherCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create a new accounting voucher (Standard style — full form)."""

    template_name = "modern/ledger/voucher_form.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def _company_accounts(self):
        from apps.master_data.models import ChartOfAccounts

        company = require_current_company(self.request)
        accounts = list(
            ChartOfAccounts.objects.filter(company=company, is_active=True, is_posting_account=True)
            .order_by("account_code")
            .values_list("account_code", "account_name")[:200]
        )
        return company, accounts

    def get(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm()
        line_formset = VoucherLineFormSet(prefix="lines")
        tax_formset = VoucherTaxLineFormSet(prefix="taxes")
        _, accounts = self._company_accounts()
        return render(
            request,
            self.template_name,
            {
                "page_title": "Tạo phiếu kế toán",
                "header_form": header_form,
                "line_formset": line_formset,
                "tax_formset": tax_formset,
                "accounts": accounts,
                "is_new": True,
            },
        )

    def post(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm(request.POST)
        line_formset = VoucherLineFormSet(request.POST, prefix="lines")
        # Tax formset is optional — gracefully handle missing management form data.
        if "taxes-TOTAL_FORMS" in request.POST:
            tax_formset = VoucherTaxLineFormSet(request.POST, prefix="taxes")
            tax_formset_valid = tax_formset.is_valid()
        else:
            tax_formset = VoucherTaxLineFormSet(prefix="taxes")
            tax_formset_valid = True  # unbound = no tax data submitted

        company, accounts = self._company_accounts()

        ctx_base = {
            "page_title": "Tạo phiếu kế toán",
            "header_form": header_form,
            "line_formset": line_formset,
            "tax_formset": tax_formset,
            "accounts": accounts,
            "is_new": True,
        }

        if not header_form.is_valid() or not line_formset.is_valid() or not tax_formset_valid:
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

        # Save tax lines (under "Thuế" tab)
        if tax_formset_valid and tax_formset.is_bound:
            line_no = self._save_tax_lines(voucher, tax_formset, line_no)

        # Auto-post
        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f"Đã ghi sổ phiếu {voucher.voucher_no}")
        except VoucherNotBalancedError as e:
            messages.error(request, str(e))

        return redirect("ui_modern:voucher_list")

    def _save_tax_lines(self, voucher, tax_formset, line_no):
        """Persist non-empty tax lines from the tax formset. Returns next line_no."""
        for tax_form in tax_formset:
            cd_tax = tax_form.cleaned_data
            if cd_tax.get("DELETE"):
                continue
            invoice_no = cd_tax.get("invoice_no", "")
            if not invoice_no and not cd_tax.get("goods_amount_vnd"):
                continue  # skip empty rows
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=cd_tax.get("offset_account_code") or "",
                invoice_no=invoice_no,
                invoice_date=cd_tax.get("invoice_date"),
                invoice_form=cd_tax.get("invoice_form") or "",
                invoice_symbol=cd_tax.get("invoice_symbol") or "",
                invoice_serial=cd_tax.get("invoice_serial") or "",
                tax_code=cd_tax.get("tax_code"),
                tax_rate=cd_tax.get("tax_rate") or Decimal("0"),
                goods_amount_vnd=cd_tax.get("goods_amount_vnd") or Decimal("0"),
                tax_amount_vnd=cd_tax.get("tax_amount_vnd") or Decimal("0"),
                offset_account_code=cd_tax.get("offset_account_code") or "",
                invoice_group_code=cd_tax.get("invoice_group_code"),
                object_address=cd_tax.get("object_address") or "",
                description=f"Tax line — {invoice_no}" if invoice_no else "Tax line",
            )
            line_no += 1
        return line_no


class VoucherDetailView(LoginRequiredMixin, DetailView):
    """Detail view of a single accounting voucher with its lines."""

    template_name = "modern/ledger/voucher_detail.html"
    context_object_name = "voucher"
    login_url = "/auth/login/"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        company = require_current_company(self.request)
        return AccountingVoucher.objects.filter(company=company).prefetch_related("lines")

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
        company = require_current_company(request)
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
            AccountingVoucher.objects.filter(company=company)
            .select_related("company")
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


class VoucherDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Delete a voucher and reverse its ledger entries.

    Supports both DRAFT and POSTED vouchers. For POSTED vouchers we first
    unpost (reverse ledger entries) then delete. Any unpost failure is
    surfaced to the user instead of being silently swallowed — this was
    the root cause of feedback #4 (POST returned 302 but the voucher
    remained because unpost() raised and was caught with bare except).
    """

    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def post(self, request, pk, *args, **kwargs):
        company = require_current_company(request)
        voucher = get_object_or_404(AccountingVoucher, pk=pk, company=company)
        if voucher.status == AccountingVoucher.Status.LOCKED:
            messages.error(
                request,
                f"Không thể xóa phiếu {voucher.voucher_no}: phiếu đã khóa.",
            )
            return redirect("ui_modern:voucher_detail", pk=pk)
        if voucher.status != AccountingVoucher.Status.DRAFT:
            # Posted (SUBSIDIARY / LEDGER): unpost first, surface failures.
            try:
                VoucherPostingService().unpost(voucher)
            except Exception as exc:  # noqa: BLE001 — surface, don't crash
                import logging

                logging.getLogger("apps.ui_modern").exception(
                    "unpost failed for voucher %s: %s", voucher.voucher_no, exc
                )
                messages.error(
                    request,
                    f"Không thể bỏ ghi sổ phiếu {voucher.voucher_no}. "
                    f"Vui lòng kiểm tra kỳ kế toán hoặc liên hệ quản trị viên.",
                )
                return redirect("ui_modern:voucher_detail", pk=pk)
        voucher_no = voucher.voucher_no
        voucher.delete()
        messages.success(request, f"Đã xóa phiếu {voucher_no}")
        return redirect("ui_modern:voucher_list")

    def get(self, request, pk, *args, **kwargs):
        # No GET confirm page — confirm via JS in template; redirect if hit directly.
        return redirect("ui_modern:voucher_detail", pk=pk)


class VoucherGuidedView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Guided voucher creation — pick action → auto-generate lines."""

    template_name = "modern/ledger/voucher_guided.html"
    login_url = "/auth/login/"
    required_permission = "ledger.access"

    def get(self, request, *args, **kwargs):
        ctx = {"page_title": "Tạo phiếu nhanh"}
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)

        action = request.POST.get("action_type", "")
        amount_str = request.POST.get("amount", "0").strip()
        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Số tiền không hợp lệ.")
            return redirect("ui_modern:voucher_guided")

        if amount < 1000:
            messages.error(request, "Số tiền tối thiểu 1.000đ.")
            return redirect("ui_modern:voucher_guided")

        pm = request.POST.get("payment_method", "111")
        cp = request.POST.get("counterparty", "").strip()
        desc = request.POST.get("description", "").strip()
        today = date.today()

        # Build voucher based on action
        vtype = AccountingVoucher.VoucherType.JOURNAL
        lines_to_create = []

        if action == "collect":
            vtype = AccountingVoucher.VoucherType.CASH_RECEIPT
            lines_to_create = [
                (pm, amount, Decimal("0"), f"Thu tiền{' — ' + cp if cp else ''}"),
                ("131", Decimal("0"), amount, f"Khách hàng{': ' + cp if cp else ''} thanh toán"),
            ]
        elif action == "pay_vendor":
            vtype = AccountingVoucher.VoucherType.CASH_PAYMENT
            lines_to_create = [
                ("331", amount, Decimal("0"), f"Thanh toán NCC{': ' + cp if cp else ''}"),
                (pm, Decimal("0"), amount, f"Chi tiền{' — ' + cp if cp else ''}"),
            ]
        elif action == "pay_expense":
            vtype = AccountingVoucher.VoucherType.CASH_PAYMENT
            exp_acc = request.POST.get("expense_type", "642")
            has_vat = request.POST.get("has_vat") == "on"
            if has_vat:
                net = (amount / Decimal("1.1")).quantize(Decimal("0.0001"))
                vat = amount - net
                lines_to_create = [
                    (exp_acc, net, Decimal("0"), desc or "Chi phí"),
                    ("1331", vat, Decimal("0"), f"VAT 10% — {desc}" if desc else "VAT 10%"),
                    (pm, Decimal("0"), amount, desc or "Chi tiền"),
                ]
            else:
                lines_to_create = [
                    (exp_acc, amount, Decimal("0"), desc or "Chi phí"),
                    (pm, Decimal("0"), amount, desc or "Chi tiền"),
                ]
        else:
            messages.error(request, "Vui lòng chọn loại nghiệp vụ.")
            return redirect("ui_modern:voucher_guided")

        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=today.year,
            period=today.month,
            voucher_no=f"GUIDE-{today.strftime('%y%m%d')}-{AccountingVoucher.objects.filter(company=company, voucher_no__startswith='GUIDE').count() + 1:04d}",
            voucher_type=vtype,
            voucher_date=today,
            description=desc or f"[Tạo nhanh] {action}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=amount,
            status=AccountingVoucher.Status.DRAFT,
            created_by=request.user,
        )

        for idx, (acc, dr, cr, line_desc) in enumerate(lines_to_create, 1):
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=idx,
                account_code=acc,
                object_code=cp if action in ("collect", "pay_vendor") else "",
                debit_vnd=dr,
                credit_vnd=cr,
                description=line_desc,
            )

        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f"Đã tạo và ghi sổ phiếu {voucher.voucher_no}.")
        except Exception as e:
            messages.warning(request, f"Phiếu đã tạo: {voucher.voucher_no}. Ghi sổ: {e}")
        return redirect("ui_modern:voucher_detail", pk=voucher.pk)
