"""VoucherPostingService: post/unpost voucher → updates AccountPeriodBalance."""

from decimal import Decimal

from django.db import models, transaction

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


class VoucherPostingService:
    """Service for posting/unposting vouchers and updating balance projections."""

    BALANCE_TOLERANCE = Decimal("0.01")  # 1 VND rounding tolerance

    @transaction.atomic
    def post(self, voucher: AccountingVoucher) -> None:
        """Post a voucher: validate + update AccountPeriodBalance + set status=LEDGER."""
        if voucher.is_locked:
            raise VoucherLockedError(f"Voucher {voucher.voucher_no} is locked")

        self._validate_balanced(voucher)
        self._generate_tax_postings(voucher)
        self._update_balances(voucher, sign=+1)

        voucher.status = AccountingVoucher.Status.LEDGER
        voucher.save(update_fields=["status", "total_vnd", "total_fc", "updated_at"])

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
        self._remove_tax_postings(voucher)

        voucher.status = AccountingVoucher.Status.DRAFT
        voucher.save(update_fields=["status", "updated_at"])

    def _validate_balanced(self, voucher: AccountingVoucher) -> None:
        """Verify total debit == total credit on user-entered lines (excludes auto-tax)."""
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for line in voucher.lines.filter(is_auto_tax_posting=False):
            total_debit += line.debit_vnd or Decimal("0")
            total_credit += line.credit_vnd or Decimal("0")

        if abs(total_debit - total_credit) > self.BALANCE_TOLERANCE:
            raise VoucherNotBalancedError(total_debit, total_credit)

        # Also update voucher totals
        voucher.total_vnd = total_debit
        voucher.total_fc = sum(
            (line.debit_fc or 0 for line in voucher.lines.filter(is_auto_tax_posting=False)),
            Decimal("0"),
        )

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

    # ── Tax posting helpers (M1) ────────────────────────────────────────
    # Constants for auto-generated tax ledger lines.
    INPUT_TAX_ACCOUNT = "1331"  # Thuế GTGT đầu vào được khấu trừ
    OUTPUT_TAX_ACCOUNT = "33311"  # Thuế GTGT đầu ra phải nộp
    INPUT_GROUP_CODE = "4"  # InvoiceGroup code for INPUT invoices
    OUTPUT_GROUP_CODE = "5"  # InvoiceGroup code for OUTPUT invoices

    def _generate_tax_postings(self, voucher: AccountingVoucher) -> None:
        """Create auto VoucherLine rows for TK 1331 (input) / 33311 (output).

        For each user-entered line that has invoice_group_code set and a
        non-zero tax_amount_vnd, generate a single-sided ledger line:

        - invoice_group #4 (INPUT): debit TK 1331 for tax_amount_vnd
        - invoice_group #5 (OUTPUT): credit TK 33311 for tax_amount_vnd

        Idempotent: re-running post() after a previous post removes stale
        auto lines first via _remove_tax_postings.
        """
        # Clean up any prior auto tax lines so repost is idempotent.
        self._remove_tax_postings(voucher)

        # Determine the next line_no to use for auto-generated rows.
        existing_max = voucher.lines.aggregate(max_no=models.Max("line_no"))["max_no"] or 0

        next_line_no = max(existing_max + 1, 9000)
        new_lines = []

        for line in voucher.lines.filter(is_auto_tax_posting=False):
            group = line.invoice_group_code
            tax_amount = line.tax_amount_vnd or Decimal("0")
            if tax_amount == 0 or not group:
                continue

            if group.code == self.INPUT_GROUP_CODE:
                new_lines.append(
                    VoucherLine(
                        voucher=voucher,
                        line_no=next_line_no,
                        account_code=self.INPUT_TAX_ACCOUNT,
                        debit_vnd=tax_amount,
                        credit_vnd=Decimal("0"),
                        description=f"VAT đầu vào (auto) — {line.invoice_no or ''}".strip(),
                        is_auto_tax_posting=True,
                    )
                )
                next_line_no += 1
            elif group.code == self.OUTPUT_GROUP_CODE:
                new_lines.append(
                    VoucherLine(
                        voucher=voucher,
                        line_no=next_line_no,
                        account_code=self.OUTPUT_TAX_ACCOUNT,
                        debit_vnd=Decimal("0"),
                        credit_vnd=tax_amount,
                        description=f"VAT đầu ra (auto) — {line.invoice_no or ''}".strip(),
                        is_auto_tax_posting=True,
                    )
                )
                next_line_no += 1

        if new_lines:
            VoucherLine.objects.bulk_create(new_lines)

    def _remove_tax_postings(self, voucher: AccountingVoucher) -> None:
        """Delete all auto-generated tax posting lines for a voucher."""
        voucher.lines.filter(is_auto_tax_posting=True).delete()
