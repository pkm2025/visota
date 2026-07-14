"""Company profile edit view — full CRUD with logo/stamp upload."""

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.core.models import Company


class CompanyProfileView(LoginRequiredMixin, View):
    """View + edit company profile with logo, stamp, bank accounts, etc."""

    template_name = "modern/admin/company_profile.html"
    login_url = "/auth/login/"

    def get_company(self, request):
        return getattr(request, "current_company", None) or Company.objects.first()

    def get(self, request, *args, **kwargs):
        company = self.get_company(request)
        ctx = {
            "page_title": f"Hồ sơ công ty: {company.name}",
            "company": company,
            "regime_choices": Company.AccountingRegime.choices,
            "sme_choices": Company.SMESize.choices,
            "vat_method_choices": Company.VatMethod.choices,
            "tndn_method_choices": Company.TndnMethod.choices,
            "entity_type_choices": Company.EntityType.choices,
            "bank_accounts_json": json.dumps(company.bank_accounts or [], ensure_ascii=False),
        }
        return render(request, self.template_name, ctx)

    _simple_fields = [
        "name",
        "name_en",
        "short_name",
        "tax_code",
        "address",
        "phone",
        "email",
        "fax",
        "website",
        "legal_representative",
        "representative_position",
        "representative_phone",
        "representative_email",
        "representative_id_no",
        "chief_accountant",
        "chief_accountant_license",
        "chief_accountant_phone",
        "business_license_no",
        "business_license_place",
        "facebook",
        "linkedin",
        "zalo",
        "brand_name",
        "brand_primary_color",
        "brand_accent_color",
    ]

    _select_fields = ["accounting_regime", "sme_size", "vat_method", "tndn_method", "entity_type"]

    _file_fields = ["brand_logo", "brand_logo_dark", "brand_favicon", "company_stamp"]

    def post(self, request, *args, **kwargs):
        company = self.get_company(request)
        for field in self._simple_fields:
            value = request.POST.get(field, "").strip()
            if hasattr(company, field):
                setattr(company, field, value)

        # Date fields
        for date_field in ["business_license_date"]:
            val = request.POST.get(date_field, "").strip()
            if val:
                from datetime import date

                try:
                    setattr(company, date_field, date.fromisoformat(val))
                except ValueError:
                    pass
            else:
                setattr(company, date_field, None)

        # Select fields (including TT58 tax configuration fields)
        for sel_field in self._select_fields:
            if request.POST.get(sel_field):
                setattr(company, sel_field, request.POST[sel_field])

        # Bank accounts JSON
        bank_json = request.POST.get("bank_accounts_json", "[]").strip()
        try:
            company.bank_accounts = json.loads(bank_json)
        except json.JSONDecodeError:
            company.bank_accounts = []

        # File uploads
        for file_field in self._file_fields:
            f = request.FILES.get(file_field)
            if f:
                old = getattr(company, file_field)
                if old:
                    try:
                        old.delete(save=False)
                    except Exception:
                        pass
                setattr(company, file_field, f)

        company.save()
        messages.success(request, f"Đã cập nhật hồ sơ công ty '{company.name}'.")
        return redirect("ui_modern:company_profile")
