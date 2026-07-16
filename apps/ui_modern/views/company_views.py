"""Company profile edit view — full CRUD with logo/stamp upload."""

import contextlib
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.core.models import Company
from apps.core.module_config import (
    ADVANCED_MODULES,
    CORE_MODULES,
    MODULE_DESCRIPTIONS,
    MODULE_LABELS,
    ModuleVisibilityService,
)
from apps.ui_modern.mixins import require_current_company


class CompanyProfileView(LoginRequiredMixin, View):
    """View + edit company profile with logo, stamp, bank accounts, etc."""

    template_name = "modern/admin/company_profile.html"
    login_url = "/auth/login/"

    def get_company(self, request):
        return require_current_company(request)

    def get(self, request, *args, **kwargs):
        company = self.get_company(request)
        vis_service = ModuleVisibilityService(company)
        ctx = {
            "page_title": f"Hồ sơ công ty: {company.name}",
            "company": company,
            "regime_choices": Company.AccountingRegime.choices,
            "sme_choices": Company.SMESize.choices,
            "vat_method_choices": Company.VatMethod.choices,
            "tndn_method_choices": Company.TndnMethod.choices,
            "entity_type_choices": Company.EntityType.choices,
            "bank_accounts_json": json.dumps(company.bank_accounts or [], ensure_ascii=False),
            "core_modules": [
                {
                    "key": m,
                    "label": MODULE_LABELS.get(m, m),
                    "description": MODULE_DESCRIPTIONS.get(m, ""),
                }
                for m in CORE_MODULES
            ],
            "advanced_modules": [
                {
                    "key": m,
                    "label": MODULE_LABELS.get(m, m),
                    "description": MODULE_DESCRIPTIONS.get(m, ""),
                    "enabled": vis_service.is_module_visible(m),
                }
                for m in ADVANCED_MODULES
            ],
            "is_dnsn": vis_service._is_dnsn,
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
        "industry",
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

    _checkbox_fields = ["hide_visota_branding"]

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
                with contextlib.suppress(ValueError):
                    setattr(company, date_field, date.fromisoformat(val))
            else:
                setattr(company, date_field, None)

        # Select fields (including TT58 tax configuration fields)
        for sel_field in self._select_fields:
            if request.POST.get(sel_field):
                setattr(company, sel_field, request.POST[sel_field])

        # Checkbox fields (unchecked means False)
        for cb_field in self._checkbox_fields:
            setattr(company, cb_field, request.POST.get(cb_field) == "on")

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
                    with contextlib.suppress(Exception):
                        old.delete(save=False)
                setattr(company, file_field, f)

        # Module visibility settings: advanced modules enabled via checkboxes.
        # The POST contains "module_nhan_su", "module_tai_san", etc. for
        # each enabled advanced module.
        vis_service = ModuleVisibilityService(company)
        vis_service.set_enabled_modules(
            [m for m in ADVANCED_MODULES if request.POST.get(f"module_{m}") == "on"]
        )

        company.save()
        messages.success(request, f"Đã cập nhật hồ sơ công ty '{company.name}'.")
        return redirect("ui_modern:company_profile")
