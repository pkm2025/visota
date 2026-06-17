"""PeriodClosingService — kết chuyển cuối kỳ."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services.voucher_posting_service import VoucherPostingService

# Account code prefixes that get closed
REVENUE_PREFIXES = ("5", "7")  # 511, 515, 711 → credit balances → N to close
EXPENSE_PREFIXES = ("6", "8")  # 632, 641, 642, 635, 811, 821 → debit balances → C to close
PROFIT_ACCOUNT = "421"  # Lợi nhuận chưa phân phối
RESULT_ACCOUNT = "911"  # Xác định KQ


class PeriodClosingService:
    """Kết chuyển cuối kỳ: move revenue/expense balances to TK 911, then to TK 421."""

    def __init__(self, company):
        self.company = company

    @transaction.atomic
    def close_period(self, fiscal_year: int, period: int) -> dict:
        """Close a period by transferring revenue/expense to 911, then 421.

        Idempotent: skips if a closing voucher already exists for this period.
        """
        # Check idempotency
        existing = AccountingVoucher.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            source="closing",
        ).exists()
        if existing:
            return {"skipped": True, "voucher_id": None}

        balances = AccountPeriodBalance.objects.filter(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
        )

        total_revenue = Decimal("0")
        total_expense = Decimal("0")
        kc_lines = []  # (account_code, is_debit, amount)

        for b in balances:
            code = b.account_code
            period_d = b.period_debit or Decimal("0")
            period_c = b.period_credit or Decimal("0")

            net_credit = period_c - period_d  # revenue net
            net_debit = period_d - period_c  # expense net

            if code.startswith(REVENUE_PREFIXES) and net_credit > 0:
                # KC: N5111 (close revenue by debiting)
                kc_lines.append((code, True, net_credit))
                total_revenue += net_credit
            elif code.startswith(EXPENSE_PREFIXES) and net_debit > 0:
                # KC: C642 (close expense by crediting)
                kc_lines.append((code, False, net_debit))
                total_expense += net_debit

        if not kc_lines:
            return {
                "skipped": True,
                "voucher_id": None,
                "reason": "No revenue/expense to close",
            }

        profit = total_revenue - total_expense

        # Create closing voucher
        voucher = AccountingVoucher.objects.create(
            company=self.company,
            fiscal_year=fiscal_year,
            period=period,
            voucher_no=f"KC-{fiscal_year}{period:02d}",
            voucher_type="closing",
            voucher_date=date(fiscal_year, period, 28),  # end of period (simplified)
            currency_code="VND",
            exchange_rate=Decimal("1"),
            status=AccountingVoucher.Status.DRAFT,
            source="closing",
            description=f"Kết chuyển cuối kỳ {period}/{fiscal_year}",
        )

        line_no = 1

        # Step 1: KC revenue → N5xx / C911
        for acc_code, is_debit, amount in kc_lines:
            if is_debit:  # revenue: N5xx
                VoucherLine.objects.create(
                    voucher=voucher,
                    line_no=line_no,
                    account_code=acc_code,
                    debit_vnd=amount,
                    description=f"KC doanh thu {acc_code}",
                )
                line_no += 1

        if total_revenue > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=RESULT_ACCOUNT,
                credit_vnd=total_revenue,
                description="KC doanh thu → 911",
            )
            line_no += 1

        # Step 2: KC expense → N911 / C6xx
        if total_expense > 0:
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=RESULT_ACCOUNT,
                debit_vnd=total_expense,
                description="KC chi phí → 911",
            )
            line_no += 1

        for acc_code, is_debit, amount in kc_lines:
            if not is_debit:  # expense: C6xx
                VoucherLine.objects.create(
                    voucher=voucher,
                    line_no=line_no,
                    account_code=acc_code,
                    credit_vnd=amount,
                    description=f"KC chi phí {acc_code}",
                )
                line_no += 1

        # Step 3: Transfer profit/loss to 421
        if profit > 0:
            # Profit: N911 / C421
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=RESULT_ACCOUNT,
                debit_vnd=profit,
                description="KC lợi nhuận → 421",
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=PROFIT_ACCOUNT,
                credit_vnd=profit,
                description="Lợi nhuận sau thuế",
            )
        elif profit < 0:
            # Loss: N421 / C911
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=PROFIT_ACCOUNT,
                debit_vnd=-profit,
                description="Lỗ kỳ",
            )
            line_no += 1
            VoucherLine.objects.create(
                voucher=voucher,
                line_no=line_no,
                account_code=RESULT_ACCOUNT,
                credit_vnd=-profit,
                description="KC lỗ → 421",
            )

        # Post voucher
        VoucherPostingService().post(voucher)

        return {
            "skipped": False,
            "voucher_id": voucher.id,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "profit": profit,
        }
