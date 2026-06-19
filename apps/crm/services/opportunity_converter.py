"""Convert a won opportunity into Customer + Contract + Project + Invoice."""

from datetime import date

from django.db import transaction

from apps.contracts.models import Contract
from apps.crm.models import Opportunity
from apps.master_data.models import Customer
from apps.projects.models import Project
from apps.sales.services import SalesInvoiceService


class OpportunityConverter:
    """Convert a won opportunity into Customer + Contract + Project + Invoice."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def convert(self, opportunity):
        if opportunity.stage != Opportunity.Stage.WON:
            raise ValueError("Only WON opportunities can be converted")

        results = {}

        customer = self._ensure_customer(opportunity.account)
        results["customer"] = customer

        contract = self._create_contract(opportunity, customer)
        results["contract"] = contract

        project = self._create_project(opportunity, contract)
        results["project"] = project

        invoice = self._create_invoice(opportunity, customer)
        results["invoice"] = invoice

        opportunity.created_contract_id = contract.id
        opportunity.created_project_id = project.id
        opportunity.created_invoice_id = invoice.id if invoice else None
        opportunity.actual_close_date = date.today()
        opportunity.save()

        return results

    def _ensure_customer(self, account):
        """Find existing Customer or create new from CRM Account."""
        if account.customer:
            return account.customer

        if account.tax_code:
            existing = Customer.objects.filter(
                company=self.company, tax_code=account.tax_code
            ).first()
            if existing:
                account.customer = existing
                account.save()
                return existing

        customer = Customer.objects.create(
            company=self.company,
            code=f"CRM{account.code}",
            name=account.name,
            tax_code=account.tax_code,
            address=account.address,
            phone=account.phone,
            email=account.email,
        )
        account.customer = customer
        account.save()
        return customer

    def _create_contract(self, opportunity, customer):
        """Create Contract from Opportunity."""
        return Contract.objects.create(
            company=self.company,
            contract_no=f"HĐ{opportunity.code}",
            contract_date=date.today(),
            contract_type=Contract.ContractType.SERVICE,
            party_code=customer.code,
            party_name=customer.name,
            party_tax_code=customer.tax_code,
            party_address=customer.address,
            description=opportunity.name,
            value=opportunity.estimated_value,
            currency_code=opportunity.currency_code,
            start_date=date.today(),
            status=Contract.Status.ACTIVE,
        )

    def _create_project(self, opportunity, contract):
        """Create Project from Opportunity + Contract."""
        return Project.objects.create(
            company=self.company,
            code=f"PRJ{opportunity.code}",
            name=opportunity.name,
            description=opportunity.description,
            contract=contract,
            customer_code=contract.party_code,
            customer_name=contract.party_name,
            start_date=date.today(),
            budget_revenue=opportunity.estimated_value,
            status=Project.Status.PLANNED,
        )

    def _create_invoice(self, opportunity, customer):
        """Create draft SalesInvoice (NOT posted — accountant reviews first)."""
        lines = list(opportunity.lines.all())
        if not lines:
            return None

        invoice_lines = []
        for line in lines:
            if not line.product_id:
                continue
            invoice_lines.append(
                {
                    "product_id": line.product_id,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "vat_rate": line.vat_rate,
                }
            )

        if not invoice_lines:
            return None

        return SalesInvoiceService(company=self.company).create(
            {
                "invoice_no": f"HĐ{opportunity.code}",
                "invoice_date": date.today(),
                "customer_id": customer.id,
                "lines": invoice_lines,
                "post": False,
            }
        )
