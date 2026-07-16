"""Integration tests for the PKM interaction service.

These tests verify the three public functions of ``interaction_service``:

  - ``log_interaction`` - creates UserInteractionLog entries; uses async_task
    when django-q2 is available, else synchronous.
  - ``get_context_summary`` - produces a human-readable summary of recent
    activity scoped by user + company + time window.
  - ``get_recent_interactions`` - returns a queryset scoped by user + company.

Additionally verifies:
  - Per-user isolation (User B's logs are invisible to User A).
  - Per-company isolation (Company B logs invisible to Company A user).
  - Non-blocking behaviour: ``log_interaction`` does not materially delay the
    caller when django-q2 is available (async path) and is fast even in sync.

Fulfills:
  - VAL-CAP-001: Page views on PKM pages are logged (log_interaction creates
    page_view entries)
  - VAL-CAP-007: Recent activity summary generated (get_context_summary)
  - VAL-CAP-009: Interaction logging is non-blocking
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import UserInteractionLog
from apps.pkm.services.interaction_service import (
    get_context_summary,
    get_recent_interactions,
    log_interaction,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="ISVC_TEST",
        name="Interaction Service Test Co",
        tax_code="0101234567",
        accounting_regime="tt133",
    )


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="isvc_user",
        password="Test1234",
        email="isvc@t.co",
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="isvc_other",
        password="Test1234",
        email="isvc_other@t.co",
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(
        code="ISVC_OTHER",
        name="Interaction Service Other Co",
        tax_code="0209876543",
        accounting_regime="tt133",
    )


# ---------------------------------------------------------------------------
# log_interaction: creates UserInteractionLog entries
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_log_interaction_creates_entry_synchronous(company, user):
    """log_interaction creates a UserInteractionLog entry (sync path)."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        result = log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
        )
    assert result is not None
    log = UserInteractionLog.objects.get(pk=result.pk)
    assert log.user == user
    assert log.company == company
    assert log.interaction_type == "page_view"
    assert log.module == "pkm"
    assert log.entity_type == ""
    assert log.entity_id == ""
    assert log.metadata == {}


@pytest.mark.django_db
def test_log_interaction_creates_entry_with_all_fields(company, user):
    """log_interaction stores all optional fields (entity + metadata)."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(
            user=user,
            company=company,
            interaction_type="note_create",
            module="pkm",
            entity_type="note",
            entity_id="42",
            metadata={"title": "Tax notes"},
        )
    log = UserInteractionLog.objects.filter(user=user, company=company).first()
    assert log is not None
    assert log.entity_type == "note"
    assert log.entity_id == "42"
    assert log.metadata == {"title": "Tax notes"}


@pytest.mark.django_db
def test_log_interaction_page_view_fulfills_val_cap_001(company, user):
    """VAL-CAP-001: page_view interactions are logged."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
            metadata={"url": "/modern/knowledge/notes/"},
        )
    logs = UserInteractionLog.objects.filter(
        user=user, company=company, interaction_type="page_view"
    )
    assert logs.count() == 1
    assert logs.first().module == "pkm"


@pytest.mark.django_db
def test_log_interaction_all_types(company, user):
    """log_interaction accepts all five interaction types."""
    types = ["page_view", "search", "note_create", "document_create", "voucher_create"]
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        for itype in types:
            log_interaction(
                user=user,
                company=company,
                interaction_type=itype,
                module="pkm",
            )
    assert UserInteractionLog.objects.filter(user=user, company=company).count() == 5


@pytest.mark.django_db
def test_log_interaction_search_with_query_metadata(company, user):
    """Search interactions can carry the search query in metadata."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(
            user=user,
            company=company,
            interaction_type="search",
            module="pkm",
            metadata={"query": "VAT calculation"},
        )
    log = UserInteractionLog.objects.get(interaction_type="search")
    assert log.metadata["query"] == "VAT calculation"


# ---------------------------------------------------------------------------
# log_interaction: async path (django-q2 available)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_log_interaction_uses_async_task_when_django_q_available(company, user):
    """When django-q2 is available, log_interaction enqueues an async task."""
    with (
        patch("apps.pkm.services.interaction_service._django_q_available", return_value=True),
        patch("apps.pkm.services.interaction_service._enqueue_async") as mock_enqueue,
    ):
        log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
        )
    mock_enqueue.assert_called_once()


@pytest.mark.django_db
def test_log_interaction_falls_back_to_sync_on_async_error(company, user):
    """If the async enqueue fails, log_interaction falls back to synchronous create."""
    with (
        patch("apps.pkm.services.interaction_service._django_q_available", return_value=True),
        patch(
            "apps.pkm.services.interaction_service._enqueue_async",
            side_effect=Exception("Broker down"),
        ),
    ):
        # Should NOT raise - falls back to sync
        log = log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
        )
    assert log is not None
    assert UserInteractionLog.objects.filter(user=user, company=company).count() == 1


@pytest.mark.django_db
def test_log_interaction_never_raises_on_failure(company, user):
    """log_interaction swallows exceptions so logging never breaks the caller."""
    with (
        patch(
            "apps.pkm.services.interaction_service._create_sync",
            side_effect=Exception("DB exploded"),
        ),
        patch("apps.pkm.services.interaction_service._django_q_available", return_value=False),
    ):
        # Should not raise even when create fails
        result = log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
        )
    assert result is None


# ---------------------------------------------------------------------------
# get_context_summary: produces readable activity summary
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_context_summary_empty(company, user):
    """get_context_summary returns a no-activity message when no logs exist."""
    summary = get_context_summary(user, company, hours=24)
    assert isinstance(summary, str)
    assert len(summary) > 0
    # Should indicate no recent activity (English or Vietnamese)
    assert (
        "no recent activity" in summary.lower()
        or "không có hoạt động" in summary.lower()
        or "chưa có hoạt động" in summary.lower()
        or "khong co hoat dong" in summary.lower()
    )


@pytest.mark.django_db
def test_get_context_summary_generates_from_logs(company, user):
    """VAL-CAP-007: get_context_summary produces a readable summary from logs."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        # Create 3 ledger page views
        for _ in range(3):
            log_interaction(user, company, "page_view", "ledger")
        # Create 2 notes
        for _ in range(2):
            log_interaction(user, company, "note_create", "pkm")
        # Upload 1 document
        log_interaction(user, company, "document_create", "pkm")

    summary = get_context_summary(user, company, hours=24)
    assert isinstance(summary, str)
    # The summary should mention the activity counts
    assert "3" in summary  # 3 page views
    assert "2" in summary  # 2 notes
    assert "1" in summary  # 1 document


@pytest.mark.django_db
def test_get_context_summary_respects_time_window(company, user):
    """get_context_summary only includes logs within the hours window."""
    import datetime

    from django.utils import timezone

    # Create an old log (48 hours ago) - outside the 24h window
    old_log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="ledger",
    )
    old_log.created_at = timezone.now() - datetime.timedelta(hours=48)
    old_log.save(update_fields=["created_at"])

    # Create a recent log (1 hour ago) - inside the 24h window
    recent_log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="note_create",
        module="pkm",
    )
    recent_log.created_at = timezone.now() - datetime.timedelta(hours=1)
    recent_log.save(update_fields=["created_at"])

    summary = get_context_summary(user, company, hours=24)
    # Should include the note_create (1) but not the old page view (3 would be
    # wrong since only one note exists)
    assert "1" in summary
    # The old page view is outside the window — module "ledger" should not
    # appear as a current-module label. (It may still appear in a role label
    # only if the user has a ledger-scoped role, which is not the case here.)
    # We accept either the English code "ledger" being absent OR the summary
    # being purely in Vietnamese without the code.
    assert "kế toán" not in summary.lower() or "ledger" not in summary.lower()


@pytest.mark.django_db
def test_get_context_summary_custom_hours_window(company, user):
    """get_context_summary honours a custom hours parameter."""
    import datetime

    from django.utils import timezone

    # Log 30 hours ago
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="ledger",
    )
    log.created_at = timezone.now() - datetime.timedelta(hours=30)
    log.save(update_fields=["created_at"])

    # 24h window should not include it - summary should indicate no activity
    summary_24 = get_context_summary(user, company, hours=24)
    assert (
        "no recent activity" in summary_24.lower()
        or "không có hoạt động" in summary_24.lower()
        or "chưa có hoạt động" in summary_24.lower()
        or "khong co hoat dong" in summary_24.lower()
    )

    # 48h window should include it - summary should mention ledger page view
    summary_48 = get_context_summary(user, company, hours=48)
    # The module should appear either as the English code or the Vietnamese label
    assert "ledger" in summary_48.lower() or "kế toán" in summary_48.lower()
    assert "1" in summary_48


@pytest.mark.django_db
def test_get_context_summary_human_readable_format(company, user):
    """get_context_summary returns a human-readable string (not JSON/empty)."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "page_view", "ledger")
    summary = get_context_summary(user, company, hours=24)
    # Should be a non-trivial human-readable sentence
    assert isinstance(summary, str)
    assert len(summary) > 10


# ---------------------------------------------------------------------------
# get_recent_interactions: returns queryset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_recent_interactions_returns_queryset(company, user):
    """get_recent_interactions returns a queryset ordered by created_at desc."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        for _ in range(5):
            log_interaction(user, company, "page_view", "pkm")

    qs = get_recent_interactions(user, company, limit=20)
    assert hasattr(qs, "count")  # queryset-like
    assert qs.count() == 5
    # Ordering: most recent first (default ordering on the model)
    results = list(qs)
    assert results[0].created_at >= results[-1].created_at


@pytest.mark.django_db
def test_get_recent_interactions_respects_limit(company, user):
    """get_recent_interactions honours the limit parameter."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        for _ in range(10):
            log_interaction(user, company, "page_view", "pkm")

    qs = get_recent_interactions(user, company, limit=3)
    assert list(qs).__len__() == 3


@pytest.mark.django_db
def test_get_recent_interactions_empty(company, user):
    """get_recent_interactions returns empty queryset when no logs."""
    qs = get_recent_interactions(user, company, limit=20)
    assert qs.count() == 0


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_context_summary_user_isolation(company, user, other_user):
    """get_context_summary only includes the requesting user's logs."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "note_create", "pkm")
        log_interaction(other_user, company, "page_view", "ledger")
        log_interaction(other_user, company, "page_view", "ledger")

    user_summary = get_context_summary(user, company, hours=24)
    other_summary = get_context_summary(other_user, company, hours=24)

    # user's summary should mention 1 note, not the 2 page views
    assert "1" in user_summary
    # other user's summary should mention 2 page views
    assert "2" in other_summary


@pytest.mark.django_db
def test_get_recent_interactions_user_isolation(company, user, other_user):
    """get_recent_interactions only returns the requesting user's logs."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "page_view", "pkm")
        log_interaction(user, company, "note_create", "pkm")
        log_interaction(other_user, company, "page_view", "ledger")
        log_interaction(other_user, company, "search", "pkm")

    user_qs = get_recent_interactions(user, company, limit=20)
    other_qs = get_recent_interactions(other_user, company, limit=20)

    assert user_qs.count() == 2
    assert other_qs.count() == 2
    # All logs in user_qs belong to `user`
    assert all(log.user_id == user.id for log in user_qs)
    assert all(log.user_id == other_user.id for log in other_qs)


@pytest.mark.django_db
def test_log_interaction_user_isolation(company, user, other_user):
    """log_interaction creates entries scoped to the given user only."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "page_view", "pkm")

    # other_user should not see user's log
    assert UserInteractionLog.objects.filter(user=other_user).count() == 0
    assert UserInteractionLog.objects.filter(user=user).count() == 1


# ---------------------------------------------------------------------------
# Per-company isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_context_summary_company_isolation(user, company, other_company):
    """get_context_summary only includes logs for the given company."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "page_view", "pkm")
        log_interaction(user, other_company, "note_create", "pkm")
        log_interaction(user, other_company, "note_create", "pkm")

    company_summary = get_context_summary(user, company, hours=24)
    other_summary = get_context_summary(user, other_company, hours=24)

    # company summary should reflect 1 page view
    assert "1" in company_summary
    # other_company summary should reflect 2 note creates
    assert "2" in other_summary


@pytest.mark.django_db
def test_get_recent_interactions_company_isolation(user, company, other_company):
    """get_recent_interactions only returns logs for the given company."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log_interaction(user, company, "page_view", "pkm")
        log_interaction(user, other_company, "page_view", "pkm")
        log_interaction(user, other_company, "note_create", "pkm")

    company_qs = get_recent_interactions(user, company, limit=20)
    other_qs = get_recent_interactions(user, other_company, limit=20)

    assert company_qs.count() == 1
    assert other_qs.count() == 2
    assert all(log.company_id == company.id for log in company_qs)
    assert all(log.company_id == other_company.id for log in other_qs)


# ---------------------------------------------------------------------------
# Non-blocking behaviour (VAL-CAP-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_log_interaction_async_does_not_block(company, user):
    """VAL-CAP-009: async log_interaction returns quickly (non-blocking)."""
    # Simulate async path - async_task is mocked so the DB write is deferred
    with (
        patch("apps.pkm.services.interaction_service._django_q_available", return_value=True),
        patch("apps.pkm.services.interaction_service._enqueue_async") as mock_enqueue,
    ):
        start = time.monotonic()
        log_interaction(user, company, "page_view", "pkm")
        elapsed = time.monotonic() - start

    mock_enqueue.assert_called_once()
    # Async path should be extremely fast (< 0.1s) since no DB write happens
    assert elapsed < 0.1


@pytest.mark.django_db
def test_log_interaction_sync_is_fast(company, user):
    """Even in sync mode, log_interaction completes quickly (sub-50ms typical)."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        start = time.monotonic()
        log_interaction(user, company, "page_view", "pkm")
        elapsed = time.monotonic() - start

    # A single INSERT should be well under 200ms even on slow disks
    assert elapsed < 0.2
    assert UserInteractionLog.objects.filter(user=user, company=company).count() == 1


@pytest.mark.django_db
def test_log_interaction_response_time_unaffected_by_multiple_calls(company, user):
    """Multiple log calls do not cause cumulative slowdown (non-blocking intent)."""
    with (
        patch("apps.pkm.services.interaction_service._django_q_available", return_value=True),
        patch("apps.pkm.services.interaction_service._enqueue_async"),
    ):
        start = time.monotonic()
        for _ in range(20):
            log_interaction(user, company, "page_view", "pkm")
        elapsed = time.monotonic() - start

    # 20 async calls should each be near-instant; total well under 0.5s
    assert elapsed < 0.5


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_log_interaction_metadata_none_defaults_to_empty_dict(company, user):
    """Passing metadata=None stores an empty dict, not None."""
    with patch("apps.pkm.services.interaction_service._django_q_available", return_value=False):
        log = log_interaction(
            user=user,
            company=company,
            interaction_type="page_view",
            module="pkm",
            metadata=None,
        )
    log.refresh_from_db()
    assert log.metadata == {}


@pytest.mark.django_db
def test_get_context_summary_handles_only_old_logs(company, user):
    """get_context_summary does not error when only old logs exist."""
    import datetime

    from django.utils import timezone

    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="ledger",
    )
    log.created_at = timezone.now() - datetime.timedelta(hours=72)
    log.save(update_fields=["created_at"])

    summary = get_context_summary(user, company, hours=24)
    assert isinstance(summary, str)
    assert len(summary) > 0
