"""Banking UI views."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.models import Company

from .models import BankAccount, BankStatementImport, BankTransaction, ReconciliationMatch
from .services import BankImportError, BankReconciliationService
from .services.vietqr_service import VietQRService


class BankAccountListView(LoginRequiredMixin, ListView):
    template_name = "modern/banking/account_list.html"
    context_object_name = "accounts"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        return BankAccount.objects.filter(company=company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tài khoản ngân hàng"
        return ctx


class BankStatementImportListView(LoginRequiredMixin, ListView):
    template_name = "modern/banking/import_list.html"
    context_object_name = "imports"
    login_url = "/auth/login/"

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        return BankStatementImport.objects.filter(company=company).select_related("bank_account")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Sao kê ngân hàng"
        return ctx


class BankStatementUploadView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        bank_account_id = request.POST.get("bank_account_id")
        period_from = request.POST.get("period_from")
        period_to = request.POST.get("period_to")
        uploaded_file = request.FILES.get("file")

        if not (bank_account_id and period_from and period_to and uploaded_file):
            messages.error(request, "Thiếu thông tin tài khoản / kỳ / file.")
            return redirect("ui_modern:banking_import_list")

        bank_account = get_object_or_404(BankAccount, pk=bank_account_id, company=company)
        from datetime import date as date_cls

        imp = BankStatementImport.objects.create(
            company=company,
            bank_account=bank_account,
            file_name=uploaded_file.name,
            file=uploaded_file,
            period_from=date_cls.fromisoformat(period_from),
            period_to=date_cls.fromisoformat(period_to),
            imported_by=request.user,
        )
        try:
            # Re-read file (already saved via FileField)
            imp.file.open("rb")
            content = imp.file.read().decode("utf-8-sig")
            imp.file.close()
            import csv
            from decimal import Decimal
            from io import StringIO

            reader = csv.DictReader(StringIO(content))
            count = 0
            for row in reader:
                try:
                    txn_date = BankReconciliationService._parse_date(row.get("date", ""))
                    amount = Decimal(str(row.get("amount", "0")).replace(",", ""))
                    direction = "credit" if amount > 0 else "debit"
                    BankTransaction.objects.create(
                        import_session=imp,
                        company=company,
                        bank_account=bank_account,
                        txn_date=txn_date,
                        value_date=txn_date,
                        direction=direction,
                        amount=abs(amount),
                        description=row.get("description", "")[:500],
                        counterparty_name=row.get("counterparty", "")[:255],
                        reference=row.get("reference", "")[:100],
                    )
                    count += 1
                except Exception:
                    continue
            imp.status = "parsed"
            imp.save()
            messages.success(request, f"Đã import {count} giao dịch từ sao kê.")
        except BankImportError as e:
            messages.error(request, f"Lỗi parse: {e}")

        # Try auto-reconcile immediately
        matched = BankReconciliationService.auto_reconcile(company)
        if matched:
            messages.info(request, f"Đã tự động đối soát {matched} giao dịch.")
        return redirect("ui_modern:banking_import_detail", pk=imp.pk)


class BankStatementImportDetailView(LoginRequiredMixin, DetailView):
    template_name = "modern/banking/import_detail.html"
    context_object_name = "import"
    pk_url_kwarg = "pk"
    login_url = "/auth/login/"

    def get_queryset(self):
        return BankStatementImport.objects.select_related("bank_account")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Sao kê {self.object.bank_account.account_number}"
        ctx["transactions"] = self.object.transactions.all().order_by("-txn_date")
        return ctx


class BankReconciliationView(LoginRequiredMixin, TemplateView):
    """Show unreconciled transactions + matches."""

    template_name = "modern/banking/reconcile.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        ctx["page_title"] = "Đối soát ngân hàng"
        ctx["unreconciled"] = BankTransaction.objects.filter(
            company=company, is_reconciled=False
        ).order_by("-txn_date")[:100]
        ctx["recent_matches"] = ReconciliationMatch.objects.select_related("transaction").order_by(
            "-created_at"
        )[:50]
        return ctx


class BankReconciliationRunView(LoginRequiredMixin, View):
    """POST: trigger auto-reconcile."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company = getattr(request, "current_company", None) or Company.objects.first()
        matched = BankReconciliationService.auto_reconcile(company)
        messages.success(request, f"Đã đối soát {matched} giao dịch.")
        return redirect("ui_modern:banking_reconcile")


class VietQRModalView(LoginRequiredMixin, View):
    """AJAX endpoint that returns JSON for the VietQR payment modal.

    GET /modern/banking/vietqr/<invoice_type>/<pk>/?bank=<bank_id>

    invoice_type: 'einvoice' or 'sales'.
    """

    def get(self, request, invoice_type, pk):
        company = getattr(request, "current_company", None) or Company.objects.first()
        if not company:
            return JsonResponse({"error": "No company"}, status=400)

        # Load invoice — resolves (amount, invoice_no, customer_code)
        try:
            amount, invoice_no, customer_code = self._load_invoice(invoice_type, pk, company)
        except Http404:
            return JsonResponse({"error": "Invoice not found"}, status=404)

        # Resolve bank account
        bank_qs = BankAccount.objects.filter(company=company, is_active=True)
        bank_id = request.GET.get("bank")
        if bank_id:
            bank_account = bank_qs.filter(pk=bank_id).first()
        else:
            bank_account = bank_qs.first()
        if not bank_account:
            return JsonResponse(
                {"error": "Công ty chưa có tài khoản ngân hàng"},
                status=404,
            )

        # Build QR
        svc = VietQRService()
        memo = svc.build_memo(invoice_no, customer_code)
        try:
            qr_url = svc.build_url(bank_account, amount, memo)
        except VietQRService.UnsupportedBankError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        # ponytail: VND amounts are whole-number; strip Decimal places for display.
        amount_display = str(int(amount)) if amount == int(amount) else str(amount)

        bank_list = list(bank_qs.values("id", "account_number", "bank_name", "account_holder"))

        return JsonResponse(
            {
                "qr_url": qr_url,
                "account_no": bank_account.account_number,
                "bank_name": bank_account.bank_name,
                "holder": bank_account.account_holder,
                "amount": amount_display,
                "memo": memo,
                "bank_list": bank_list,
                "selected_bank_id": bank_account.id,
            }
        )

    def _load_invoice(self, invoice_type, pk, company):
        if invoice_type == "einvoice":
            from apps.einvoice.models import EInvoice

            ei = EInvoice.objects.filter(pk=pk, company=company).first()
            if not ei:
                raise Http404
            return ei.total_amount, ei.invoice_no or f"PK-{ei.pk}", ""
        if invoice_type == "sales":
            from apps.sales.models import SalesInvoice

            si = SalesInvoice.objects.filter(pk=pk, company=company).first()
            if not si:
                raise Http404
            customer_code = si.customer.code if si.customer_id else ""
            return si.total_amount, si.invoice_no, customer_code
        raise Http404(f"Unknown invoice type: {invoice_type}")
