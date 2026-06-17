"""Tests for RecurringTemplate model + RecurringService."""


import pytest
from django.utils import timezone

from apps.core.models import Company
from apps.recurring.models import RecurringTemplate
from apps.recurring.services import RecurringService


@pytest.fixture
def setup(db):
    return Company.objects.create(code="TCO", name="Test Co")


def test_create_recurring_template(setup):
    company = setup
    tpl = RecurringTemplate.objects.create(
        company=company,
        name="Khấu hao TSCĐ",
        description="Tính khấu hao tháng",
        service_func="apps.recurring.runners:run_depreciation",
        schedule_type=RecurringTemplate.ScheduleType.MONTHLY,
        day_of_month=1,
        is_active=True,
    )
    tpl.refresh_from_db()
    assert tpl.id is not None
    assert tpl.schedule_type == "monthly"
    assert tpl.is_active is True


def test_run_one_executes_service_func(setup):
    company = setup
    tpl = RecurringTemplate.objects.create(
        company=company,
        name="Test runner",
        service_func="apps.recurring.runners:noop",
        schedule_type=RecurringTemplate.ScheduleType.MONTHLY,
        day_of_month=1,
        is_active=True,
    )
    svc = RecurringService()
    result = svc.run_one(tpl)
    assert result["status"] == "ok"
    tpl.refresh_from_db()
    assert tpl.last_run_at is not None
    assert tpl.last_run_result["result"] == {"status": "ok", "message": "noop"}
    assert tpl.next_run_at is not None


def test_run_all_due_skips_non_due(setup):
    company = setup
    # Future next_run_at → should not be picked up
    future = timezone.now() + timezone.timedelta(days=30)
    RecurringTemplate.objects.create(
        company=company,
        name="Future tpl",
        service_func="apps.recurring.runners:noop",
        schedule_type=RecurringTemplate.ScheduleType.MONTHLY,
        day_of_month=1,
        is_active=True,
        next_run_at=future,
    )
    # Past next_run_at → due
    past = timezone.now() - timezone.timedelta(days=1)
    RecurringTemplate.objects.create(
        company=company,
        name="Past tpl",
        service_func="apps.recurring.runners:noop",
        schedule_type=RecurringTemplate.ScheduleType.MONTHLY,
        day_of_month=1,
        is_active=True,
        next_run_at=past,
    )
    # Inactive → skip even if due
    RecurringTemplate.objects.create(
        company=company,
        name="Inactive tpl",
        service_func="apps.recurring.runners:noop",
        schedule_type=RecurringTemplate.ScheduleType.MONTHLY,
        day_of_month=1,
        is_active=False,
        next_run_at=past,
    )
    svc = RecurringService()
    results = svc.run_all_due()
    names = [r["name"] for r in results]
    assert "Past tpl" in names
    assert "Future tpl" not in names
    assert "Inactive tpl" not in names


def test_setup_defaults_creates_templates(setup):
    company = setup
    svc = RecurringService()
    created = svc.setup_defaults(company)
    assert len(created) == 3
    names = {t.name for t in created}
    assert "Khấu hao TSCĐ/CCDC hàng tháng" in names
    assert "Tính lương định kỳ" in names
    assert "Kết chuyển cuối kỳ" in names
    # All have valid next_run_at + dotted paths
    for tpl in created:
        assert tpl.next_run_at is not None
        assert ":" in tpl.service_func or "." in tpl.service_func
    # Idempotent
    again = svc.setup_defaults(company)
    assert len(again) == 3
    assert RecurringTemplate.objects.filter(company=company).count() == 3
