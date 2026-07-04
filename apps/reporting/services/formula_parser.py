"""Config-driven financial-report engine.

The ``ReportEngine`` reads ``FinancialReportLine`` rows for a given
``report_type``, evaluates each line's value (either from an account-
code pattern aggregation or a formula referencing sibling ``ma_so``
codes), and returns a list of ordered dicts that the view/template can
render directly.

The evaluation strategy per line (in precedence order):

1. If ``cong_thuc`` is non-empty, parse the formula and resolve every
   ``ma_so`` reference against the already-computed sibling values.
2. Otherwise aggregate ``AccountPeriodBalance`` rows whose
   ``account_code`` matches the ``tk_no_pattern`` / ``tk_co_pattern``
   wildcard patterns.
3. Header lines (``is_header=True``) with no data source render a value
   of ``None`` (template shows blank).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Q, Sum

from apps.ledger.models import AccountPeriodBalance
from apps.reporting.models import FinancialReportLine

if TYPE_CHECKING:
    from apps.core.models import Company


@dataclass
class ReportLine:
    """A single rendered report line with computed value."""

    stt: str
    ma_so: str
    chi_tieu: str
    thuyet_minh: str
    is_header: bool
    parent_ma_so: str
    value: Decimal | None = None
    raw_config: FinancialReportLine | None = field(default=None, repr=False)


def _expand_pattern(pattern: str) -> Q:
    """Translate a wildcard account pattern into a Django ``Q`` filter.

    ``1331*`` -> ``account_code__startswith='1331'``
    ``111``   -> ``account_code__startswith='111'``
    Multiple comma-separated patterns are OR-ed together.
    """
    if not pattern:
        return Q(pk__in=[])
    q = Q()
    for part in pattern.split(","):
        part = part.strip()
        if not part:
            continue
        if part.endswith("*"):
            q |= Q(account_code__startswith=part[:-1])
        else:
            q |= Q(account_code__startswith=part)
    return q


# ----- formula parsing ---------------------------------------------------

_TOKEN_RE = re.compile(r"[+\-*/]")
_REF_RE = re.compile(r"^\d+[A-Za-z0-9_]*$")


def parse_formula_tokens(expr: str) -> list[tuple[str, str]]:
    """Split ``110+120-130`` into ``[('+','110'), ('+','120'), ('-','130')]``.

    The first token implicitly carries a ``+`` sign.
    Raises ``ValueError`` if a token is empty or contains illegal chars.
    """
    expr = expr.strip()
    if expr.startswith("="):
        expr = expr[1:]
    if not expr:
        return []

    tokens: list[tuple[str, str]] = []
    sign = "+"
    buf = ""
    for ch in expr:
        if ch in "+-*/":
            if buf.strip():
                tokens.append((sign, buf.strip()))
            elif tokens:
                # stray operator - ignore
                pass
            sign = ch
            buf = ""
        else:
            buf += ch
    if buf.strip():
        tokens.append((sign, buf.strip()))

    for _, tok in tokens:
        if not _REF_RE.match(tok):
            raise ValueError(f"Invalid formula token: {tok!r} in {expr!r}")
    return tokens


class ReportEngine:
    """Evaluate ``FinancialReportLine`` config into a list of ``ReportLine``."""

    def __init__(self, company: Company | None, fiscal_year: int, period: int):
        self.company = company
        self.fiscal_year = fiscal_year
        self.period = period
        self._balance_cache: dict[str, tuple[Decimal, Decimal]] = {}

    # -- account-pattern aggregation -------------------------------------

    def _aggregate_pattern(self, pattern: str, field_prefix: str) -> Decimal:
        """Sum debit or credit columns for accounts matching ``pattern``."""
        key = f"{field_prefix}:{pattern}"
        if key in self._balance_cache:
            d, c = self._balance_cache[key]
            return d if field_prefix == "debit" else c

        qs = AccountPeriodBalance.objects.filter(
            fiscal_year=self.fiscal_year,
            period=self.period,
        ).filter(_expand_pattern(pattern))
        if self.company is not None:
            qs = qs.filter(company=self.company)

        agg = qs.aggregate(d=Sum("period_debit"), c=Sum("period_credit"))
        d = agg["d"] or Decimal("0")
        c = agg["c"] or Decimal("0")
        self._balance_cache[key] = (d, c)
        return d if field_prefix == "debit" else c

    def _aggregate_closing(self, pattern: str, field_prefix: str) -> Decimal:
        """Sum closing debit or credit columns for accounts matching ``pattern``."""
        key = f"closing_{field_prefix}:{pattern}"
        if key in self._balance_cache:
            d, c = self._balance_cache[key]
            return d if field_prefix == "debit" else c

        qs = AccountPeriodBalance.objects.filter(
            fiscal_year=self.fiscal_year,
            period=self.period,
        ).filter(_expand_pattern(pattern))
        if self.company is not None:
            qs = qs.filter(company=self.company)

        agg = qs.aggregate(d=Sum("closing_debit"), c=Sum("closing_credit"))
        d = agg["d"] or Decimal("0")
        c = agg["c"] or Decimal("0")
        self._balance_cache[key] = (d, c)
        return d if field_prefix == "debit" else c

    # -- line evaluation -------------------------------------------------

    def _resolve_ref(self, ref: str, values: dict[str, Decimal]) -> Decimal:
        """Resolve a formula reference: either a ma_so key or a numeric literal."""
        if ref in values:
            return values[ref]
        try:
            return Decimal(ref)
        except Exception:
            return Decimal("0")

    def _eval_cong_thuc(self, formula: str, values: dict[str, Decimal]) -> Decimal:
        """Evaluate a formula like ``110+120-130`` using resolved ma_so values."""
        result = Decimal("0")
        for sign, tok in parse_formula_tokens(formula):
            val = self._resolve_ref(tok, values)
            if sign == "+":
                result += val
            elif sign == "-":
                result -= val
            elif sign == "*":
                result *= val
            elif sign == "/" and val != 0:
                result /= val
        return result

    def _compute_line_value(
        self,
        line: FinancialReportLine,
        values: dict[str, Decimal],
        use_closing: bool = False,
    ) -> Decimal | None:
        """Compute the value for a single config line.

        Args:
            line: the FinancialReportLine config row.
            values: already-computed sibling ma_so -> value dict.
            use_closing: when True, use closing balances instead of period
                movements (used by the balance sheet).
        """
        # Formula takes precedence.
        if line.cong_thuc.strip():
            return self._eval_cong_thuc(line.cong_thuc, values)

        # Header lines with no data source -> blank.
        if line.is_header and not line.tk_no_pattern and not line.tk_co_pattern:
            return None

        agg_fn = self._aggregate_closing if use_closing else self._aggregate_pattern

        debit = Decimal("0")
        credit = Decimal("0")
        if line.tk_no_pattern:
            debit = agg_fn(line.tk_no_pattern, "debit")
        if line.tk_co_pattern:
            credit = agg_fn(line.tk_co_pattern, "credit")

        # For P&L lines (no closing balance concept) the "natural" side is:
        #   - revenue / equity / liability: credit - debit
        #   - expense / asset: debit - credit
        # The line declares which side via tk_no_pattern (debit-natured)
        # and tk_co_pattern (credit-natured); we return net of both.
        if debit > 0 and credit > 0:
            return debit - credit
        if debit > 0:
            return debit
        if credit > 0:
            return credit
        return Decimal("0")

    # -- public API ------------------------------------------------------

    def generate(self, report_type: str, use_closing: bool = False) -> list[ReportLine]:
        """Build the full ordered list of rendered lines for ``report_type``.

        Uses a two-pass evaluation:
          1. Compute every line that has account patterns (no formula).
          2. Resolve formula lines using the now-complete values dict.

        This ensures parent lines (which appear before children in
        ``display_order``) can reference child ``ma_so`` codes.
        """
        configs = list(
            FinancialReportLine.objects.filter(report_type=report_type).order_by(
                "display_order", "id"
            )
        )

        values: dict[str, Decimal] = {}

        # Pass 1: pattern-based lines.
        for cfg in configs:
            if cfg.cong_thuc.strip():
                continue
            if cfg.is_header and not cfg.tk_no_pattern and not cfg.tk_co_pattern:
                val: Decimal | None = None
            else:
                val = self._compute_line_value(cfg, values, use_closing=use_closing)
            if cfg.ma_so:
                values[cfg.ma_so] = val or Decimal("0")

        # Pass 2: formula-based lines (may reference pass-1 values).
        for cfg in configs:
            if not cfg.cong_thuc.strip():
                continue
            val = self._eval_cong_thuc(cfg.cong_thuc, values)
            if cfg.ma_so:
                values[cfg.ma_so] = val or Decimal("0")

        # Build the output list in display order.
        result: list[ReportLine] = []
        for cfg in configs:
            if cfg.ma_so:
                val = values.get(cfg.ma_so)
            elif cfg.cong_thuc.strip():
                val = self._eval_cong_thuc(cfg.cong_thuc, values)
            elif cfg.is_header and not cfg.tk_no_pattern and not cfg.tk_co_pattern:
                val = None
            else:
                val = self._compute_line_value(cfg, values, use_closing=use_closing)
            result.append(
                ReportLine(
                    stt=cfg.stt,
                    ma_so=cfg.ma_so,
                    chi_tieu=cfg.chi_tieu,
                    thuyet_minh=cfg.thuyet_minh,
                    is_header=cfg.is_header,
                    parent_ma_so=cfg.parent_ma_so,
                    value=val,
                    raw_config=cfg,
                )
            )

        return result
