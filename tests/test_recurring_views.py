"""Tests for recurring UI views."""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.recurring.models import RecurringTemplate
from apps.recurring.services import RecurringService


@pytest.fixture
def auth_client(db):
    user = User.objects.create_superuser(username="alice", password="Secret123", email="alice@test.local")
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def setup(db):
    company = Company.objects.create(code="TCO", name="Test Co")
    RecurringService().setup_defaults(company)
    return company


@pytest.mark.django_db
def test_recurring_list_loads(auth_client, setup):
    response = auth_client.get("/modern/recurring/")
    assert response.status_code == 200
    # Page renders the templates table with seeded data
    assert b"recurring_run" in response.content or "Kh".encode("utf-8") in response.content


@pytest.mark.django_db
def test_recurring_run_triggers_due(auth_client, setup):
    # Force at least one template to be due
    tpl = RecurringTemplate.objects.filter(company=setup).first()
    from django.utils import timezone

    tpl.next_run_at = timezone.now() - timezone.timedelta(days=1)
    tpl.service_func = "apps.recurring.runners:noop"
    tpl.save()

    response = auth_client.post("/modern/recurring/run/")
    assert response.status_code in (200, 302)

    tpl.refresh_from_db()
    assert tpl.last_run_at is not None
