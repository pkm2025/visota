"""Compliance tests for legal references and data hygiene (feature fix-legal-references).

Covers:
- VAL-LEGAL-001: Bidding law number corrected to 22/2023/QH15
- VAL-LEGAL-002: All 8+ new regulations seeded in LegalReference
- VAL-LEGAL-003: Luat TNDN cites 67/2025/QH15 as primary
- VAL-LEGAL-004: QD48 marked as deprecated
"""

import io
import pathlib

import pytest

from apps.core.models import Company, LegalReference

BIDDING_MODELS_PATH = pathlib.Path("apps/bidding/models.py")
BIDDING_APPS_PATH = pathlib.Path("apps/bidding/apps.py")

# Regulations that MUST be present in seed_legal_references output.
REQUIRED_NEW_REGULATIONS = [
    ("ND254_2026", "254/2026"),  # ND 254/2026 - E-invoice framework
    ("TT91_2026", "91/2026"),  # TT 91/2026 - E-invoice guidance
    ("LuatQLT108_2025", "108/2025"),  # Luat Quản lý thuế 108/2025
    ("ND161_2026", "161/2026"),  # ND 161/2026 - BHXH base salary
    ("ND253_2026", "253/2026"),  # ND 253/2026 - PIT allowances
    ("TT87_2026", "87/2026"),  # TT 87/2026 - PIT allowances guidance
    ("ND141_2026", "141/2026"),  # ND 141/2026 - CIT exemption for <=1B revenue
    ("ND293_2025", "293/2025"),  # ND 293/2025 - Minimum wage 2026
    ("TT50_2026", "50/2026"),  # TT 50/2026 - HKD e-invoice
]


# --- VAL-LEGAL-001: Bidding law number ---


def test_bidding_models_docstring_cites_22_2023_qh15():
    """The bidding models.py docstring must cite 22/2023/QH15 (not 23/2023)."""
    text = BIDDING_MODELS_PATH.read_text(encoding="utf-8")
    assert "22/2023/QH15" in text
    assert "23/2023" not in text


def test_bidding_apps_docstring_cites_22_2023_qh15():
    """The bidding apps.py docstring must cite 22/2023/QH15 (not 23/2023)."""
    text = BIDDING_APPS_PATH.read_text(encoding="utf-8")
    assert "22/2023/QH15" in text
    assert "23/2023" not in text


def test_no_23_2023_in_bidding_app():
    """No file under apps/bidding/ should still reference the wrong 23/2023 number."""
    bidding_dir = pathlib.Path("apps/bidding")
    offenders = []
    for p in bidding_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "23/2023" in text:
            offenders.append(str(p))
    assert offenders == [], f"Files still referencing 23/2023: {offenders}"


# --- VAL-LEGAL-002: 9 new regulations seeded ---


@pytest.fixture
def seeded_legal_refs(db):
    from django.core.management import call_command

    out = io.StringIO()
    call_command("seed_legal_references", verbosity=0, stdout=out)
    return out.getvalue()


@pytest.mark.parametrize("label,fragment", REQUIRED_NEW_REGULATIONS)
def test_seed_includes_new_regulation(seeded_legal_refs, label, fragment):
    """Each required new regulation must be present in LegalReference after seeding.

    We search both by name/full_name (looking for the regulation number fragment)
    so the test is robust to the exact code chosen.
    """
    matches = LegalReference.objects.filter(
        name__contains=fragment,
    ) | LegalReference.objects.filter(
        full_name__contains=fragment,
    )
    assert matches.exists(), (
        f"No LegalReference found containing '{fragment}' (expected: {label}). "
        f"Seed output:\n{seeded_legal_refs}"
    )


def test_seed_includes_at_least_nine_new_regulations(seeded_legal_refs):
    """At minimum 9 of the new regulations must be present after seeding."""
    found = 0
    for _label, fragment in REQUIRED_NEW_REGULATIONS:
        qs = LegalReference.objects.filter(name__contains=fragment) | LegalReference.objects.filter(
            full_name__contains=fragment
        )
        if qs.exists():
            found += 1
    assert found >= 9, f"Only {found}/9 new regulations found after seeding."


def test_seed_is_idempotent(seeded_legal_refs):
    """Running the seed twice does not duplicate rows."""
    from django.core.management import call_command

    count_before = LegalReference.objects.count()
    call_command("seed_legal_references", verbosity=0)
    count_after = LegalReference.objects.count()
    assert count_before == count_after


# --- VAL-LEGAL-003: Luat TNDN cites 67/2025/QH15 as primary ---


def test_luat_tndn_primary_is_67_2025_qh15(seeded_legal_refs):
    """The primary Luat Thuế TNDN legal reference must cite 67/2025/QH15.

    The old 'LuatThueTNDN' entry (14/2008) must either be superseded or
    no longer be the primary active entry.
    """
    # The 67/2025/QH15 entry must exist and be active
    primary = LegalReference.objects.filter(
        full_name__contains="67/2025/QH15",
        status="active",
    ).first()
    assert primary is not None, (
        f"No active LegalReference citing 67/2025/QH15 found. Seed output:\n{seeded_legal_refs}"
    )
    # The old LuatThueTNDN (14/2008) must be marked superseded (not the primary)
    old = LegalReference.objects.filter(code="LuatThueTNDN").first()
    if old is not None:
        assert old.status in {"superseded", "repealed"}, (
            f"Old LuatThueTNDN status should be 'superseded' or 'repealed', got '{old.status}'."
        )
        assert old.replaced_by_id == primary.id, (
            "Old LuatThueTNDN must link replaced_by to the 67/2025/QH15 entry."
        )


# --- VAL-LEGAL-004: QD48 marked as deprecated ---


def test_q48_accounting_regime_deprecated():
    """The Q48 AccountingRegime choice must indicate it is deprecated."""
    q48 = Company.AccountingRegime.Q48
    label = q48.label
    lowered = label.lower()
    assert "cũ" in lowered or "deprecated" in lowered or "khuyến nghị" in lowered, (
        f"Q48 label should indicate deprecation, got: '{label}'"
    )
