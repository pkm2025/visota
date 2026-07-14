"""TT58 DNSN ledger type availability logic.

Maps tax method groups (1-4) to their applicable ledger types,
and manages optional S4 ledgers that can be independently enabled.

Ledger availability per TT58/2026/TT-BTC:
- Group 1 (GTGT% + TNDN%): S1 only
- Group 2 (GTGT% + TNDN tinh thue): S2a, S2b, S2c, S2d
- Group 3 (GTGT khau tru + TNDN%): S3a, S3b
- Group 4 (GTGT khau tru + TNDN tinh thue): S2b, S2c, S2d + S3b

Optional ledgers (off by default, can be enabled independently):
- S4a: Cong no (receivables/payables)
- S4b: Tai san co dinh (fixed assets)
- S4c: Thue khac (other taxes)
- S4d: Von CSH (owner's equity)
"""

# Ledger types required (non-optional) for each tax method group.
GROUP_LEDGER_MAP: dict[int, list[str]] = {
    1: ["s1"],
    2: ["s2a", "s2b", "s2c", "s2d"],
    3: ["s3a", "s3b"],
    4: ["s2b", "s2c", "s2d", "s3b"],
}

# Optional ledger types that can be independently enabled.
OPTIONAL_LEDGER_TYPES: list[str] = ["s4a", "s4b", "s4c", "s4d"]

# Human-readable labels and descriptions for all ledger types.
LEDGER_LABELS: dict[str, str] = {
    "s1": "S1-DNSN — Sổ doanh thu (Nhóm 1)",
    "s2a": "S2a-DNSN — Sổ doanh thu (Nhóm 2)",
    "s2b": "S2b-DNSN — Sổ chi tiết doanh thu, chi phí",
    "s2c": "S2c-DNSN — Sổ vật liệu, hàng hóa",
    "s2d": "S2d-DNSN — Sổ chi tiết tiền",
    "s3a": "S3a-DNSN — Sổ doanh thu (Nhóm 3)",
    "s3b": "S3b-DNSN — Sổ nghĩa vụ thuế GTGT",
    "s4a": "S4a-DNSN — Sổ công nợ (tùy chọn)",
    "s4b": "S4b-DNSN — Sổ TSCĐ (tùy chọn)",
    "s4c": "S4c-DNSN — Sổ thuế khác (tùy chọn)",
    "s4d": "S4d-DNSN — Sổ vốn CSH (tùy chọn)",
}

LEDGER_SHORT_LABELS: dict[str, str] = {
    "s1": "S1-DNSN",
    "s2a": "S2a-DNSN",
    "s2b": "S2b-DNSN",
    "s2c": "S2c-DNSN",
    "s2d": "S2d-DNSN",
    "s3a": "S3a-DNSN",
    "s3b": "S3b-DNSN",
    "s4a": "S4a-DNSN",
    "s4b": "S4b-DNSN",
    "s4c": "S4c-DNSN",
    "s4d": "S4d-DNSN",
}


def get_required_ledgers(tax_method_group: int) -> list[str]:
    """Return the list of required (non-optional) ledger types for a group."""
    return GROUP_LEDGER_MAP.get(tax_method_group, [])


def get_optional_ledger_defaults() -> dict[str, bool]:
    """Return the default enablement state for optional ledgers (all False)."""
    return dict.fromkeys(OPTIONAL_LEDGER_TYPES, False)


def get_available_ledgers(
    tax_method_group: int,
    enabled_optional: dict[str, bool] | None = None,
) -> list[str]:
    """Return all available ledger types for a company.

    Combines the required ledgers for the tax method group with
    any optional ledgers that have been explicitly enabled.
    """
    ledgers = list(get_required_ledgers(tax_method_group))
    if enabled_optional:
        for lt in OPTIONAL_LEDGER_TYPES:
            if enabled_optional.get(lt, False):
                ledgers.append(lt)
    return ledgers


def get_company_available_ledgers(company) -> list[str]:
    """Get all available ledgers for a company instance.

    Reads tax_method_group from the company and optional ledger
    enablement flags from the company's JSON field.
    """
    if company.accounting_regime != "tt58":
        return []
    group = company.tax_method_group
    enabled = company.dnsn_optional_ledgers or {}
    return get_available_ledgers(group, enabled)


def is_ledger_available(company, ledger_type: str) -> bool:
    """Check if a specific ledger type is available for a company."""
    return ledger_type in get_company_available_ledgers(company)


def get_ledger_label(ledger_type: str) -> str:
    """Get the human-readable label for a ledger type."""
    return LEDGER_LABELS.get(ledger_type, ledger_type.upper())


def get_ledger_short_label(ledger_type: str) -> str:
    """Get the short label for a ledger type."""
    return LEDGER_SHORT_LABELS.get(ledger_type, ledger_type.upper())


def get_all_ledger_choices() -> list[tuple[str, str]]:
    """Return (code, label) pairs for all ledger types (for forms)."""
    return list(LEDGER_LABELS.items())
