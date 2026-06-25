"""Bank reconciliation service."""

import csv
import io
from datetime import datetime, date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import (
    BankAccount,
    BankStatementImport,
    BankTransaction,
    ReconciliationMatch,
)


class BankImportError(Exception):
    pass


class BankReconciliationService:
    """Parse statement + auto-match transactions to system records."""

    SUPPORTED_FORMATS = ("csv", "xlsx", "xml")

    @classmethod
    def parse_csv(cls, import_session, file_obj):
        """Parse a CSV statement into BankTransaction rows."""
        decoded = file_obj.read().decode("utf-8-sig") if hasattr(file_obj, "read") else file_obj
        reader = csv.DictReader(io.StringIO(decoded))
        required_cols = {"date", "amount", "description"}
        if not required_cols.issubset({c.lower() for c in (reader.fieldnames or [])}):
            raise BankImportError(
                f"CSV missing required columns. Found: {reader.fieldnames}"
            )

        count = 0
        for row in reader:
            try:
                txn_date = cls._parse_date(row.get("date", ""))
                amount = Decimal(str(row.get("amount", "0")).replace(",", ""))
                direction = (
                    BankTransaction.Direction.CREDIT
                    if amount > 0
                    else BankTransaction.Direction.DEBIT
                )
                BankTransaction.objects.create(
                    import_session=import_session,
                    company=import_session.company,
                    bank_account=import_session.bank_account,
                    txn_date=txn_date,
                    value_date=txn_date,
                    direction=direction,
                    amount=abs(amount),
                    description=row.get("description", "")[:500],
                    counterparty_name=row.get("counterparty", "")[:255],
                    reference=row.get("reference", "")[:100],
                )
                count += 1
            except Exception as e:
                # Skip bad row, log
                continue

        import_session.status = BankStatementImport.Status.PARSED
        import_session.save()
        return count

    @classmethod
    def auto_reconcile(cls, company):
        """Try to match each unreconciled transaction to a voucher line (TK 1111/1121) by amount + date."""
        from apps.ledger.models import AccountingVoucher, VoucherLine

        unreconciled = BankTransaction.objects.filter(
            company=company, is_reconciled=False
        )
        voucher_ct = ContentType.objects.get_for_model(AccountingVoucher)
        bank_accounts = ("1121", "1122", "1111", "1112")

        matched_count = 0
        for txn in unreconciled:
            # Match against voucher lines on bank accounts within ±3 days
            from datetime import timedelta

            window_start = txn.txn_date - timedelta(days=3)
            window_end = txn.txn_date + timedelta(days=3)

            # For CREDIT (money in), look for debit on bank account (receipt)
            # For DEBIT (money out), look for credit on bank account (payment)
            lines = VoucherLine.objects.filter(
                voucher__company=company,
                voucher__voucher_date__range=(window_start, window_end),
                account_code__in=bank_accounts,
            )
            if txn.direction == BankTransaction.Direction.CREDIT:
                lines = lines.filter(debit_vnd=txn.amount)
            else:
                lines = lines.filter(credit_vnd=txn.amount)

            for line in lines[:5]:  # consider first 5 candidates
                v = line.voucher
                if ReconciliationMatch.objects.filter(
                    content_type=voucher_ct, object_id=v.id
                ).exists():
                    continue
                ReconciliationMatch.objects.create(
                    transaction=txn,
                    content_type=voucher_ct,
                    object_id=v.id,
                    object_label=f"{v.voucher_no} ({v.description[:30]})",
                    object_amount=txn.amount,
                    match_method=ReconciliationMatch.MatchMethod.AUTO,
                )
                txn.is_reconciled = True
                txn.reconciled_at = timezone.now()
                txn.save()
                matched_count += 1
                break
        return matched_count

    @staticmethod
    def _parse_date(s):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except (ValueError, AttributeError):
                continue
        raise BankImportError(f"Cannot parse date: {s}")
