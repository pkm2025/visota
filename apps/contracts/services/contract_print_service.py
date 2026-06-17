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
    """Render a Django template *string* (not a file) with the given context."""
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
        return HTML(string=html).write_pdf()

    def _build_context(self, contract: Contract) -> dict:
        """Auto-fill template with contract + company + party data."""
        return {
            "company": contract.company,
            "contract": contract,
            "today": date.today(),
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
