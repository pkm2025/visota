"""Contract UI views — list, detail, create."""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from apps.contracts.models import Contract
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class ContractListView(LoginRequiredMixin, ListView):
    """List all contracts for the current company."""

    template_name = "modern/contracts/contract_list.html"
    context_object_name = "contracts"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        qs = (
            Contract.objects.filter(company=company)
            .select_related("company")
            .order_by("-contract_date", "-id")
        )
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(contract_no__icontains=search) | qs.filter(party_name__icontains=search)
        contract_type = self.request.GET.get("contract_type")
        if contract_type:
            qs = qs.filter(contract_type=contract_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hợp đồng"
        ctx["contract_type_choices"] = Contract.ContractType.choices
        return ctx


class ContractDetailView(LoginRequiredMixin, DetailView):
    """Detail view of a single contract with related vouchers/minutes."""

    template_name = "modern/contracts/contract_detail.html"
    context_object_name = "contract"
    login_url = "/auth/login/"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        company = require_current_company(self.request)
        return Contract.objects.filter(company=company).select_related("company", "linked_voucher")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.documents.services.attachment_service import AttachmentService

        c = self.object
        ctx["page_title"] = f"Hợp đồng {c.contract_no}"
        ctx["minutes"] = c.minutes_set.all().order_by("-minutes_date")[:20]
        ctx["attachments"] = AttachmentService.get_for_object(c)
        ctx["object_type"] = "contracts.contract"
        ctx["object_id"] = c.pk
        return ctx


class ContractCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create a new contract."""

    template_name = "modern/contracts/contract_form.html"
    login_url = "/auth/login/"
    required_permission = "contracts.access"

    def get(self, request, *args, **kwargs):
        company = require_current_company(request)
        template_code = request.GET.get("template", "")
        selected_template = None
        suggested_type = ""
        if template_code:
            from apps.contracts.models import ContractTemplate

            try:
                selected_template = ContractTemplate.objects.get(
                    code=template_code, company=company
                )
                suggested_type = selected_template.contract_type
            except ContractTemplate.DoesNotExist:
                pass
        ctx = {
            "page_title": "Tạo hợp đồng",
            "contract_type_choices": Contract.ContractType.choices,
            "status_choices": Contract.Status.choices,
            "today": date.today().isoformat(),
            "selected_template": selected_template,
            "suggested_type": suggested_type,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        company = require_current_company(request)
        contract_no = request.POST.get("contract_no", "").strip()
        contract_date_str = request.POST.get("contract_date", "").strip()
        contract_type = request.POST.get("contract_type", Contract.ContractType.OTHER)
        party_code = request.POST.get("party_code", "").strip()
        party_name = request.POST.get("party_name", "").strip()
        party_tax_code = request.POST.get("party_tax_code", "").strip()
        party_address = request.POST.get("party_address", "").strip()
        description = request.POST.get("description", "").strip()
        value_str = request.POST.get("value", "0").strip()
        currency_code = request.POST.get("currency_code", "VND").strip() or "VND"
        start_date_str = request.POST.get("start_date", "").strip()
        end_date_str = request.POST.get("end_date", "").strip()
        status = request.POST.get("status", Contract.Status.DRAFT)

        errors = []
        if not contract_no:
            errors.append("Vui lòng nhập số hợp đồng.")
        if not party_name:
            errors.append("Vui lòng nhập tên đối tác.")
        try:
            value = Decimal(value_str) if value_str else Decimal("0")
        except Exception:
            errors.append("Giá trị không hợp lệ.")
            value = Decimal("0")
        try:
            contract_date = date.fromisoformat(contract_date_str)
        except Exception:
            errors.append("Ngày hợp đồng không hợp lệ.")
            contract_date = date.today()

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except Exception:
                errors.append("Ngày bắt đầu không hợp lệ.")
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except Exception:
                errors.append("Ngày kết thúc không hợp lệ.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(
                request,
                self.template_name,
                {
                    "page_title": "Tạo hợp đồng",
                    "contract_type_choices": Contract.ContractType.choices,
                    "status_choices": Contract.Status.choices,
                    "today": date.today().isoformat(),
                    "form_data": request.POST,
                },
                status=200,
            )

        Contract.objects.create(
            company=company,
            contract_no=contract_no,
            contract_date=contract_date,
            contract_type=contract_type,
            party_code=party_code,
            party_name=party_name,
            party_tax_code=party_tax_code,
            party_address=party_address,
            description=description,
            value=value,
            currency_code=currency_code,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        messages.success(request, f"Đã tạo hợp đồng {contract_no}")
        return redirect("ui_modern:contract_list")
