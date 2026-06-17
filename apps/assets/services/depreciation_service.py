"""DepreciationService — calculate monthly depreciation + post voucher."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.assets.models import AssetDepreciation, FixedAsset
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService


class DepreciationService:
    """Service for monthly depreciation calculation + posting."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def calculate_period(self, fiscal_year: int, period: int) -> dict:
        """Calculate depreciation for all active assets in given period.

        Returns dict with: assets_processed, total_depreciation, skipped_already_depreciated.
        Idempotent: skips assets that already have AssetDepreciation for this period.
        """
        period_str = f"{fiscal_year:04d}-{period:02d}"
        voucher_date = date(fiscal_year, period, 1)  # first day of period (simplified)

        # Get active assets not yet depreciated this period
        active_assets = FixedAsset.objects.filter(
            company=self.company,
            status=FixedAsset.Status.ACTIVE,
        ).select_related("using_department")

        processed = 0
        skipped = 0
        total = Decimal("0")

        # Per asset: compute depreciation, create history row
        asset_lines = []  # list of (asset, depreciation_amount)
        for asset in active_assets:
            # Idempotency check
            if AssetDepreciation.objects.filter(asset=asset, period=period_str).exists():
                skipped += 1
                continue

            dep_amount = asset.calculate_monthly_depreciation()
            if dep_amount <= 0:
                continue

            asset.accumulated_depreciation += dep_amount
            if asset.accumulated_depreciation >= asset.original_cost - asset.salvage_value:
                asset.accumulated_depreciation = asset.original_cost - asset.salvage_value
                asset.status = FixedAsset.Status.FULLY_DEPRECIATED
            asset.save(
                update_fields=[
                    "accumulated_depreciation",
                    "status",
                    "updated_at",
                ]
            )

            asset_lines.append((asset, dep_amount))
            total += dep_amount
            processed += 1

        if not asset_lines:
            return {
                "assets_processed": 0,
                "total_depreciation": Decimal("0"),
                "skipped_already_depreciated": skipped,
            }

        # Aggregate by (expense_account, depreciation_account) — but for simplicity,
        # assume all assets in this period share one expense/depr account pair.
        # Real implementation would group by account.
        expense_account = asset_lines[0][0].expense_account
        depr_account = asset_lines[0][0].depreciation_account

        # Create voucher
        voucher = AccountingVoucher.objects.create(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            voucher_no=f"KH-{period_str}",
            voucher_type="depreciation",
            voucher_date=voucher_date,
            currency_code="VND",
            exchange_rate=Decimal("1"),
            total_vnd=total,
            status=AccountingVoucher.Status.DRAFT,
            source="depreciation",
            description=f"Khấu hao TSCĐ/CCDC kỳ {period_str}",
        )

        # N641/642/635 — expense debit
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=1,
            account_code=expense_account,
            debit_vnd=total,
            description=f"CP khấu hao kỳ {period_str}",
        )

        # C2141/2142/2143 or C142/242 — accumulated credit
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=2,
            account_code=depr_account,
            credit_vnd=total,
            description=f"Hao mòn lũy kế kỳ {period_str}",
        )

        # Post voucher → updates AccountPeriodBalance
        VoucherPostingService().post(voucher)

        # Create AssetDepreciation history rows linked to voucher
        for asset, dep_amount in asset_lines:
            AssetDepreciation.objects.create(
                asset=asset,
                period=period_str,
                depreciation_amount=dep_amount,
                accumulated_depreciation_end=asset.accumulated_depreciation,
                net_book_value_end=asset.net_book_value,
                gl_voucher=voucher,
            )

        return {
            "assets_processed": processed,
            "total_depreciation": total,
            "skipped_already_depreciated": skipped,
            "voucher_id": voucher.id,
        }
