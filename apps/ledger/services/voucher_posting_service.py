"""VoucherPostingService: post/unpost voucher → updates AccountPeriodBalance."""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine


class VoucherNotBalancedError(Exception):
    """Raised when voucher debit total != credit total."""

    def __init__(self, total_debit, total_credit):
        self.total_debit = total_debit
        self.total_credit = total_credit
        super().__init__(
            f"Voucher not balanced: debit={total_debit} credit={total_credit} "
            f"diff={total_debit - total_credit}"
        )


class VoucherLockedError(Exception):
    """Raised when attempting to modify a locked voucher."""


class PeriodClosedError(Exception):
    """Raised when attempting to post to a closed period."""


class VoucherPostingService:
    """Service for posting/unposting vouchers and updating balance projections."""

    BALANCE_TOLERANCE = Decimal("0.01")  # 1 VND rounding tolerance

    @transaction.atomic
    def post(self, voucher: AccountingVoucher) -> None:
        """Post a voucher: validate + update AccountPeriodBalance + set status=LEDGER."""
        if voucher.is_locked:
            raise VoucherLockedError(f"Voucher {voucher.voucher_no} is locked")

        if voucher.is_posted:
            return  # idempotent — already posted

        self._check_period_open(voucher)
        self._validate_balanced(voucher)
        self._update_balances(voucher, sign=+1)

        voucher.status = AccountingVoucher.Status.LEDGER
        voucher.save(update_fields=["status", "total_vnd", "total_fc", "updated_at"])

        # Recompute running balances for affected account codes
        self._recompute_running_balances(voucher)

        # Log business event (non-blocking)
        try:
            from apps.pkm.services.interaction_service import log_interaction

            log_interaction(
                user=None,
                company=voucher.company,
                interaction_type="voucher_create",
                module="ledger",
                entity_type="voucher",
                entity_id=voucher.voucher_no,
                metadata={"amount": str(voucher.total_vnd)},
            )
        except Exception:
            pass  # interaction logging must never block posting

        # Fire-and-forget notification to all superusers (KTT alerts)
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send_to_superusers(
                company=voucher.company,
                title=f"Phiếu kế toán đã ghi sổ: {voucher.voucher_no}",
                message=(
                    f"Phiếu {voucher.voucher_no} ({voucher.get_voucher_type_display()}) "
                    f"đã được ghi sổ với giá trị {voucher.total_vnd:,.0f} VND."
                ),
                type="success",
                url=f"/modern/vouchers/{voucher.id}/",
                related_object_type="ledger.accountingvoucher",
                related_object_id=voucher.id,
            )
        except Exception:
            pass  # notification failure should never block posting

    @transaction.atomic
    def unpost(self, voucher: AccountingVoucher) -> None:
        """Unpost a voucher: revert balance updates + set status=DRAFT."""
        if voucher.is_locked:
            raise VoucherLockedError(f"Voucher {voucher.voucher_no} is locked")

        if not voucher.is_posted:
            return  # idempotent — already unposted

        self._update_balances(voucher, sign=-1)

        voucher.status = AccountingVoucher.Status.DRAFT
        voucher.save(update_fields=["status", "updated_at"])

        # Clear running balance on the unposted voucher's own lines, then
        # recompute for all other lines sharing the affected account codes.
        affected_codes = list(voucher.lines.values_list("account_code", flat=True).distinct())
        voucher.lines.update(
            running_balance_debit=Decimal("0"),
            running_balance_credit=Decimal("0"),
        )
        self._recompute_running_balances_for_codes(voucher.company, affected_codes)

    def _check_period_open(self, voucher: AccountingVoucher) -> None:
        """Raise PeriodClosedError if the voucher's period has been closed.

        A period is considered closed if a *previously committed* closing
        voucher (source='closing') exists for the same
        (company, fiscal_year, period). The voucher being posted is excluded
        so that PeriodClosingService can post the closing voucher itself.
        """
        period_closed = (
            AccountingVoucher.objects.filter(
                company=voucher.company,
                fiscal_year=voucher.fiscal_year,
                period=voucher.period,
                source="closing",
            )
            .exclude(pk=voucher.pk)
            .exists()
        )
        if period_closed:
            raise PeriodClosedError(
                f"Period {voucher.period}/{voucher.fiscal_year} is closed for company "
                f"{voucher.company_id}"
            )

    def _validate_balanced(self, voucher: AccountingVoucher) -> None:
        """Verify total debit == total credit on user-entered lines."""
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for line in voucher.lines.all():
            total_debit += line.debit_vnd or Decimal("0")
            total_credit += line.credit_vnd or Decimal("0")

        if abs(total_debit - total_credit) > self.BALANCE_TOLERANCE:
            raise VoucherNotBalancedError(total_debit, total_credit)

        # Also update voucher totals
        voucher.total_vnd = total_debit
        voucher.total_fc = sum(
            (line.debit_fc or 0 for line in voucher.lines.all()),
            Decimal("0"),
        )

    def _update_balances(self, voucher: AccountingVoucher, sign: int) -> None:
        """Update AccountPeriodBalance for each line. sign=+1 for post, -1 for unpost."""
        for line in voucher.lines.all():
            self._update_one_balance(voucher, line, sign)

    def _update_one_balance(self, voucher: AccountingVoucher, line, sign: int) -> None:
        """Update or create the balance row for one line."""
        balance, _ = AccountPeriodBalance.objects.select_for_update().get_or_create(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            account_code=line.account_code,
            object_type=line.object_type or "",
            object_code=line.object_code or "",
            defaults={
                "opening_debit": Decimal("0"),
                "opening_credit": Decimal("0"),
            },
        )

        # Apply delta (sign controls direction)
        balance.period_debit += sign * (line.debit_vnd or Decimal("0"))
        balance.period_credit += sign * (line.credit_vnd or Decimal("0"))
        balance.period_debit_fc += sign * (line.debit_fc or Decimal("0"))
        balance.period_credit_fc += sign * (line.credit_fc or Decimal("0"))

        # Recalculate closing
        balance.recalculate_closing()

        # Track last txn
        if sign > 0:
            if (
                not balance.last_transaction_date
                or voucher.voucher_date > balance.last_transaction_date
            ):
                balance.last_transaction_date = voucher.voucher_date
            balance.transaction_count = (balance.transaction_count or 0) + 1
        else:
            balance.transaction_count = max(0, (balance.transaction_count or 0) - 1)

        balance.save()

    def _recompute_running_balances(self, voucher: AccountingVoucher) -> None:
        """Recompute running balances for all account codes touched by this voucher."""
        affected_codes = list(voucher.lines.values_list("account_code", flat=True).distinct())
        self._recompute_running_balances_for_codes(voucher.company, affected_codes)

    @staticmethod
    def _recompute_running_balances_for_codes(company: object, account_codes: list[str]) -> None:
        """Recompute cumulative debit/credit running balances for given account codes.

        For each account_code, all posted VoucherLine rows (across all fiscal years
        and periods of the same company) are ordered by (voucher_date, voucher_id,
        line_no) and a cumulative debit and cumulative credit total is stored on
        each line's running_balance_debit / running_balance_credit fields.
        """
        if not account_codes:
            return

        # Only lines belonging to posted vouchers participate in the running balance.
        lines = (
            VoucherLine.objects.select_related("voucher")
            .filter(
                voucher__company=company,
                voucher__status__gte=AccountingVoucher.Status.LEDGER,
                account_code__in=account_codes,
            )
            .order_by("account_code", "voucher__voucher_date", "voucher__id", "line_no")
            .only(
                "id",
                "account_code",
                "debit_vnd",
                "credit_vnd",
                "voucher__voucher_date",
                "voucher__id",
            )
        )

        cumulative_debit: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        cumulative_credit: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        updates: list[tuple[int, Decimal, Decimal]] = []
        for line in lines:
            code = line.account_code
            cumulative_debit[code] += line.debit_vnd or Decimal("0")
            cumulative_credit[code] += line.credit_vnd or Decimal("0")
            updates.append((line.pk, cumulative_debit[code], cumulative_credit[code]))

        # Bulk-update each line. We use individual save() calls in a single
        # transaction (already wrapped) since each line has a distinct value.
        for pk, rbd, rbc in updates:
            VoucherLine.objects.filter(pk=pk).update(
                running_balance_debit=rbd,
                running_balance_credit=rbc,
            )
