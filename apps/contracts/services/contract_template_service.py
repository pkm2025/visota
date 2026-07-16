"""ContractTemplateService — CRUD/lookup helpers for ContractTemplate."""

from ..models import ContractTemplate


class ContractTemplateService:
    """Lookup, activate, and manage contract templates.

    VAL-SEC-004: ContractTemplate is now company-scoped. Callers must
    pass ``company`` (or use ``code`` together with ``company``) so the
    lookup does not cross tenant boundaries.
    """

    @staticmethod
    def list_active(company, contract_type=None):
        qs = ContractTemplate.objects.filter(company=company, is_active=True)
        if contract_type:
            qs = qs.filter(contract_type=contract_type)
        return qs.order_by("code")

    @staticmethod
    def get(company, code):
        return ContractTemplate.objects.get(company=company, code=code)
