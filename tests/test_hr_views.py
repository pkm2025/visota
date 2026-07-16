"""Tests for HR + payroll UI views (just verify pages load)."""

import pytest
from django.test import Client

from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    from apps.core.models import Company
    company = Company.objects.create(
        code='TST', name='Test Co', tax_code='0100000000', accounting_regime='tt133'
    )
    user = User.objects.create_superuser(username="alice", password="Secret123", email="alice@test.local")
    c = Client()
    c.force_login(user)
    session = c.session
    session['current_company_id'] = company.id
    session.save()
    return c


@pytest.mark.django_db
def test_employee_list_loads(auth_client):
    response = auth_client.get("/modern/employees/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_employee_create_form_loads(auth_client):
    response = auth_client.get("/modern/employees/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_payroll_run_form_loads(auth_client):
    response = auth_client.get("/modern/payroll/run/")
    assert response.status_code == 200
