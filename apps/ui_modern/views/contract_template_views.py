"""Contract template UI views — list, create, edit, delete, generate, preview."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.services.contract_print_service import ContractPrintService


class ContractTemplateListView(LoginRequiredMixin, ListView):
    template_name = "modern/contracts/contract_template_list.html"
    context_object_name = "templates"
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = ContractTemplate.objects.all().order_by("code")
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Mẫu văn bản"
        ctx["contracts_available"] = Contract.objects.all().order_by("-contract_date")[:20]
        return ctx


class ContractTemplateCreateView(LoginRequiredMixin, View):
    """Create new template from scratch or duplicate existing."""

    template_name = "modern/contracts/contract_template_form.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        ctx = {
            "page_title": "Tạo mẫu văn bản",
            "is_new": True,
            "form_data": {
                "code": "",
                "name": "",
                "contract_type": "service",
                "template_html": DEFAULT_TEMPLATE_HTML,
                "required_fields": '["company", "party_name", "value"]',
                "legal_basis": "",
                "version": "2026",
                "is_active": True,
            },
        }
        # Pre-fill if duplicating
        dup_id = request.GET.get("duplicate")
        if dup_id:
            src = get_object_or_404(ContractTemplate, pk=dup_id)
            ctx["form_data"] = {
                "code": src.code + "_copy",
                "name": src.name + " (bản sao)",
                "contract_type": src.contract_type,
                "template_html": src.template_html,
                "required_fields": str(src.required_fields),
                "legal_basis": src.legal_basis,
                "version": src.version,
                "is_active": src.is_active,
            }
            ctx["page_title"] = f"Nhân bản từ: {src.name}"
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        if not code or not name:
            messages.error(request, "Vui lòng nhập mã và tên mẫu.")
            return render(
                request,
                self.template_name,
                {
                    "page_title": "Tạo mẫu văn bản",
                    "is_new": True,
                    "form_data": request.POST,
                },
            )
        if ContractTemplate.objects.filter(code=code).exists():
            messages.error(request, f"Mã '{code}' đã tồn tại.")
            return render(
                request,
                self.template_name,
                {
                    "page_title": "Tạo mẫu văn bản",
                    "is_new": True,
                    "form_data": request.POST,
                },
            )
        import json

        try:
            fields = json.loads(request.POST.get("required_fields", "[]"))
        except json.JSONDecodeError:
            fields = []
        tpl = ContractTemplate.objects.create(
            code=code,
            name=name,
            contract_type=request.POST.get("contract_type", "service"),
            template_html=request.POST.get("template_html", ""),
            required_fields=fields,
            legal_basis=request.POST.get("legal_basis", ""),
            version=request.POST.get("version", "2026"),
            is_active=request.POST.get("is_active") == "on",
        )
        messages.success(request, f"Đã tạo mẫu '{name}'.")
        return redirect("ui_modern:contract_template_list")


class ContractTemplateEditView(LoginRequiredMixin, View):
    """Edit existing template — full inline editor with preview."""

    template_name = "modern/contracts/contract_template_form.html"
    login_url = "/auth/login/"

    def get(self, request, pk, *args, **kwargs):
        tpl = get_object_or_404(ContractTemplate, pk=pk)
        ctx = {
            "page_title": f"Sửa mẫu: {tpl.name}",
            "is_new": False,
            "template": tpl,
            "form_data": {
                "code": tpl.code,
                "name": tpl.name,
                "contract_type": tpl.contract_type,
                "template_html": tpl.template_html,
                "required_fields": str(tpl.required_fields),
                "legal_basis": tpl.legal_basis,
                "version": tpl.version,
                "is_active": tpl.is_active,
            },
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        tpl = get_object_or_404(ContractTemplate, pk=pk)
        tpl.name = request.POST.get("name", tpl.name)
        tpl.contract_type = request.POST.get("contract_type", tpl.contract_type)
        tpl.template_html = request.POST.get("template_html", tpl.template_html)
        import json

        try:
            tpl.required_fields = json.loads(request.POST.get("required_fields", "[]"))
        except json.JSONDecodeError:
            pass
        tpl.legal_basis = request.POST.get("legal_basis", "")
        tpl.version = request.POST.get("version", tpl.version)
        tpl.is_active = request.POST.get("is_active") == "on"
        tpl.save()
        messages.success(request, f"Đã cập nhật mẫu '{tpl.name}'.")
        return redirect("ui_modern:contract_template_list")


class ContractTemplateDeleteView(LoginRequiredMixin, View):
    """Delete template (system templates protected)."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        tpl = get_object_or_404(ContractTemplate, pk=pk)
        name = tpl.name
        tpl.delete()
        messages.success(request, f"Đã xóa mẫu '{name}'.")
        return redirect("ui_modern:contract_template_list")


class ContractTemplatePreviewRawView(LoginRequiredMixin, View):
    """AJAX: render template HTML from POST body → return HTML for iframe preview."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        html = request.POST.get("template_html", "")
        contract_id = request.POST.get("contract_id")
        ctx = {}
        if contract_id:
            try:
                contract = Contract.objects.get(pk=contract_id)
                service = ContractPrintService()
                ctx = service._build_context(contract)
            except Contract.DoesNotExist:
                pass
        else:
            # Use placeholder data for preview
            ctx = {
                "company": type(
                    "C",
                    (),
                    {
                        "name": "CÔNG TY ABC",
                        "tax_code": "0101234567",
                        "address": "123 Đường ABC, Hà Nội",
                    },
                )(),
                "contract": type(
                    "D",
                    (),
                    {
                        "contract_no": "HĐ-DEMO-001",
                        "contract_date": "25/06/2026",
                        "party_name": "Công ty Đối tác XYZ",
                        "party_tax_code": "0109876543",
                        "party_address": "456 Lê Lợi, TP.HCM",
                        "value": "500000000",
                        "start_date": "01/07/2026",
                        "end_date": "30/06/2027",
                        "description": "Hợp đồng dịch vụ",
                    },
                )(),
            }
        from django.template import engines

        try:
            if "{% load humanize" not in html:
                html = "{% load humanize %}\n" + html
            rendered = engines["django"].from_string(html).render(ctx)
            return HttpResponse(rendered)
        except Exception as e:
            return HttpResponse(f'<div class="alert alert-danger">Lỗi template: {e}</div>')


class ContractGenerateView(LoginRequiredMixin, View):
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


DEFAULT_TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<title>Mẫu văn bản</title>
<style>
@page { size: A4; margin: 2.5cm; }
body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; }
.header { text-align: center; margin-bottom: 20px; }
.title { text-align: center; font-weight: bold; font-size: 14pt; text-transform: uppercase; margin: 20px 0; }
.signatures { margin-top: 50px; width: 100%; }
.signatures td { text-align: center; width: 50%; vertical-align: top; }
</style></head>
<body>
<div class="header">
  <strong>{{ company.name }}</strong><br>
  MST: {{ company.tax_code }} — Địa chỉ: {{ company.address|default:"" }}
</div>
<div class="title">{{ contract.contract_no }}</div>
<p>Kính gửi: <strong>{{ contract.party_name }}</strong></p>
<p>MST: {{ contract.party_tax_code }}</p>
<p>Giá trị: <strong>{{ contract.value|floatformat:0 }} đồng</strong></p>
<p>Ngày hợp đồng: {{ contract.contract_date }}</p>
<p>{% if contract.description %}{{ contract.description }}{% endif %}</p>
<table class="signatures">
<tr><td><strong>ĐẠI DIỆN BÊN A</strong><br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
    <td><strong>ĐẠI DIỆN BÊN B</strong><br><br><br>(Ký, ghi rõ họ tên, đóng dấu)</td>
</tr>
</table>
</body></html>"""


# ============================================================================
# Contract Wizard — guided template selection
# ============================================================================

WIZARD_CATEGORIES = [
    {
        "key": "labor",
        "label": "Hợp đồng với nhân viên",
        "icon": "bi-person-badge",
        "desc": "HĐLĐ, thử việc, quyết định...",
        "types": ["labor_fixed", "labor_indefinite", "labor_probation", "labor_dispatch", "labor"],
    },
    {
        "key": "commercial",
        "label": "Hợp đồng với khách hàng / NCC",
        "icon": "bi-briefcase",
        "desc": "Mua bán, dịch vụ, gia công, đại lý...",
        "types": ["sale", "service", "it_service", "processing", "agency", "lease", "purchase"],
    },
    {
        "key": "construction",
        "label": "Hợp đồng thi công / đấu thầu",
        "icon": "bi-building",
        "desc": "Thi công, đấu thầu, tư vấn...",
        "types": ["construction", "bidding_lump_sum", "bidding_unit_price", "bidding_consulting"],
    },
    {
        "key": "minutes",
        "label": "Biên bản",
        "icon": "bi-file-earmark-text",
        "desc": "Nghiệm thu, bàn giao, thanh lý, đối chiếu...",
        "types": ["other"],
        "code_prefix": "bb_",
    },
    {
        "key": "decision",
        "label": "Quyết định",
        "icon": "bi-award",
        "desc": "Nâng lương, điều chuyển, chấm dứt HĐLĐ...",
        "types": ["labor"],
        "code_prefix": "qd_",
    },
    {
        "key": "other",
        "label": "Khác / Phụ lục",
        "icon": "bi-three-dots",
        "desc": "Phụ lục hợp đồng và mẫu khác",
        "types": ["appendix"],
    },
]


class ContractWizardView(LoginRequiredMixin, View):
    """Guided wizard: pick category → pick template → create contract."""

    template_name = "modern/contracts/wizard.html"
    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        category = request.GET.get("cat", "")
        selected_templates = []
        active_category = None

        if category:
            for cat in WIZARD_CATEGORIES:
                if cat["key"] == category:
                    active_category = cat
                    qs = ContractTemplate.objects.filter(
                        contract_type__in=cat["types"], is_active=True
                    ).order_by("name")
                    if cat.get("code_prefix"):
                        # Filter by code_prefix (for minutes bb_ and decisions qd_)
                        prefix = cat["code_prefix"]
                        if cat["key"] == "minutes" or cat["key"] == "decision":
                            qs = ContractTemplate.objects.filter(
                                code__startswith=prefix, is_active=True
                            ).order_by("name")
                    selected_templates = list(qs)
                    break

        return render(
            request,
            self.template_name,
            {
                "page_title": "Tạo hợp đồng nhanh",
                "categories": WIZARD_CATEGORIES,
                "active_category": active_category,
                "selected_templates": selected_templates,
            },
        )
