"""Ledger views — voucher list, form, detail."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.ledger.services.voucher_posting_service import VoucherNotBalancedError
from apps.ui_modern.forms import VoucherHeaderForm, VoucherLineFormSet


class VoucherListView(LoginRequiredMixin, ListView):
    """List of accounting vouchers for the current company."""

    template_name = "modern/ledger/voucher_list.html"
    context_object_name = "vouchers"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = AccountingVoucher.objects.select_related("company").order_by("-voucher_date", "-id")
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
        return render(
            request,
            self.template_name,
            {
                "page_title": "Tạo phiếu kế toán",
                "header_form": header_form,
                "line_formset": line_formset,
                "is_new": True,
            },
        )

    def post(self, request, *args, **kwargs):
        header_form = VoucherHeaderForm(request.POST)
        line_formset = VoucherLineFormSet(request.POST, prefix="lines")

        ctx_base = {
            "page_title": "Tạo phiếu kế toán",
            "header_form": header_form,
            "line_formset": line_formset,
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
        ctx["page_title"] = f"Phiếu {self.object.voucher_no}"
        # Related vouchers: same company/fiscal_year/period, exclude self
        related_qs = AccountingVoucher.objects.filter(
            company=self.object.company,
            fiscal_year=self.object.fiscal_year,
            period=self.object.period,
        )
        ctx["related_vouchers"] = related_qs.exclude(id=self.object.id).distinct()[:10]
        ctx["voucher"] = self.object  # for right sidebar
        return ctx
