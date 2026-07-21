"""Year-to-date (YTD) balance aggregation.

The ``AccountPeriodBalance`` table stores one row per
(company, fiscal_year, period, account_code, object_*).  ``period=0`` holds
the opening balance carried forward from the prior year; periods 1..12 hold
monthly movements only.

Before this module, reports read a single period row, which produced
incorrect numbers whenever the user selected a month other than the first
month with activity (the classic "BCTC không cộng dồn YTD" bug).

``YtdBalanceService`` recomputes the effective opening, period and
closing amounts for any (fiscal_year, period) by combining:

    opening  = period_0_opening + Σ(period=1..N-1) movements
    period   = period N movements   (unchanged)
    closing  = opening + period     (= period_0 + Σ period=1..N movements)

For P&L accounts (5, 6, 7, 8, 9) period 0 is excluded because revenue and
expenses start the year at zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from apps.ledger.models import AccountPeriodBalance

if TYPE_CHECKING:
    from apps.core.models import Company


# Account-code first digits that represent income-statement accounts.
# These begin the year at zero (no carry-forward from period 0).
_PNL_FIRST_DIGITS = ("5", "6", "7", "8", "9")


def _is_pnl_account(account_code: str) -> bool:
    return bool(account_code) and account_code[0] in _PNL_FIRST_DIGITS


@dataclass
class YtdRow:
    """Effective balances for one account/object at a given period.

    Fields:
        opening_*:      balance at start of period N
                        (period-0 + movements of periods 1..N-1).
                        Always 0 for P&L accounts (5/6/7/8/9).
        period_*:       movement **of period N only** (month column on
                        the trial balance).
        period_ytd_*:   cumulative movement for periods 1..N (what P&L
                        reports need).
        closing_*:      opening + period_ytd.
    """

    account_code: str
    object_type: str
    object_code: str
    opening_debit: Decimal
    opening_credit: Decimal
    period_debit: Decimal
    period_credit: Decimal
    period_debit_ytd: Decimal
    period_credit_ytd: Decimal
    closing_debit: Decimal
    closing_credit: Decimal

    def has_activity(self) -> bool:
        return any(
            v != 0
            for v in (
                self.opening_debit,
                self.opening_credit,
                self.period_debit,
                self.period_credit,
                self.closing_debit,
                self.closing_credit,
            )
        )


class YtdBalanceService:
    """Compute YTD opening/period/closing balances for a fiscal period."""

    def __init__(self, company: Company | None, fiscal_year: int, period: int):
        self.company = company
        self.fiscal_year = fiscal_year
        # period=0 means "full year" (aggregate periods 1..12).
        self.period = period if period > 0 else 12
        self.is_full_year = period <= 0

    # -- public API ------------------------------------------------------

    def fetch(self) -> list[YtdRow]:
        """Return effective YTD rows for every account with activity.

        Combines period-0 opening rows (balance-sheet accounts only) with
        monthly movement rows for periods 1..N.  One ``YtdRow`` per
        (account_code, object_type, object_code).

        When ``period`` was passed as 0 (or negative), the service
        aggregates the full fiscal year (periods 1..12) — used by the
        "Cả năm" dropdown option in reports.
        """
        # period=0 originally meant "period-0 opening only".  We now
        # treat it as full-year (periods 1..12), so self.period is set
        # to 12 in __init__.  The _fetch_period_zero_only path is only
        # reached if an explicit very-negative period is passed (edge case).
        if self.period <= 0:
            return self._fetch_period_zero_only()

        # Base queryset: period 0 + periods 1..N for this fiscal year.
        qs = AccountPeriodBalance.objects.filter(
            fiscal_year=self.fiscal_year,
            period__lte=self.period,
        )
        if self.company is not None:
            qs = qs.filter(company=self.company)

        # Aggregate by (account_code, object_type, object_code), separating
        # period-0 (opening) from period>=1 (movements).
        # Django ORM cannot easily do conditional sums over groups in a
        # backend-agnostic way, so we pull the rows and aggregate in Python.
        rows = list(
            qs.only(
                "account_code",
                "object_type",
                "object_code",
                "period",
                "opening_debit",
                "opening_credit",
                "period_debit",
                "period_credit",
            )
        )

        grouped: dict[tuple[str, str, str], dict[str, Decimal]] = {}
        for r in rows:
            key = (r.account_code, r.object_type or "", r.object_code or "")
            bucket = grouped.setdefault(
                key,
                {
                    "opening_debit": Decimal("0"),
                    "opening_credit": Decimal("0"),
                    "period_debit": Decimal("0"),
                    "period_credit": Decimal("0"),
                    "period_debit_ytd": Decimal("0"),
                    "period_credit_ytd": Decimal("0"),
                    "cur_period_debit": Decimal("0"),
                    "cur_period_credit": Decimal("0"),
                },
            )
            if r.period == 0:
                # Period 0 stores the year opening (carried forward).
                bucket["opening_debit"] += r.opening_debit or Decimal("0")
                bucket["opening_credit"] += r.opening_credit or Decimal("0")
                # If period-0 also recorded a movement (rare), fold into opening.
                bucket["opening_debit"] += r.period_debit or Decimal("0")
                bucket["opening_credit"] += r.period_credit or Decimal("0")
            else:
                bucket["period_debit_ytd"] += r.period_debit or Decimal("0")
                bucket["period_credit_ytd"] += r.period_credit or Decimal("0")
                if r.period == self.period:
                    bucket["cur_period_debit"] += r.period_debit or Decimal("0")
                    bucket["cur_period_credit"] += r.period_credit or Decimal("0")

        result: list[YtdRow] = []
        for (account_code, object_type, object_code), b in grouped.items():
            # P&L accounts start the year at zero — drop any period-0 opening.
            if _is_pnl_account(account_code):
                opening_d = Decimal("0")
                opening_c = Decimal("0")
            else:
                opening_d = b["opening_debit"]
                opening_c = b["opening_credit"]

            period_d_ytd = b["period_debit_ytd"]
            period_c_ytd = b["period_credit_ytd"]
            cur_period_d = b["cur_period_debit"]
            cur_period_c = b["cur_period_credit"]

            # Opening for period N (on the trial balance) is period-0 plus
            # the cumulative YTD movement *before* period N.  For P&L
            # accounts this collapses to YTD-before-N; for BS accounts it
            # includes the year opening carry-forward.
            opening_d_effective = opening_d + (period_d_ytd - cur_period_d)
            opening_c_effective = opening_c + (period_c_ytd - cur_period_c)

            # Closing follows AccountPeriodBalance.recalculate_closing
            # semantics: the heavier side wins, the other collapses to zero.
            close_d_total = opening_d_effective + cur_period_d
            close_c_total = opening_c_effective + cur_period_c
            if close_d_total >= close_c_total:
                closing_d = close_d_total - close_c_total
                closing_c = Decimal("0")
            else:
                closing_c = close_c_total - close_d_total
                closing_d = Decimal("0")

            result.append(
                YtdRow(
                    account_code=account_code,
                    object_type=object_type,
                    object_code=object_code,
                    opening_debit=opening_d_effective,
                    opening_credit=opening_c_effective,
                    period_debit=cur_period_d,
                    period_credit=cur_period_c,
                    period_debit_ytd=period_d_ytd,
                    period_credit_ytd=period_c_ytd,
                    closing_debit=closing_d,
                    closing_credit=closing_c,
                )
            )

        result.sort(key=lambda r: r.account_code)
        return result

    # -- period 0 (year opening) ----------------------------------------

    def _fetch_period_zero_only(self) -> list[YtdRow]:
        qs = AccountPeriodBalance.objects.filter(
            fiscal_year=self.fiscal_year,
            period=0,
        )
        if self.company is not None:
            qs = qs.filter(company=self.company)

        out: list[YtdRow] = []
        for r in qs.only(
            "account_code",
            "object_type",
            "object_code",
            "opening_debit",
            "opening_credit",
        ):
            od = r.opening_debit or Decimal("0")
            oc = r.opening_credit or Decimal("0")
            if od == 0 and oc == 0:
                continue
            out.append(
                YtdRow(
                    account_code=r.account_code,
                    object_type=r.object_type or "",
                    object_code=r.object_code or "",
                    opening_debit=od,
                    opening_credit=oc,
                    period_debit=Decimal("0"),
                    period_credit=Decimal("0"),
                    period_debit_ytd=Decimal("0"),
                    period_credit_ytd=Decimal("0"),
                    closing_debit=od,
                    closing_credit=oc,
                )
            )
        return out

    # -- helpers for engines that aggregate by account-code pattern -----

    def aggregate_closing(self, account_code_prefix: str) -> tuple[Decimal, Decimal]:
        """Return (closing_debit, closing_credit) summed for accounts whose
        code starts with ``account_code_prefix`` (e.g. ``111`` or ``1111``).
        """
        d = Decimal("0")
        c = Decimal("0")
        for row in self.fetch():
            code = row.account_code
            if code == account_code_prefix or code.startswith(account_code_prefix):
                d += row.closing_debit
                c += row.closing_credit
        return d, c

    def aggregate_period_ytd(self, account_code_prefix: str) -> tuple[Decimal, Decimal]:
        """Return (period_debit_ytd, period_credit_ytd) summed for matching accounts.

        YTD period movements (Jan..N) — what income-statement reports need.
        """
        d = Decimal("0")
        c = Decimal("0")
        for row in self.fetch():
            code = row.account_code
            if code == account_code_prefix or code.startswith(account_code_prefix):
                d += row.period_debit_ytd
                c += row.period_credit_ytd
        return d, c
