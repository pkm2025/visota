"""Tests for asset UI views (list, create, depreciation run)."""

import pytest
from django.test import Client

from apps.identity.models import User


@pytest.fixture
def auth_client(db):
    user = User.objects.create_superuser(username="alice", password="Secret123", email="alice@test.local")
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_asset_list_loads(auth_client):
    response = auth_client.get("/modern/assets/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_asset_create_form_loads(auth_client):
    response = auth_client.get("/modern/assets/new/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_depreciation_run_form_loads(auth_client):
    response = auth_client.get("/modern/assets/depreciation/")
    assert response.status_code == 200
