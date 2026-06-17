"""ContractTemplateService — CRUD/lookup helpers for ContractTemplate."""

from ..models import ContractTemplate


class ContractTemplateService:
    """Lookup, activate, and manage contract templates."""

    @staticmethod
    def list_active(contract_type=None):
        qs = ContractTemplate.objects.filter(is_active=True)
        if contract_type:
            qs = qs.filter(contract_type=contract_type)
        return qs.order_by("code")

    @staticmethod
    def get(code):
        return ContractTemplate.objects.get(code=code)
