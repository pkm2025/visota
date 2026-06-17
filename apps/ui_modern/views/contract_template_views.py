"""Contract template UI views — list templates + generate PDF."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services.contract_print_service import ContractPrintService


class ContractTemplateListView(LoginRequiredMixin, ListView):
    """List available contract templates."""

    template_name = "modern/contracts/contract_template_list.html"
    context_object_name = "templates"
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = ContractTemplate.objects.filter(is_active=True).order_by("code")
        contract_type = self.request.GET.get("contract_type")
        if contract_type:
            qs = qs.filter(contract_type=contract_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contracts_available"] = Contract.objects.all()[:20]
        ctx["page_title"] = "Mẫu hợp đồng"
        ctx["contract_type_choices"] = [
            ("labor_fixed", "HĐLĐ xác định thời hạn"),
            ("labor_indefinite", "HĐLĐ không xác định thời hạn"),
            ("labor_probation", "HĐ thử việc"),
            ("sale", "HĐ mua bán"),
            ("purchase", "HĐ mua hàng"),
            ("service", "HĐ dịch vụ"),
            ("construction", "HĐ thi công"),
            ("appendix", "Phụ lục"),
        ]
        return ctx


class ContractGenerateView(LoginRequiredMixin, View):
    """Select template + contract → generate PDF."""

    login_url = "/auth/login/"

    def get(self, request, template_code, contract_id):
        template = get_object_or_404(ContractTemplate, code=template_code)
        contract = get_object_or_404(Contract, id=contract_id)
        service = ContractPrintService()
        pdf_bytes = service.generate_contract_pdf(contract, template_code)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"{contract.contract_no}_{template.code}.pdf"
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class ContractTemplatePreviewView(LoginRequiredMixin, View):
    """Render template HTML preview (browser) before generating PDF."""

    template_name = "modern/contracts/contract_template_preview.html"
    login_url = "/auth/login/"

    def get(self, request, template_code, contract_id):
        template = get_object_or_404(ContractTemplate, code=template_code)
        contract = get_object_or_404(Contract, id=contract_id)
        service = ContractPrintService()
        ctx = service._build_context(contract)
        from django.template import engines

        rendered = engines["django"].from_string(template.template_html).render(ctx)
        return render(
            request,
            self.template_name,
            {
                "page_title": f"Xem trước — {template.name}",
                "template": template,
                "contract": contract,
                "rendered_html": rendered,
            },
        )
