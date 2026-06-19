"""AssetLifecycleService: dispose / transfer assets with GL posting."""

from datetime import date
from decimal import Decimal

from django.db import transaction as db_transaction

from apps.assets.models import AssetTransaction, FixedAsset
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.ledger.services import VoucherPostingService


class AssetLifecycleService:
    @db_transaction.atomic
    def dispose(self, asset: FixedAsset, disposal_value=Decimal("0"), reason=""):
        """Dispose/liquidate an asset. Creates disposal transaction + GL voucher."""
        company = asset.company

        # Create transaction record
        txn = AssetTransaction.objects.create(
            company=company,
            transaction_no=f"TL-{asset.asset_code}-{date.today().strftime('%Y%m%d')}",
            transaction_date=date.today(),
            transaction_type=AssetTransaction.TransactionType.DISPOSAL,
            asset=asset,
            disposal_value=disposal_value,
            disposal_reason=reason,
        )

        # Create GL voucher
        voucher = AccountingVoucher.objects.create(
            company=company,
            fiscal_year=date.today().year,
            period=date.today().month,
            voucher_no=txn.transaction_no,
            voucher_type=AccountingVoucher.VoucherType.JOURNAL,
            voucher_date=date.today(),
            status=AccountingVoucher.Status.DRAFT,
            description=f"Thanh lý TSCĐ {asset.asset_code} - {asset.asset_name}",
        )

        line_no = 1
        # N214 (accumulated depreciation)
        if asset.accumulated_depreciation and asset.accumulated_depreciation > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=asset.depreciation_account,
                debit_vnd=asset.accumulated_depreciation,
                description=f"Hao mòn lũy kế {asset.asset_code}",
            )
            line_no += 1

        # N811 (loss) or C711 (gain) — net book value vs disposal value
        nbv = asset.original_cost - asset.accumulated_depreciation
        if disposal_value < nbv:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="811",
                debit_vnd=nbv - disposal_value,
                description=f"Lỗ thanh lý {asset.asset_code}",
            )
            line_no += 1
        elif disposal_value > nbv:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="711",
                credit_vnd=disposal_value - nbv,
                description=f"Lãi thanh lý {asset.asset_code}",
            )
            line_no += 1

        # C211 (original cost credit)
        VoucherLine.objects.create(
            voucher=voucher,
            line_no=line_no,
            account_code=asset.gl_account,
            credit_vnd=asset.original_cost,
            description=f"Giảm nguyên giá {asset.asset_code}",
        )
        line_no += 1

        # If disposal value received — debit cash/bank 111
        if disposal_value and disposal_value > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code="111",
                debit_vnd=disposal_value,
                description=f"Thu tiền thanh lý {asset.asset_code}",
            )

        # Post voucher
        VoucherPostingService().post(voucher)
        txn.gl_voucher = voucher
        txn.save()

        # Update asset status
        asset.status = FixedAsset.Status.DISPOSED
        asset.save(update_fields=["status", "updated_at"])

        return txn

    @db_transaction.atomic
    def transfer(self, asset: FixedAsset, to_department, new_expense_account=None):
        """Transfer asset to another department."""
        old_dept = asset.using_department

        txn = AssetTransaction.objects.create(
            company=asset.company,
            transaction_no=f"DC-{asset.asset_code}-{date.today().strftime('%Y%m%d')}",
            transaction_date=date.today(),
            transaction_type=AssetTransaction.TransactionType.TRANSFER,
            asset=asset,
            from_department=old_dept,
            to_department=to_department,
            description=f"Điều chuyển {asset.asset_code} từ {old_dept} đến {to_department}",
        )

        update_fields = ["using_department", "updated_at"]
        asset.using_department = to_department
        if new_expense_account:
            asset.expense_account = new_expense_account
            update_fields.append("expense_account")
        asset.save(update_fields=update_fields)

        return txn
