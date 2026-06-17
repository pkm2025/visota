"""Treasury views — phiếu thu (cash receipt) / phiếu chi (cash payment)."""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService


class _BaseCashView(LoginRequiredMixin, View):
    """Common base — defines voucher type and template, defaults."""

    template_name = "modern/treasury/cash_form.html"
    login_url = "/auth/login/"
    voucher_type = ""  # 'cash_receipt' or 'cash_payment'
    page_title = ""

    def get(self, request, *args, **kwargs):
        ctx = self._base_context()
        return render(request, self.template_name, ctx)

    def _base_context(self, **extra):
        today = date.today()
        ctx = {
            "page_title": self.page_title,
            "voucher_type": self.voucher_type,
            "today": today.isoformat(),
        }
        ctx.update(extra)
        return ctx


class CashReceiptCreateView(_BaseCashView):
    """Phiếu thu — N111 / C{account}."""

    voucher_type = "cash_receipt"
    page_title = "Phiếu thu (01-TT)"

    def post(self, request, *args, **kwargs):
        voucher_no = request.POST.get("voucher_no", "").strip()
        voucher_date_str = request.POST.get("voucher_date", "").strip()
        payer = request.POST.get("payer", "").strip()
        amount_str = request.POST.get("amount", "0").strip()
        reason = request.POST.get("reason", "").strip()
        credit_account = request.POST.get("credit_account", "131").strip() or "131"

        errors = []
        if not payer:
            errors.append("Vui lòng nhập người nộp.")
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                errors.append("Số tiền phải lớn hơn 0.")
        except Exception:
            errors.append("Số tiền không hợp lệ.")
            amount = Decimal("0")
        try:
            voucher_date = date.fromisoformat(voucher_date_str)
        except Exception:
            errors.append("Ngày không hợp lệ (định dạng YYYY-MM-DD).")
            voucher_date = date.today()

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(
                request,
                self.template_name,
                self._base_context(
                    voucher_no=voucher_no,
                    voucher_date=voucher_date_str,
                    payer=payer,
                    amount=amount_str,
                    reason=reason,
                    credit_account=credit_account,
                ),
                status=200,
            )

        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa cấu hình công ty.")
            return redirect("ui_modern:voucher_list")

        if not voucher_no:
            voucher_no = (
                f"PT-{voucher_date.strftime('%Y%m%d')}-{AccountingVoucher.objects.count() + 1:04d}"
            )

        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=voucher_date.year,
            period=voucher_date.month,
            voucher_no=voucher_no,
            voucher_type="cash_receipt",
            voucher_date=voucher_date,
            description=f"Thu tiền từ {payer} — {reason}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=amount,
            status=AccountingVoucher.Status.DRAFT,
            created_by=request.user,
        )
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=1,
            account_code="111",
            debit_vnd=amount,
            credit_vnd=Decimal("0"),
            object_name=payer,
            description=reason,
        )
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=2,
            account_code=credit_account,
            debit_vnd=Decimal("0"),
            credit_vnd=amount,
            object_name=payer,
            description=reason,
        )

        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f"Đã tạo phiếu thu {voucher.voucher_no}")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("ui_modern:voucher_list")


class CashPaymentCreateView(_BaseCashView):
    """Phiếu chi — N{account} / C111."""

    voucher_type = "cash_payment"
    page_title = "Phiếu chi (02-TT)"

    def post(self, request, *args, **kwargs):
        voucher_no = request.POST.get("voucher_no", "").strip()
        voucher_date_str = request.POST.get("voucher_date", "").strip()
        payee = request.POST.get("payee", "").strip()
        amount_str = request.POST.get("amount", "0").strip()
        reason = request.POST.get("reason", "").strip()
        debit_account = request.POST.get("debit_account", "331").strip() or "331"

        errors = []
        if not payee:
            errors.append("Vui lòng nhập người nhận.")
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                errors.append("Số tiền phải lớn hơn 0.")
        except Exception:
            errors.append("Số tiền không hợp lệ.")
            amount = Decimal("0")
        try:
            voucher_date = date.fromisoformat(voucher_date_str)
        except Exception:
            errors.append("Ngày không hợp lệ (định dạng YYYY-MM-DD).")
            voucher_date = date.today()

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(
                request,
                self.template_name,
                self._base_context(
                    voucher_no=voucher_no,
                    voucher_date=voucher_date_str,
                    payee=payee,
                    amount=amount_str,
                    reason=reason,
                    debit_account=debit_account,
                ),
                status=200,
            )

        company = Company.objects.first()
        if not company:
            messages.error(request, "Chưa cấu hình công ty.")
            return redirect("ui_modern:voucher_list")

        if not voucher_no:
            voucher_no = (
                f"PC-{voucher_date.strftime('%Y%m%d')}-{AccountingVoucher.objects.count() + 1:04d}"
            )

        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=voucher_date.year,
            period=voucher_date.month,
            voucher_no=voucher_no,
            voucher_type="cash_payment",
            voucher_date=voucher_date,
            description=f"Chi tiền cho {payee} — {reason}",
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=amount,
            status=AccountingVoucher.Status.DRAFT,
            created_by=request.user,
        )
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=1,
            account_code=debit_account,
            debit_vnd=amount,
            credit_vnd=Decimal("0"),
            object_name=payee,
            description=reason,
        )
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=2,
            account_code="111",
            debit_vnd=Decimal("0"),
            credit_vnd=amount,
            object_name=payee,
            description=reason,
        )

        try:
            VoucherPostingService().post(voucher)
            messages.success(request, f"Đã tạo phiếu chi {voucher.voucher_no}")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("ui_modern:voucher_list")
