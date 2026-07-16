"""DnsnPostingService: post/unpost DNSN vouchers without double-entry validation.

Unlike VoucherPostingService which enforces debit == credit balance,
this service creates direct ledger entries with revenue/cost/tax/cash
amounts. No balance validation is performed.
"""

from decimal import Decimal

from django.db import transaction

from apps.ledger.models import AccountingVoucher
from apps.ledger.models.dnsn import (
    DnsnLedgerBalance,
    DnsnLedgerEntry,
    DnsnVoucher,
)


class DnsnVoucherLockedError(Exception):
    """Raised when attempting to modify a locked DNSN voucher."""


class DnsnPeriodClosedError(Exception):
    """Raised when attempting to post a DNSN voucher to a closed period."""


class DnsnPostingService:
    """Service for posting/unposting DNSN vouchers.

    Key difference from VoucherPostingService: no debit=credit validation.
    Entries are single-sided direct amounts (revenue, cost, tax, cash).
    """

    @transaction.atomic
    def post(self, voucher: DnsnVoucher, entries: list[dict]) -> None:
        """Post a DNSN voucher: create ledger entries and update balances.

        Args:
            voucher: The DnsnVoucher to post.
            entries: List of dicts with keys matching DnsnLedgerEntry fields
                     (ledger_type, description, revenue_amount, cost_amount,
                      vat_amount, tndn_amount, cash_in, cash_out, bank_in,
                      bank_out, etc.)

        Raises:
            DnsnVoucherLockedError: If voucher status is 'locked'.
            DnsnPeriodClosedError: If the voucher's period has been closed.
        """
        if voucher.is_locked:
            raise DnsnVoucherLockedError(f"Voucher {voucher.voucher_no} is locked")

        if voucher.is_posted:
            return  # idempotent — already posted

        self._check_period_open(voucher)

        # Create ledger entries
        total_amount = Decimal("0")
        for idx, entry_data in enumerate(entries, start=1):
            entry = self._create_entry(voucher, idx, entry_data)
            total_amount += self._entry_total(entry)

        voucher.total_amount = total_amount
        voucher.posting_date = voucher.voucher_date
        voucher.status = DnsnVoucher.Status.POSTED
        voucher.save(
            update_fields=[
                "total_amount",
                "posting_date",
                "status",
                "updated_at",
            ]
        )

        # Update balances for each affected ledger_type
        affected_types = {e["ledger_type"] for e in entries}
        for ledger_type in affected_types:
            self._recalculate_balance(voucher, ledger_type)

        # Recompute running balances for affected ledger types
        for ledger_type in affected_types:
            self._recompute_running_balances(voucher.company, ledger_type)

    @transaction.atomic
    def unpost(self, voucher: DnsnVoucher) -> None:
        """Unpost a DNSN voucher: remove entries and reverse balances.

        Args:
            voucher: The DnsnVoucher to unpost.

        Raises:
            DnsnVoucherLockedError: If voucher status is 'locked'.
        """
        if voucher.is_locked:
            raise DnsnVoucherLockedError(f"Voucher {voucher.voucher_no} is locked")

        if not voucher.is_posted:
            return  # idempotent — already draft

        # Get affected ledger types before deleting entries
        affected_types = list(
            DnsnLedgerEntry.objects.filter(voucher=voucher)
            .values_list("ledger_type", flat=True)
            .distinct()
        )

        # Delete entries
        DnsnLedgerEntry.objects.filter(voucher=voucher).delete()

        # Recalculate balances from remaining entries (across all vouchers)
        for ledger_type in affected_types:
            self._recalculate_balance(voucher, ledger_type)
            self._recompute_running_balances(voucher.company, ledger_type)

        voucher.status = DnsnVoucher.Status.DRAFT
        voucher.save(update_fields=["status", "updated_at"])

    def _check_period_open(self, voucher: DnsnVoucher) -> None:
        """Raise DnsnPeriodClosedError if the voucher's period has been closed.

        A period is considered closed if a closing voucher (source='closing')
        exists for the same (company, fiscal_year, period) in AccountingVoucher.
        """
        period_closed = AccountingVoucher.objects.filter(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            source="closing",
        ).exists()
        if period_closed:
            raise DnsnPeriodClosedError(
                f"Period {voucher.period}/{voucher.fiscal_year} is closed for company "
                f"{voucher.company_id}"
            )

    def _create_entry(self, voucher: DnsnVoucher, line_no: int, data: dict) -> DnsnLedgerEntry:
        """Create a single DnsnLedgerEntry from a data dict."""
        # Extract known fields, defaulting to 0/blank
        defaults = {
            "voucher": voucher,
            "company": voucher.company,
            "fiscal_year": voucher.fiscal_year,
            "period": voucher.period,
            "line_no": line_no,
            "entry_date": voucher.voucher_date,
            "ledger_type": data["ledger_type"],
            "description": data.get("description", ""),
            "partner_name": data.get("partner_name", voucher.partner_name),
            "revenue_amount": Decimal(str(data.get("revenue_amount", 0))),
            "cost_amount": Decimal(str(data.get("cost_amount", 0))),
            "vat_amount": Decimal(str(data.get("vat_amount", 0))),
            "tndn_amount": Decimal(str(data.get("tndn_amount", 0))),
            "cash_in": Decimal(str(data.get("cash_in", 0))),
            "cash_out": Decimal(str(data.get("cash_out", 0))),
            "bank_in": Decimal(str(data.get("bank_in", 0))),
            "bank_out": Decimal(str(data.get("bank_out", 0))),
            "vat_input": Decimal(str(data.get("vat_input", 0))),
            "vat_output": Decimal(str(data.get("vat_output", 0))),
            "vat_payable": Decimal(str(data.get("vat_payable", 0))),
            "item_code": data.get("item_code", ""),
            "item_name": data.get("item_name", ""),
            "quantity": Decimal(str(data.get("quantity", 0))),
            "unit_price": Decimal(str(data.get("unit_price", 0))),
            "total_amount": Decimal(str(data.get("total_amount", 0))),
        }
        return DnsnLedgerEntry.objects.create(**defaults)

    def _entry_total(self, entry: DnsnLedgerEntry) -> Decimal:
        """Compute the signed total amount for an entry (for voucher total).

        Inflows (cash_in, bank_in) increase the total; outflows (cash_out,
        bank_out) DECREASE it. This fixes VAL-DNSN-001 where outflows were
        incorrectly added to the running balance.

        To avoid double-counting (eval B-07), ``total_amount`` is only added
        when the entry has no revenue/cost/cash component populated. This
        covers S2c inventory entries that store value in ``total_amount``.
        """
        component = (
            entry.revenue_amount
            + entry.cost_amount
            + entry.cash_in
            - entry.cash_out
            + entry.bank_in
            - entry.bank_out
        )
        if component == Decimal("0") and entry.total_amount != Decimal("0"):
            # Pure inventory/amount-only entry (e.g. S2c): use total_amount.
            return entry.total_amount
        return component

    def _recalculate_balance(self, voucher: DnsnVoucher, ledger_type: str) -> None:
        """Recalculate DnsnLedgerBalance from all entries for a ledger type.

        Sums period amounts from all DnsnLedgerEntry rows for the
        given (company, fiscal_year, period, ledger_type).
        """
        entries = DnsnLedgerEntry.objects.filter(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            ledger_type=ledger_type,
        )

        balance, _ = DnsnLedgerBalance.objects.select_for_update().get_or_create(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            ledger_type=ledger_type,
        )

        # Reset period accumulators
        balance.period_revenue = Decimal("0")
        balance.period_cost = Decimal("0")
        balance.period_vat = Decimal("0")
        balance.period_cash = Decimal("0")

        last_date = None
        count = 0
        for entry in entries:
            # S2c (inventory) tracks value via total_amount exclusively —
            # do NOT also add revenue_amount (eval B-08 double-count fix).
            if ledger_type == "s2c":
                balance.period_revenue += entry.total_amount
            else:
                balance.period_revenue += entry.revenue_amount
            balance.period_cost += entry.cost_amount
            # VAT: distinguish input (credit) vs output (debit/payable).
            # Net VAT payable = vat_output - vat_input + vat_amount + vat_payable.
            if ledger_type == "s3b":
                balance.period_vat += (
                    entry.vat_output - entry.vat_input + entry.vat_amount + entry.vat_payable
                )
            else:
                balance.period_vat += (
                    entry.vat_amount + entry.vat_input + entry.vat_output + entry.vat_payable
                )
            balance.period_cash += entry.cash_in - entry.cash_out + entry.bank_in - entry.bank_out
            if entry.entry_date and (last_date is None or entry.entry_date > last_date):
                last_date = entry.entry_date
            count += 1

        balance.last_transaction_date = last_date
        balance.transaction_count = count
        balance.recalculate_closing()
        balance.save()

    @staticmethod
    def _recompute_running_balances(company, ledger_type: str) -> None:
        """Recompute running_balance for all entries in a ledger type.

        Orders entries by (entry_date, id) and computes cumulative
        amount based on the ledger type's primary amount field.
        """
        entries = list(
            DnsnLedgerEntry.objects.filter(
                company=company,
                ledger_type=ledger_type,
            )
            .order_by("entry_date", "id", "line_no")
            .only(
                "id",
                "entry_date",
                "revenue_amount",
                "cost_amount",
                "cash_in",
                "cash_out",
                "bank_in",
                "bank_out",
                "vat_amount",
                "vat_input",
                "vat_output",
                "vat_payable",
                "total_amount",
            )
        )

        cumulative = Decimal("0")
        for entry in entries:
            cumulative += DnsnPostingService._entry_net_amount(entry)
            entry.running_balance = cumulative
            entry.save(update_fields=["running_balance"])

    @staticmethod
    def _entry_net_amount(entry: DnsnLedgerEntry) -> Decimal:
        """Compute the net amount for running balance purposes.

        Uses the primary amount field for each ledger type:
        - Revenue ledgers (S1, S2a, S2b, S3a): revenue_amount
        - Cash ledger (S2d): cash_in - cash_out + bank_in - bank_out
        - VAT ledger (S3b): vat_output - vat_input
        - Inventory ledger (S2c): total_amount
        - Others: revenue_amount (default)
        """
        lt = entry.ledger_type
        if lt in ("s2d",):
            return entry.cash_in - entry.cash_out + entry.bank_in - entry.bank_out
        if lt in ("s3b",):
            return entry.vat_output - entry.vat_input
        if lt in ("s2c",):
            return entry.total_amount
        if lt in ("s2b",):
            return entry.revenue_amount - entry.cost_amount
        # Default: revenue ledgers
        return entry.revenue_amount
