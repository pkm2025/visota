"""Bidding services — convert WON bid to Contract automatically."""

from datetime import date

from apps.contracts.models import Contract

from .models import BidResult


class BidConverterService:
    """When a bid is WON, create a Contract automatically."""

    @staticmethod
    def mark_won(bid_opportunity, *, final_value=None, awarded_at=None, contractor_profile=None):
        """Mark a bid as won + create Contract + (optionally) CRMAccount link."""
        result, _ = BidResult.objects.update_or_create(
            bid=bid_opportunity,
            defaults={
                "company": bid_opportunity.company,
                "outcome": BidResult.Outcome.WON,
                "awarded_at": awarded_at or date.today(),
                "final_contract_value": final_value or bid_opportunity.bid_package_price,
                "winner_name": contractor_profile.name
                if contractor_profile
                else bid_opportunity.company.name,
            },
        )
        bid_opportunity.status = "won"
        bid_opportunity.save()
        return result

    @classmethod
    def convert_to_contract(cls, bid_opportunity, **contract_overrides):
        """Convert a WON bid to a Contract. Returns the contract."""
        if bid_opportunity.status != "won":
            cls.mark_won(bid_opportunity)

        company = bid_opportunity.company
        today = date.today()

        defaults = {
            "company": company,
            "contract_date": today,
            "contract_type": Contract.ContractType.CONSTRUCTION
            if "construction" in (bid_opportunity.bid_type or "")
            else Contract.ContractType.SERVICE,
            "party_code": bid_opportunity.investor_tax_code or "INVESTOR",
            "party_name": bid_opportunity.investor_name,
            "party_tax_code": bid_opportunity.investor_tax_code,
            "description": f"Hợp đồng từ gói thầu {bid_opportunity.bid_no}: {bid_opportunity.bid_name}",
            "value": bid_opportunity.bid_package_price,
            "currency_code": bid_opportunity.currency_code,
            "start_date": today,
            "status": Contract.Status.ACTIVE,
        }
        defaults.update(contract_overrides)

        contract_no = contract_overrides.pop("contract_no", f"HĐ-{bid_opportunity.bid_no}")
        contract, created = Contract.objects.get_or_create(
            contract_no=contract_no,
            defaults=defaults,
        )

        # Link to bid result
        result = bid_opportunity.result
        result.contract = contract
        result.save()

        # Notification to project/accounting team
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_to_superusers(
                company=company,
                type="success",
                title=f"Trúng thầu → Hợp đồng {contract.contract_no}",
                message=(
                    f"Gói thầu {bid_opportunity.bid_no} ({bid_opportunity.bid_name[:40]}) "
                    f"đã trúng với giá trị {contract.value:,.0f} VND. "
                    f"Đã tạo hợp đồng {contract.contract_no}."
                ),
                url=f"/modern/contracts/{contract.id}/",
                related_object_type="contracts.contract",
                related_object_id=contract.id,
            )
        except Exception:
            pass

        return contract
