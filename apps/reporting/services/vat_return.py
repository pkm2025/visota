"""VAT Return (01/GTGT) — config-driven TT80 engine.

The :class:`VATReturnService` evaluates :class:`VATReportLine` config
rows to produce the TT80/2021 VAT return form.  Each line either:

1. Carries a ``cong_thuc`` formula like ``[25]+[26]-[27]`` referencing
   sibling line codes (resolved recursively with cycle detection).
2. Aggregates an amount column on :class:`VoucherLine` filtered by
   account-code pattern (``tk_filter``), invoice group
   (``invoice_group_filter``) and tax-rate code (``tax_code_filter``)
   for the requested period.

Backward-compatibility shim: ``generate(fiscal_year, period)`` still
returns the legacy dict shape (``vat_output``, ``vat_input_credit``,
``vat_payable``, ``vat_credit``, ``is_payable``) plus a richer
``lines`` list.  Callers that only consume the dict keys continue to
work; new callers (the TT80 view / XML view) read ``lines`` and the
``values_by_code`` mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Q, Sum

from apps.ledger.models import VoucherLine
from apps.reporting.models import VATReportLine

if TYPE_CHECKING:  # pragma: no cover
    from apps.core.models import Company


# --- formula parsing -----------------------------------------------------

# Matches a single operand inside a formula: either a [XX] reference
# or a numeric literal (integer / decimal).  Whitespace is tolerated.
_OPERAND_RE = re.compile(r"^\s*(\[\s*\d+\s*\]|\d+(?:\.\d+)?)\s*$")
_REF_TOKEN_RE = re.compile(r"^\[\s*(\d+)\s*\]$")


def _split_formula(expr: str) -> list[tuple[str, str]]:
    """Tokenise ``[25]+[26]-[27]`` into ``[('+', '[25]'), ('+', '[26]'), ('-', '[27]')]``.

    Supports ``+``, ``-``, and ``*`` operators.  The first operand
    carries an implicit ``+`` sign.  Raises ``ValueError`` if any
    operand fails to match the operand grammar.
    """
    expr = expr.strip()
    if expr.startswith("="):
        expr = expr[1:].strip()
    if not expr:
        return []

    tokens: list[tuple[str, str]] = []
    sign = "+"
    buf = ""
    for ch in expr:
        if ch in "+-*":
            piece = buf.strip()
            if piece:
                tokens.append((sign, piece))
            sign = ch
            buf = ""
        else:
            buf += ch
    if buf.strip():
        tokens.append((sign, buf.strip()))

    cleaned: list[tuple[str, str]] = []
    for sgn, tok in tokens:
        if not _OPERAND_RE.match(tok):
            raise ValueError(f"Invalid formula token: {tok!r} in {expr!r}")
        cleaned.append((sgn, tok))
    return cleaned


def _operand_ref(tok: str) -> str | None:
    """Return the bare line code (e.g. ``25``) for a ``[25]`` token, else None."""
    m = _REF_TOKEN_RE.match(tok)
    return m.group(1) if m else None


@dataclass
class VATLine:
    """A single rendered VAT return line."""

    line_code: str
    chi_tieu: str
    section: str
    stt: str
    is_header: bool
    display_order: int
    value: Decimal | None = None
    cong_thuc: str = ""
    raw_config: VATReportLine | None = field(default=None, repr=False)


class VATReturnService:
    """Generate VAT return data from ``VATReportLine`` config + ``VoucherLine``.

    The engine falls back to the legacy ``AccountPeriodBalance``-based
    computation when no ``VATReportLine`` config has been seeded yet,
    so deployments that haven't run ``seed_vat_tt80`` keep working.
    """

    def __init__(self, company: Company | None = None):
        self.company = company

    # -- aggregation helpers --------------------------------------------

    @staticmethod
    def _tk_q(pattern: str) -> Q:
        """Translate a wildcard account pattern into a Django ``Q`` filter.

        ``1331*`` → ``account_code__startswith='1331'``
        ``1331``  → ``account_code='1331'``
        Comma-separated patterns are OR-ed.
        """
        if not pattern:
            return Q()
        q = Q()
        for part in pattern.split(","):
            part = part.strip()
            if not part:
                continue
            if part.endswith("*"):
                q |= Q(account_code__startswith=part[:-1])
            else:
                q |= Q(account_code=part)
        return q

    def _base_voucher_lines(self, fiscal_year: int, period: int) -> "VoucherLine.objects":  # type: ignore[name-defined]
        qs = VoucherLine.objects.filter(
            voucher__fiscal_year=fiscal_year,
            voucher__period=period,
            voucher__status__gte=2,
        )
        if self.company is not None:
            qs = qs.filter(voucher__company=self.company)
        return qs

    def _aggregate_line(self, cfg: VATReportLine, fiscal_year: int, period: int) -> Decimal:
        """Sum ``cfg.amount_field`` over VoucherLine matching the three filters."""
        qs = self._base_voucher_lines(fiscal_year, period)
        if cfg.tk_filter:
            qs = qs.filter(self._tk_q(cfg.tk_filter))
        if cfg.invoice_group_filter:
            qs = qs.filter(invoice_group_code_id=cfg.invoice_group_filter)
        if cfg.tax_code_filter:
            qs = qs.filter(tax_code_id=cfg.tax_code_filter)

        agg = qs.aggregate(s=Sum(cfg.amount_field))
        return agg["s"] or Decimal("0")

    # -- formula evaluation ---------------------------------------------

    def _eval_formula(
        self,
        formula: str,
        values: dict[str, Decimal],
        resolving: set[str],
        configs_by_code: dict[str, VATReportLine],
        fiscal_year: int,
        period: int,
    ) -> Decimal:
        """Evaluate ``[25]+[26]-[27]`` resolving refs recursively.

        Operators ``+``, ``-`` (additive) and ``*`` (multiplicative) are
        supported with conventional precedence (``*`` binds tighter than
        ``+``/``-``).  References ``[XX]`` are resolved recursively via
        :meth:`_resolve_line_value`; ``resolving`` carries the set of
        line codes currently being resolved and a re-entrant reference
        raises ``ValueError`` to break the cycle.
        """
        tokens = _split_formula(formula)
        if not tokens:
            return Decimal("0")

        def operand_value(tok: str) -> Decimal:
            ref = _operand_ref(tok)
            if ref is None:
                return Decimal(tok)
            if ref in resolving:
                raise ValueError(f"Circular formula reference to [{ref}] in {formula!r}")
            return self._resolve_line_value(
                ref,
                values,
                resolving | {ref},
                configs_by_code,
                fiscal_year,
                period,
            )

        # First pass: fold multiplicative ``*`` runs into single terms.
        # Each term carries a sign (the operator preceding the first
        # factor in the run) and a magnitude (product of factors).
        additive: list[tuple[str, Decimal]] = []
        idx = 0
        while idx < len(tokens):
            sign, tok = tokens[idx]
            magnitude = operand_value(tok)
            idx += 1
            while idx < len(tokens) and tokens[idx][0] == "*":
                magnitude *= operand_value(tokens[idx][1])
                idx += 1
            additive.append((sign, magnitude))

        result = Decimal("0")
        for sign, magnitude in additive:
            if sign == "-":
                result -= magnitude
            else:
                result += magnitude
        return result

    def _resolve_line_value(
        self,
        line_code: str,
        values: dict[str, Decimal],
        resolving: set[str],
        configs_by_code: dict[str, VATReportLine],
        fiscal_year: int,
        period: int,
    ) -> Decimal:
        """Resolve a single line code, caching the result in ``values``."""
        if line_code in values:
            return values[line_code]
        cfg = configs_by_code.get(line_code)
        if cfg is None:
            # Unknown reference: treat as zero so unseeded formulae
            # don't crash the whole return.
            values[line_code] = Decimal("0")
            return Decimal("0")
        val = self._compute_one(cfg, values, resolving, configs_by_code, fiscal_year, period)
        values[line_code] = val
        return val

    def _compute_one(
        self,
        cfg: VATReportLine,
        values: dict[str, Decimal],
        resolving: set[str],
        configs_by_code: dict[str, VATReportLine],
        fiscal_year: int,
        period: int,
    ) -> Decimal:
        if cfg.cong_thuc.strip():
            return self._eval_formula(
                cfg.cong_thuc, values, resolving, configs_by_code, fiscal_year, period
            )
        if (
            cfg.is_header
            and not cfg.tk_filter
            and not cfg.invoice_group_filter
            and not cfg.tax_code_filter
        ):
            return Decimal("0")
        return self._aggregate_line(cfg, fiscal_year, period)

    # -- public API ------------------------------------------------------

    def _legacy_balances(self, fiscal_year: int, period: int) -> tuple[Decimal, Decimal]:
        """Aggregate output/input VAT from ``AccountPeriodBalance``.

        Used by the legacy compat keys (``vat_output``,
        ``vat_input_credit``) so the simple payable/credit summary keeps
        working even when postings don't carry invoice_group/tax_code
        metadata (e.g. legacy ``SalesInvoiceService`` flows).
        """
        from apps.ledger.models import AccountPeriodBalance

        qs = AccountPeriodBalance.objects.filter(fiscal_year=fiscal_year, period=period)
        if self.company is not None:
            qs = qs.filter(company=self.company)
        vat_output = Decimal("0")
        vat_input = Decimal("0")
        for b in qs:
            code = b.account_code or ""
            if code.startswith("33311"):
                vat_output += b.period_credit or 0
            elif code.startswith("1331"):
                vat_input += b.period_debit or 0
        return vat_output, vat_input

    def generate(self, fiscal_year: int, period: int) -> dict:
        """Compute the full VAT return for ``(fiscal_year, period)``.

        Returns a dict with:
          - ``fiscal_year`` / ``period`` — echo of inputs
          - ``lines`` — ordered list of :class:`VATLine`
          - ``values_by_code`` — ``{line_code: Decimal}``
          - ``vat_output`` / ``vat_input_credit`` / ``vat_payable`` /
            ``vat_credit`` / ``is_payable`` — legacy compat keys
          - ``sections`` — TT80 layout grouping (A / B-I / B-II / C)
        """
        configs = list(VATReportLine.objects.all().order_by("display_order", "id"))
        configs_by_code = {c.line_code: c for c in configs}

        values: dict[str, Decimal] = {}
        for cfg in configs:
            if cfg.line_code not in values:
                self._resolve_line_value(
                    cfg.line_code, values, set(), configs_by_code, fiscal_year, period
                )

        # Build the rendered line list.
        lines = [
            VATLine(
                line_code=cfg.line_code,
                chi_tieu=cfg.chi_tieu,
                section=cfg.section,
                stt=cfg.stt,
                is_header=cfg.is_header,
                display_order=cfg.display_order,
                value=values.get(cfg.line_code, Decimal("0")),
                cong_thuc=cfg.cong_thuc,
                raw_config=cfg,
            )
            for cfg in configs
        ]

        # Group lines by section for the TT80 layout.
        sections: dict[str, list[VATLine]] = {}
        for ln in lines:
            sections.setdefault(ln.section, []).append(ln)

        # Legacy dict shape for backward compatibility.
        # Prefer TT80 line values when available; fall back to the
        # AccountPeriodBalance-based computation only when no config
        # exists (so legacy callers without seed_vat_tt80 keep working).
        legacy_output, legacy_input = self._legacy_balances(fiscal_year, period)
        if configs:
            vat_output = values.get("28", legacy_output)
            # [22] = total input VAT (creditable); [23] = non-creditable
            vat_input_total = values.get("22", legacy_input)
        else:
            vat_output = legacy_output
            vat_input_total = legacy_input
        vat_input_credit = values.get("24", vat_input_total)
        if vat_output > vat_input_total:
            vat_payable = vat_output - vat_input_total
            vat_credit = Decimal("0")
            is_payable = True
        else:
            vat_payable = Decimal("0")
            vat_credit = vat_input_total - vat_output
            is_payable = False

        return {
            "fiscal_year": fiscal_year,
            "period": period,
            "lines": lines,
            "sections": sections,
            "values_by_code": values,
            "vat_output": vat_output,
            "vat_input_credit": vat_input_credit,
            "vat_payable": vat_payable,
            "vat_credit": vat_credit,
            "is_payable": is_payable,
        }
