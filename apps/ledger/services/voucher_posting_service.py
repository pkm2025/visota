"""VoucherPostingService: post/unpost voucher → updates AccountPeriodBalance."""
from decimal import Decimal
from django.db import transaction
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance


class VoucherNotBalancedError(Exception):
    """Raised when voucher debit total != credit total."""

    def __init__(self, total_debit, total_credit):
        self.total_debit = total_debit
        self.total_credit = total_credit
        super().__init__(
            f'Voucher not balanced: debit={total_debit} credit={total_credit} '
            f'diff={total_debit - total_credit}'
        )


class VoucherLockedError(Exception):
    """Raised when attempting to modify a locked voucher."""


class VoucherPostingService:
    """Service for posting/unposting vouchers and updating balance projections."""

    BALANCE_TOLERANCE = Decimal('0.01')  # 1 VND rounding tolerance

    @transaction.atomic
    def post(self, voucher: AccountingVoucher) -> None:
        """Post a voucher: validate + update AccountPeriodBalance + set status=LEDGER."""
        if voucher.is_locked:
            raise VoucherLockedError(f'Voucher {voucher.voucher_no} is locked')

        self._validate_balanced(voucher)
        self._update_balances(voucher, sign=+1)

        voucher.status = AccountingVoucher.Status.LEDGER
        voucher.save(update_fields=['status', 'total_vnd', 'total_fc', 'updated_at'])

    @transaction.atomic
    def unpost(self, voucher: AccountingVoucher) -> None:
        """Unpost a voucher: revert balance updates + set status=DRAFT."""
        if voucher.is_locked:
            raise VoucherLockedError(f'Voucher {voucher.voucher_no} is locked')

        if not voucher.is_posted:
            return  # idempotent — already unposted

        self._update_balances(voucher, sign=-1)

        voucher.status = AccountingVoucher.Status.DRAFT
        voucher.save(update_fields=['status', 'updated_at'])

    def _validate_balanced(self, voucher: AccountingVoucher) -> None:
        """Verify total debit == total credit."""
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        for line in voucher.lines.all():
            total_debit += line.debit_vnd or Decimal('0')
            total_credit += line.credit_vnd or Decimal('0')

        if abs(total_debit - total_credit) > self.BALANCE_TOLERANCE:
            raise VoucherNotBalancedError(total_debit, total_credit)

        # Also update voucher totals
        voucher.total_vnd = total_debit
        voucher.total_fc = sum((l.debit_fc or 0 for l in voucher.lines.all()), Decimal('0'))

    def _update_balances(self, voucher: AccountingVoucher, sign: int) -> None:
        """Update AccountPeriodBalance for each line. sign=+1 for post, -1 for unpost."""
        for line in voucher.lines.all():
            self._update_one_balance(voucher, line, sign)

    def _update_one_balance(self, voucher: AccountingVoucher, line, sign: int) -> None:
        """Update or create the balance row for one line."""
        balance, _ = AccountPeriodBalance.objects.get_or_create(
            company=voucher.company,
            fiscal_year=voucher.fiscal_year,
            period=voucher.period,
            account_code=line.account_code,
            object_type=line.object_type or '',
            object_code=line.object_code or '',
            defaults={
                'opening_debit': Decimal('0'),
                'opening_credit': Decimal('0'),
            },
        )

        # Apply delta (sign controls direction)
        balance.period_debit += sign * (line.debit_vnd or Decimal('0'))
        balance.period_credit += sign * (line.credit_vnd or Decimal('0'))
        balance.period_debit_fc += sign * (line.debit_fc or Decimal('0'))
        balance.period_credit_fc += sign * (line.credit_fc or Decimal('0'))

        # Recalculate closing
        balance.recalculate_closing()

        # Track last txn
        if sign > 0:
            if not balance.last_transaction_date or voucher.voucher_date > balance.last_transaction_date:
                balance.last_transaction_date = voucher.voucher_date
            balance.transaction_count = (balance.transaction_count or 0) + 1
        else:
            balance.transaction_count = max(0, (balance.transaction_count or 0) - 1)

        balance.save()
