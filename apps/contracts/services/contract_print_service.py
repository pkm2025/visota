"""ContractPrintService — render contract data into a template and produce PDF."""

from datetime import date

from django.template import engines
from django.template.loader import render_to_string  # noqa: F401  (kept for compatibility)

from apps.contracts.models import Contract, ContractTemplate

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


def render_to_string_from_string(template_str, context):
    """Render a Django template *string* (not a file) with the given context.

    Auto-prepends {% load humanize %} so templates can use |intcomma.
    """
    if "{% load humanize" not in template_str:
        template_str = "{% load humanize %}\n" + template_str
    django_engine = engines["django"]
    return django_engine.from_string(template_str).render(context)


class ContractPrintService:
    """Generate contract PDFs from ContractTemplate HTML."""

    def generate_contract_pdf(self, contract: Contract, template_code: str) -> bytes:
        """Render contract data into template, generate PDF via WeasyPrint."""
        template = ContractTemplate.objects.get(code=template_code)
        context = self._build_context(contract)
        html = render_to_string_from_string(template.template_html, context)
        if not WEASYPRINT_AVAILABLE:
            return html.encode("utf-8")

        # Build base_url for resolving image URLs in PDF
        from django.conf import settings
        base_url = getattr(settings, "BASE_URL", "http://127.0.0.1:8903")
        return HTML(string=html, base_url=base_url).write_pdf()

    def _build_context(self, contract: Contract) -> dict:
        """Auto-fill template with contract + company + party data."""
        company = contract.company
        return {
            "company": company,
            "contract": contract,
            "today": date.today(),
            "company_logo_url": company.brand_logo.url if company.brand_logo else "",
            "company_stamp_url": company.company_stamp.url if company.company_stamp else "",
            "company_bank_accounts": company.bank_accounts or [],
            "company_representative": company.legal_representative,
            "company_rep_position": company.representative_position,
            "company_chief_accountant": company.chief_accountant,
            "party_name": contract.party_name,
            "party_tax_code": contract.party_tax_code,
            "party_address": contract.party_address,
            "contract_no": contract.contract_no,
            "contract_date": contract.contract_date,
            "value": contract.value,
            "currency_code": contract.currency_code,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
        }
