"""BalanceConversionService: convert TT132/TT133 balances to TT58 DNSN opening balances.

Maps TT132/TT133 account codes (TK) to DNSN ledger types (S2d, S4a, etc.)
and creates DnsnLedgerBalance opening entries for a TT58 fiscal year.

Mapping (per architecture.md):
    TK 111/112     -> S2d (tiền — cash + bank)
    TK 131/1318    -> S4a (công nợ — receivables)
    TK 1521/1524/1526 -> S2c (hàng hóa — inventory)
    TK 211         -> S4b (TSCĐ — fixed assets)
    TK 1331        -> S3b (thuế GTGT đầu vào — input VAT)
    TK 331x        -> S4a (phải trả — payables)
    TK 33311/33331 -> S3b (thuế GTGT đầu ra — output VAT)
    TK 33334/33338 -> S4c (thuế khác — other taxes)
    TK 411/4118    -> S4d (vốn CSH — owner's equity)

Conversion is idempotent: re-running for the same (company, fiscal_year, period)
updates existing DnsnLedgerBalance rows instead of creating duplicates.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction

from apps.core.models import Company
from apps.ledger.dnsn_ledger_types import LEDGER_LABELS
from apps.ledger.models import AccountPeriodBalance, DnsnLedgerBalance

# ---------------------------------------------------------------------------
# Account-to-ledger mapping
# ---------------------------------------------------------------------------

# Each entry: (account_code_prefix, ledger_type, balance_field, sign)
# - balance_field: which DnsnLedgerBalance opening field to accumulate into
#   ("opening_cash", "opening_revenue", "opening_cost", "opening_vat")
# - sign: +1 if the source debit/credit is a positive contribution,
#         -1 if it should be subtracted (e.g., payables reduce receivables net)
#
# For debit-nature accounts (assets, input VAT), we read closing_debit.
# For credit-nature accounts (liabilities, equity, output VAT), we read closing_credit.

# Mapping table: account_code -> (ledger_type, opening_field, nature)
# nature = "debit" means we read closing_debit, "credit" means closing_credit.
ACCOUNT_LEDGER_MAP: list[dict] = [
    # Cash and bank (TK 111, 112) -> S2d (opening_cash)
    {"prefix": "111", "ledger_type": "s2d", "opening_field": "opening_cash", "nature": "debit"},
    {"prefix": "112", "ledger_type": "s2d", "opening_field": "opening_cash", "nature": "debit"},
    # Receivables (TK 131, 1318) -> S4a (opening_cash for receivable side)
    {"prefix": "131", "ledger_type": "s4a", "opening_field": "opening_cash", "nature": "debit"},
    {"prefix": "1318", "ledger_type": "s4a", "opening_field": "opening_cash", "nature": "debit"},
    # Inventory (TK 1521, 1524, 1526) -> S2c (opening_revenue for inventory value)
    {"prefix": "1521", "ledger_type": "s2c", "opening_field": "opening_revenue", "nature": "debit"},
    {"prefix": "1524", "ledger_type": "s2c", "opening_field": "opening_revenue", "nature": "debit"},
    {"prefix": "1526", "ledger_type": "s2c", "opening_field": "opening_revenue", "nature": "debit"},
    # Fixed assets (TK 211) -> S4b (opening_cash for asset value)
    {"prefix": "211", "ledger_type": "s4b", "opening_field": "opening_cash", "nature": "debit"},
    # Input VAT (TK 1331) -> S3b (opening_vat, input side)
    {"prefix": "1331", "ledger_type": "s3b", "opening_field": "opening_vat", "nature": "debit"},
    # Payables (TK 3311, 3312, 3318, 331) -> S4a (opening_cost for payable side)
    {"prefix": "331", "ledger_type": "s4a", "opening_field": "opening_cost", "nature": "credit"},
    # Output VAT (TK 33311, 33331) -> S3b (opening_vat, output side)
    {"prefix": "33311", "ledger_type": "s3b", "opening_field": "opening_vat", "nature": "credit"},
    {"prefix": "33331", "ledger_type": "s3b", "opening_field": "opening_vat", "nature": "credit"},
    # Other taxes (TK 33334, 33338) -> S4c (opening_vat for tax payable)
    {"prefix": "33334", "ledger_type": "s4c", "opening_field": "opening_vat", "nature": "credit"},
    {"prefix": "33338", "ledger_type": "s4c", "opening_field": "opening_vat", "nature": "credit"},
    # Owner's equity (TK 411, 4118) -> S4d (opening_cash for equity)
    {"prefix": "411", "ledger_type": "s4d", "opening_field": "opening_cash", "nature": "credit"},
    {"prefix": "4118", "ledger_type": "s4d", "opening_field": "opening_cash", "nature": "credit"},
]


def _find_mapping(account_code: str) -> dict | None:
    """Find the ledger mapping for an account code by prefix matching.

    Longer prefixes are checked first for specificity (e.g., "1521" before "152").
    """
    # Sort by prefix length descending so most specific match wins
    sorted_map = sorted(ACCOUNT_LEDGER_MAP, key=lambda m: len(m["prefix"]), reverse=True)
    for entry in sorted_map:
        prefix = entry["prefix"]
        # Match if account_code equals prefix or starts with prefix + digit
        # (e.g., "331" matches "331", "3311", "3318"; "111" matches "111", "1111")
        if account_code == prefix or account_code.startswith(prefix):
            return entry
    return None


# ---------------------------------------------------------------------------
# Conversion summary data structures
# ---------------------------------------------------------------------------


@dataclass
class ConversionRow:
    """One row in the conversion summary: source account -> target ledger."""

    source_account_code: str
    source_balance: Decimal
    target_ledger_type: str
    target_ledger_label: str
    converted_amount: Decimal


@dataclass
class ConversionSummary:
    """Summary of a balance conversion operation.

    Contains per-account mapping rows and aggregate totals.
    The source and converted totals always match (every mapped source
    balance is fully reflected in the target ledger amounts).
    """

    company: Company
    fiscal_year: int
    source_period: int
    rows: list[ConversionRow] = field(default_factory=list)
    converted_count: int = 0

    @property
    def total_source(self) -> Decimal:
        """Sum of all source balances."""
        return sum((r.source_balance for r in self.rows), Decimal("0"))

    @property
    def total_converted(self) -> Decimal:
        """Sum of all converted amounts (equals total_source)."""
        return sum((r.converted_amount for r in self.rows), Decimal("0"))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BalanceConversionService:
    """Convert TT132/TT133 AccountPeriodBalance to TT58 DnsnLedgerBalance opening entries.

    Usage:
        service = BalanceConversionService()
        summary = service.convert(company, fiscal_year=2026, source_period=1)

    The conversion is idempotent: calling convert() multiple times for the
    same (company, fiscal_year, source_period) will update existing
    DnsnLedgerBalance rows rather than creating duplicates.
    """

    @transaction.atomic
    def convert(
        self,
        company: Company,
        fiscal_year: int,
        source_period: int,
    ) -> ConversionSummary:
        """Convert account balances to DNSN ledger opening balances.

        Reads AccountPeriodBalance for the given company/fiscal_year/period,
        maps each account code to a DNSN ledger type, and creates or updates
        DnsnLedgerBalance opening entries.

        Args:
            company: The company to convert balances for.
            fiscal_year: The fiscal year for the DNSN opening balances.
            source_period: The source period (1-12) to read balances from.
                           Also used as the target period for DNSN balances.

        Returns:
            ConversionSummary with per-account mapping details.
        """
        summary = ConversionSummary(
            company=company,
            fiscal_year=fiscal_year,
            source_period=source_period,
        )

        # Fetch all account balances for the source period
        balances = AccountPeriodBalance.objects.filter(
            company=company,
            fiscal_year=fiscal_year,
            period=source_period,
        )

        # Aggregate amounts by (ledger_type, opening_field)
        # Key: (ledger_type, opening_field), Value: Decimal total
        aggregated: dict[tuple[str, str], Decimal] = {}
        detail_rows: list[ConversionRow] = []

        for bal in balances:
            mapping = _find_mapping(bal.account_code)
            if mapping is None:
                continue  # Skip unmapped accounts

            # Read the appropriate balance side based on nature
            if mapping["nature"] == "debit":
                amount = bal.closing_debit or Decimal("0")
            else:
                amount = bal.closing_credit or Decimal("0")

            if amount == 0:
                continue  # Skip zero balances

            key = (mapping["ledger_type"], mapping["opening_field"])
            aggregated[key] = aggregated.get(key, Decimal("0")) + amount

            detail_rows.append(
                ConversionRow(
                    source_account_code=bal.account_code,
                    source_balance=amount,
                    target_ledger_type=mapping["ledger_type"],
                    target_ledger_label=LEDGER_LABELS.get(
                        mapping["ledger_type"], mapping["ledger_type"].upper()
                    ),
                    converted_amount=amount,
                )
            )

        # Group by ledger_type to create/update DnsnLedgerBalance rows
        ledger_types_involved = {lt for (lt, _field) in aggregated}

        created_count = 0
        for ledger_type in ledger_types_involved:
            balance_obj, created = DnsnLedgerBalance.objects.get_or_create(
                company=company,
                fiscal_year=fiscal_year,
                period=source_period,
                ledger_type=ledger_type,
            )

            if created:
                created_count += 1

            # Reset opening fields before applying (idempotent: always recompute from source)
            balance_obj.opening_cash = Decimal("0")
            balance_obj.opening_revenue = Decimal("0")
            balance_obj.opening_cost = Decimal("0")
            balance_obj.opening_vat = Decimal("0")

            # Apply aggregated amounts for this ledger_type
            for (lt, opening_field), amount in aggregated.items():
                if lt == ledger_type:
                    current = getattr(balance_obj, opening_field) or Decimal("0")
                    setattr(balance_obj, opening_field, current + amount)

            # Closing = opening (no period activity for opening balances)
            balance_obj.recalculate_closing()
            balance_obj.save()

        summary.rows = detail_rows
        summary.converted_count = created_count
        return summary

    def get_conversion_summary(
        self,
        company: Company,
        fiscal_year: int,
        period: int,
    ) -> ConversionSummary:
        """Build a summary from existing DnsnLedgerBalance opening entries.

        Unlike convert(), this does not modify any data. It reconstructs
        the conversion summary from already-converted balances.

        Args:
            company: The company.
            fiscal_year: The fiscal year.
            period: The period.

        Returns:
            ConversionSummary reconstructed from existing DnsnLedgerBalance rows.
        """
        summary = ConversionSummary(
            company=company,
            fiscal_year=fiscal_year,
            source_period=period,
        )

        balances = DnsnLedgerBalance.objects.filter(
            company=company,
            fiscal_year=fiscal_year,
            period=period,
        )

        for bal in balances:
            label = LEDGER_LABELS.get(bal.ledger_type, bal.ledger_type.upper())

            # Add a row for each non-zero opening field
            if bal.opening_cash and bal.opening_cash != 0:
                summary.rows.append(
                    ConversionRow(
                        source_account_code=f"(aggregated → {bal.ledger_type})",
                        source_balance=bal.opening_cash,
                        target_ledger_type=bal.ledger_type,
                        target_ledger_label=label,
                        converted_amount=bal.opening_cash,
                    )
                )
            if bal.opening_revenue and bal.opening_revenue != 0:
                summary.rows.append(
                    ConversionRow(
                        source_account_code=f"(aggregated → {bal.ledger_type})",
                        source_balance=bal.opening_revenue,
                        target_ledger_type=bal.ledger_type,
                        target_ledger_label=label,
                        converted_amount=bal.opening_revenue,
                    )
                )
            if bal.opening_cost and bal.opening_cost != 0:
                summary.rows.append(
                    ConversionRow(
                        source_account_code=f"(aggregated → {bal.ledger_type})",
                        source_balance=bal.opening_cost,
                        target_ledger_type=bal.ledger_type,
                        target_ledger_label=label,
                        converted_amount=bal.opening_cost,
                    )
                )
            if bal.opening_vat and bal.opening_vat != 0:
                summary.rows.append(
                    ConversionRow(
                        source_account_code=f"(aggregated → {bal.ledger_type})",
                        source_balance=bal.opening_vat,
                        target_ledger_type=bal.ledger_type,
                        target_ledger_label=label,
                        converted_amount=bal.opening_vat,
                    )
                )

        return summary
