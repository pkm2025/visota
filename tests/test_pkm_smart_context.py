"""Tests for the PKM smart-context enrichment (VAL-CTX-004).

Verifies that :func:`apps.pkm.services.interaction_service.get_context_summary`
produces a Vietnamese natural-language summary that includes:

  - Recent business activities (voucher_create, invoice_create, ...) with
    amounts when available.
  - The current module inferred from the most recent page_view.
  - The user's role within the company.
  - Grouped page-view counts by module.

Also verifies that :func:`apps.pkm.services.qa_service.answer_question`
injects the enriched context summary into the prompt so the LLM can
personalise its answer.

Fulfills:
  - VAL-CTX-004: Smart context includes business activities
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.identity.models import Role, User, UserCompanyRole
from apps.pkm.models import UserInteractionLog
from apps.pkm.services.interaction_service import (
    _format_business_events_vn,
    _format_vnd,
    get_context_summary,
    log_interaction,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _force_sync():
    """Patch django-q detection so log_interaction writes synchronously."""
    return patch(
        "apps.pkm.services.interaction_service._django_q_available",
        return_value=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="SC_TX04",
        name="Smart Context Test Co",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="sc_user",
        password="Test1234",
        email="sc@t.co",
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(
        code="SC_OC04",
        name="Smart Context Other Co",
        tax_code="0209876543",
        accounting_regime="tt133",
    )


@pytest.fixture
def accountant_role(db, company):
    """Create an accountant role scoped to the company."""
    return Role.objects.create(
        company=company,
        code="accountant",
        name="Kế toán viên",
        is_system=False,
    )


@pytest.fixture
def user_with_role(db, user, company, accountant_role):
    """Assign the accountant role to the user within the company."""
    UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=accountant_role,
        is_default=True,
    )
    return user


# ---------------------------------------------------------------------------
# _format_vnd unit tests
# ---------------------------------------------------------------------------


def test_format_vnd_integer():
    """_format_vnd formats integers with Vietnamese thousands separators."""
    assert _format_vnd(50000000) == "50.000.000"


def test_format_vnd_decimal_string():
    """_format_vnd accepts numeric strings (as stored in metadata)."""
    assert _format_vnd("1000000") == "1.000.000"


def test_format_vnd_decimal_type():
    """_format_vnd accepts Decimal values from business services."""
    assert _format_vnd(Decimal("50000000")) == "50.000.000"


def test_format_vnd_small_value():
    """_format_vnd handles small values without separators."""
    assert _format_vnd(500) == "500"


def test_format_vnd_invalid_fallback():
    """_format_vnd falls back to str() for non-numeric values."""
    assert _format_vnd("not-a-number") == "not-a-number"


# ---------------------------------------------------------------------------
# VAL-CTX-004: get_context_summary includes business activities
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_includes_voucher_create_activity(company, user):
    """VAL-CTX-004: voucher_create events appear in the summary in Vietnamese."""
    with _force_sync():
        log_interaction(
            user=user,
            company=company,
            interaction_type="voucher_create",
            module="ledger",
            entity_type="voucher",
            entity_id="PT001",
            metadata={"amount": "50000000"},
        )

    summary = get_context_summary(user, company, hours=24)
    assert isinstance(summary, str)
    # The summary mentions the voucher activity in Vietnamese
    assert "phiếu" in summary.lower() or "phieu" in summary.lower()
    # The entity id is referenced
    assert "PT001" in summary
    # The amount is rendered with Vietnamese thousands separators
    assert "50.000.000" in summary
    assert "VND" in summary


@pytest.mark.django_db
def test_summary_includes_invoice_create_activity(company, user):
    """VAL-CTX-004: invoice_create events appear in the summary with amounts."""
    with _force_sync():
        log_interaction(
            user=user,
            company=company,
            interaction_type="invoice_create",
            module="sales",
            entity_type="sales_invoice",
            entity_id="SI001",
            metadata={"total_amount": "11000000"},
        )

    summary = get_context_summary(user, company, hours=24)
    assert "hóa đơn" in summary.lower() or "hoa don" in summary.lower()
    assert "SI001" in summary
    assert "11.000.000" in summary


@pytest.mark.django_db
def test_summary_includes_multiple_business_events(company, user):
    """Multiple business events are all rendered in the summary."""
    with _force_sync():
        log_interaction(
            user=user,
            company=company,
            interaction_type="voucher_create",
            module="ledger",
            entity_type="voucher",
            entity_id="V01",
            metadata={"amount": "1000"},
        )
        log_interaction(
            user=user,
            company=company,
            interaction_type="invoice_create",
            module="sales",
            entity_type="sales_invoice",
            entity_id="I01",
            metadata={"total_amount": "2000"},
        )
        log_interaction(
            user=user,
            company=company,
            interaction_type="einvoice_issue",
            module="einvoice",
            entity_type="einvoice",
            entity_id="E01",
            metadata={"total_amount": "3000"},
        )

    summary = get_context_summary(user, company, hours=24)
    # All three entity ids appear
    assert "V01" in summary
    assert "I01" in summary
    assert "E01" in summary
    # The summary is in Vietnamese (mentions "hoat dong nghiep vu" or similar)
    assert "nghiệp vụ" in summary.lower() or "nghiep vu" in summary.lower()


@pytest.mark.django_db
def test_summary_includes_business_event_without_amount(company, user):
    """Business events without an amount are rendered without the amount clause."""
    with _force_sync():
        log_interaction(
            user=user,
            company=company,
            interaction_type="period_close",
            module="ledger",
            entity_type="period",
            entity_id="2026-06",
            metadata={"fiscal_year": 2026, "period": 6},
        )

    summary = get_context_summary(user, company, hours=24)
    # The period close activity is mentioned
    assert "khóa sổ" in summary.lower() or "khoa so" in summary.lower()
    assert "2026-06" in summary
    # No VND amount clause since no amount key is present
    assert "VND" not in summary


# ---------------------------------------------------------------------------
# Current module detection from page_view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_includes_current_module_from_page_view(company, user):
    """The summary includes the current module inferred from the latest page view."""
    with _force_sync():
        log_interaction(user, company, "page_view", "ledger")
        log_interaction(user, company, "page_view", "sales")

    summary = get_context_summary(user, company, hours=24)
    # The most recent page view is "sales" → Vietnamese label "Bán hàng"
    assert "Bán hàng" in summary or "ban hang" in summary.lower()
    # "Đang ở module" is the prefix for the current-module line
    assert "Đang ở module" in summary or "module" in summary.lower()


@pytest.mark.django_db
def test_summary_current_module_uses_vietnamese_label(company, user):
    """Current-module labels come from the Vietnamese label map."""
    with _force_sync():
        log_interaction(user, company, "page_view", "ledger")

    summary = get_context_summary(user, company, hours=24)
    assert "Kế toán" in summary


@pytest.mark.django_db
def test_summary_includes_grouped_page_views_by_module(company, user):
    """Page views are grouped by module with Vietnamese labels."""
    with _force_sync():
        for _ in range(3):
            log_interaction(user, company, "page_view", "ledger")
        for _ in range(2):
            log_interaction(user, company, "page_view", "pkm")

    summary = get_context_summary(user, company, hours=24)
    # Vietnamese module labels appear with counts
    assert "3" in summary
    assert "2" in summary
    assert "Kế toán" in summary
    assert "Quản lý tri thức" in summary or "tri thức" in summary.lower()


# ---------------------------------------------------------------------------
# User role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_includes_user_role(company, user_with_role):
    """The summary includes the user's role within the company."""
    summary = get_context_summary(user_with_role, company, hours=24)
    assert "Vai trò:" in summary
    assert "Kế toán viên" in summary


@pytest.mark.django_db
def test_summary_without_role_still_works(company, user):
    """When the user has no role assignment, the summary omits the role line gracefully."""
    with _force_sync():
        log_interaction(user, company, "page_view", "ledger")

    summary = get_context_summary(user, company, hours=24)
    # Role line is absent but the summary is still valid
    assert "Vai trò:" not in summary
    assert "Kế toán" in summary  # module label still present


# ---------------------------------------------------------------------------
# Vietnamese natural-language formatting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_is_vietnamese_natural_language(company, user):
    """The summary is formatted as Vietnamese natural language (not English)."""
    with _force_sync():
        log_interaction(user, company, "page_view", "ledger")
        log_interaction(
            user,
            company,
            "voucher_create",
            "ledger",
            entity_type="voucher",
            entity_id="V01",
            metadata={"amount": "1000"},
        )

    summary = get_context_summary(user, company, hours=24)
    # Vietnamese diacritics or ASCII Vietnamese present
    vn_markers = ["Kế toán", "hoạt động", "nghiệp vụ", "trang", "module", "Đang ở"]
    assert any(marker in summary for marker in vn_markers)


@pytest.mark.django_db
def test_summary_empty_returns_vietnamese_message(company, user):
    """The no-activity message is in Vietnamese."""
    summary = get_context_summary(user, company, hours=24)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert (
        "không có hoạt động" in summary.lower()
        or "chưa có hoạt động" in summary.lower()
        or "khong co hoat dong" in summary.lower()
    )


# ---------------------------------------------------------------------------
# Time window scoping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_excludes_old_business_events(company, user):
    """Business events outside the time window are excluded from the summary."""
    from django.utils import timezone

    old_event = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="voucher_create",
        module="ledger",
        entity_type="voucher",
        entity_id="OLD01",
        metadata={"amount": "9999"},
    )
    old_event.created_at = timezone.now() - datetime.timedelta(hours=48)
    old_event.save(update_fields=["created_at"])

    summary = get_context_summary(user, company, hours=24)
    # The old entity id must not appear
    assert "OLD01" not in summary
    # The summary reports no recent activity
    assert (
        "không có hoạt động" in summary.lower()
        or "chưa có hoạt động" in summary.lower()
        or "khong co hoat dong" in summary.lower()
    )


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_user_isolation(company, user):
    """Another user's business events do not appear in this user's summary."""
    other = User.objects.create_user(username="sc_other", password="Test1234", email="o@t.co")
    with _force_sync():
        log_interaction(
            user,
            company,
            "voucher_create",
            "ledger",
            entity_type="voucher",
            entity_id="MINE",
            metadata={"amount": "100"},
        )
        log_interaction(
            other,
            company,
            "voucher_create",
            "ledger",
            entity_type="voucher",
            entity_id="THEIRS",
            metadata={"amount": "200"},
        )

    summary = get_context_summary(user, company, hours=24)
    assert "MINE" in summary
    assert "THEIRS" not in summary


@pytest.mark.django_db
def test_summary_company_isolation(user, company, other_company):
    """Business events from another company do not leak into the summary."""
    with _force_sync():
        log_interaction(
            user,
            company,
            "voucher_create",
            "ledger",
            entity_type="voucher",
            entity_id="CO_A",
            metadata={"amount": "100"},
        )
        log_interaction(
            user,
            other_company,
            "voucher_create",
            "ledger",
            entity_type="voucher",
            entity_id="CO_B",
            metadata={"amount": "200"},
        )

    summary = get_context_summary(user, company, hours=24)
    assert "CO_A" in summary
    assert "CO_B" not in summary


# ---------------------------------------------------------------------------
# _format_business_events_vn unit test
# ---------------------------------------------------------------------------


def test_format_business_events_vn_empty():
    """_format_business_events_vn returns None for an empty list."""
    assert _format_business_events_vn([]) is None


def test_format_business_events_vn_with_entries():
    """_format_business_events_vn renders entries with Vietnamese verbs + amounts."""
    event = UserInteractionLog(
        interaction_type="voucher_create",
        module="ledger",
        entity_type="voucher",
        entity_id="PT001",
        metadata={"amount": "50000000"},
    )
    result = _format_business_events_vn([event])
    assert result is not None
    assert "phiếu" in result.lower() or "phieu" in result.lower()
    assert "PT001" in result
    assert "50.000.000" in result
    assert "VND" in result


# ---------------------------------------------------------------------------
# Q&A service injects enriched context (VAL-CTX-004 integration)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_qa_answer_injects_business_activity_context(company, user_with_role):
    """answer_question injects the enriched context summary into the prompt."""
    from types import SimpleNamespace

    from apps.pkm.models import UserLLMConfig
    from apps.pkm.services.encryption_service import encrypt
    from apps.pkm.services.qa_service import answer_question

    UserLLMConfig.objects.create(
        user=user_with_role,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )

    # Log a business event so the context summary mentions it
    with _force_sync():
        log_interaction(
            user=user_with_role,
            company=company,
            interaction_type="voucher_create",
            module="ledger",
            entity_type="voucher",
            entity_id="PTCTX01",
            metadata={"amount": "75000000"},
        )

    mock_embed = SimpleNamespace(data=[SimpleNamespace(embedding=[0.01] * 1536)])
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Mocked answer."))]
    )

    with (
        patch("apps.pkm.services.qa_service.get_embedding", return_value=mock_embed),
        patch(
            "apps.pkm.services.qa_service.get_completion",
            return_value=mock_completion,
        ) as mock_gc,
        patch("apps.pkm.services.qa_service.search_similar", return_value=[]),
    ):
        result = answer_question(user_with_role, company, "Tôi vừa làm gì?")

    # The result exposes the interaction context summary
    assert "interaction_context" in result
    ctx = result["interaction_context"]
    assert "PTCTX01" in ctx
    assert "75.000.000" in ctx

    # The LLM call received messages that contain the business activity context
    messages = mock_gc.call_args[0][1]
    user_msg = messages[1]["content"]
    assert "PTCTX01" in user_msg
    assert "75.000.000" in user_msg
    # The system message references the activity-context section
    system_msg = messages[0]["content"]
    assert (
        "HOAT DONG NGUOI DUNG" in system_msg.upper() or "hoat dong nguoi dung" in system_msg.lower()
    )
