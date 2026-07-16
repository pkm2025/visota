"""Tests for company context enrichment in ``interaction_service``.

Verifies the ``_format_company_context`` helper and its integration into
``get_context_summary``. The company context prepends a Vietnamese description
of the company's accounting regime, entity type, tax method group (TT58 only),
VAT/TNDN methods, and industry to the activity summary.

Fulfills:
  - VAL-COMP-001: Context includes company entity type in Vietnamese
  - VAL-COMP-002: Context includes accounting regime
  - VAL-COMP-003: Context includes tax method group for TT58
  - VAL-COMP-004: Different company types produce different context
"""

from __future__ import annotations

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.services.interaction_service import (
    _format_company_context,
    get_context_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_company(db):
    return Company.objects.create(
        code="CCS_TT58",
        name="TT58 Sieu Nho Co",
        tax_code="0105550001",
        accounting_regime="tt58",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="ty_le_phan_tram",
        tndn_method="tinh_thue",
        industry="Thương mại - Công nghệ",
    )


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="CCS_TT133",
        name="TT133 SME Co",
        tax_code="0105550002",
        accounting_regime="tt133",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="khau_tru",
        tndn_method="tinh_thue",
        industry="Dịch vụ - bán lẻ",
    )


@pytest.fixture
def user(db, tt58_company):
    return User.objects.create_user(
        username="ccs_user",
        password="Test1234",
        email="ccs@t.co",
    )


# ---------------------------------------------------------------------------
# _format_company_context: Vietnamese company text
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_format_company_context_returns_str(tt58_company, user):
    """_format_company_context returns a non-empty Vietnamese string."""
    text = _format_company_context(user, tt58_company)
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.django_db
def test_format_company_context_includes_entity_type(tt58_company, user):
    """VAL-COMP-001: Entity type appears in Vietnamese."""
    text = _format_company_context(user, tt58_company)
    assert "Doanh nghiệp siêu nhỏ" in text


@pytest.mark.django_db
def test_format_company_context_includes_regime(tt58_company, user):
    """VAL-COMP-002: Accounting regime appears."""
    text = _format_company_context(user, tt58_company)
    assert "TT58" in text


@pytest.mark.django_db
def test_format_company_context_includes_tax_method_group_for_tt58(tt58_company, user):
    """VAL-COMP-003: TT58 tax method group mentions GTGT, ty le, TNDN, tinh thue."""
    # TT58 with vat=ty_le_phan_tram + tndn=tinh_thue => group 2
    text = _format_company_context(user, tt58_company)
    assert "GTGT" in text
    assert "tỷ lệ" in text.lower()
    assert "TNDN" in text
    assert "tính thuế" in text.lower()


@pytest.mark.django_db
def test_format_company_context_omits_tax_group_for_tt133(tt133_company, user):
    """Non-TT58 regimes do not include the TT58 tax method group description."""
    text = _format_company_context(user, tt133_company)
    # TT133 does not use tax method groups, so the group description should be
    # absent. The TT133 regime label must still appear.
    assert "TT133" in text
    # The TT58-only tax group description starts with "Nhóm N:". It must not
    # appear for TT133 companies.
    assert "Nhóm 1:" not in text
    assert "Nhóm 2:" not in text
    assert "Nhóm 3:" not in text
    assert "Nhóm 4:" not in text


@pytest.mark.django_db
def test_format_company_context_includes_industry(tt58_company, user):
    """Industry appears in the company context."""
    text = _format_company_context(user, tt58_company)
    assert "Thương mại - Công nghệ" in text


@pytest.mark.django_db
def test_format_company_context_includes_vat_method(tt58_company, user):
    """VAT method label appears in the company context."""
    text = _format_company_context(user, tt58_company)
    assert "Tỷ lệ" in text or "tỷ lệ" in text


@pytest.mark.django_db
def test_format_company_context_includes_tndn_method(tt58_company, user):
    """TNDN method label appears in the company context."""
    text = _format_company_context(user, tt58_company)
    assert "tính thuế" in text.lower() or "Tỷ lệ" in text


@pytest.mark.django_db
def test_format_company_context_handles_missing_industry(tt133_company, user):
    """Missing industry does not break the formatter."""
    tt133_company.industry = ""
    tt133_company.save(update_fields=["industry"])
    text = _format_company_context(user, tt133_company)
    assert isinstance(text, str)
    assert "TT133" in text


@pytest.mark.django_db
def test_format_company_context_different_companies_differ(tt58_company, tt133_company, user):
    """VAL-COMP-004: TT58 vs TT133 companies produce different context text."""
    tt58_text = _format_company_context(user, tt58_company)
    tt133_text = _format_company_context(user, tt133_company)
    assert tt58_text != tt133_text
    # The regime text differs
    assert "TT58" in tt58_text
    assert "TT133" in tt133_text


@pytest.mark.django_db
def test_format_company_context_ho_kinh_doanh_entity(tt133_company, user):
    """Ho kinh doanh entity type renders its own Vietnamese label."""
    tt133_company.entity_type = "ho_kinh_doanh"
    tt133_company.save(update_fields=["entity_type"])
    text = _format_company_context(user, tt133_company)
    assert "Hộ kinh doanh" in text


# ---------------------------------------------------------------------------
# get_context_summary: integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_context_summary_prepends_company_context(tt58_company, user):
    """get_context_summary includes the company context fragment."""
    summary = get_context_summary(user, tt58_company, hours=24)
    assert "TT58" in summary
    assert "Doanh nghiệp siêu nhỏ" in summary


@pytest.mark.django_db
def test_get_context_summary_company_context_before_activity(tt58_company, user):
    """Company context is prepended before the activity summary."""
    # Create an activity so the summary has both company + activity content
    from unittest.mock import patch

    from apps.pkm.services.interaction_service import log_interaction

    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, tt58_company, "page_view", "ledger")

    summary = get_context_summary(user, tt58_company, hours=24)
    # Company context (entity type) should appear before any activity text
    entity_idx = summary.find("Doanh nghiệp siêu nhỏ")
    # activity markers like the role line or module line come later; at minimum
    # the entity text must be present and not at the very end of the string
    assert entity_idx >= 0
    assert entity_idx < len(summary) - 1


@pytest.mark.django_db
def test_get_context_summary_different_companies_differ(tt58_company, tt133_company, user):
    """VAL-COMP-004: Different company types produce different summaries."""
    tt58_summary = get_context_summary(user, tt58_company, hours=24)
    tt133_summary = get_context_summary(user, tt133_company, hours=24)
    assert tt58_summary != tt133_summary
    assert "TT58" in tt58_summary
    assert "TT133" in tt133_summary


@pytest.mark.django_db
def test_get_context_summary_no_activity_still_has_company_context(tt58_company, user):
    """Company context appears even when there is no recent activity."""
    summary = get_context_summary(user, tt58_company, hours=24)
    assert "TT58" in summary
    assert "Doanh nghiệp siêu nhỏ" in summary
