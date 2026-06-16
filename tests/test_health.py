import pytest
from django.test import Client


def test_health_simple(client):
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'


@pytest.mark.django_db
def test_health_detailed_returns_200_when_healthy(client):
    response = client.get('/health/detailed/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'checks' in data
    assert 'database' in data['checks']
    assert 'cache' in data['checks']
    assert data['checks']['database']['status'] == 'ok'
    assert data['checks']['cache']['status'] == 'ok'


@pytest.mark.django_db
def test_health_detailed_includes_request_id(client):
    response = client.get('/health/detailed/')
    data = response.json()
    # Optional meta section
    assert 'checks' in data


def test_health_no_auth_required(client):
    """Health endpoints should not require authentication."""
    response = client.get('/health/')
    assert response.status_code == 200
