"""Tests for Modern UI dashboard view."""
import pytest
from django.test import Client
from apps.identity.models import User


def test_dashboard_requires_login():
    """Unauthenticated users are redirected to login."""
    client = Client()
    response = client.get('/modern/')
    assert response.status_code == 302
    assert '/auth/login/' in response.url


@pytest.mark.django_db
def test_dashboard_loads_for_authenticated_user():
    """Authenticated users see dashboard with greeting."""
    user = User.objects.create_user(
        username='alice', password='Secret123', full_name='Alice',
    )
    client = Client()
    client.force_login(user)

    response = client.get('/modern/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'Tổng quan' in content
    assert 'Alice' in content


@pytest.mark.django_db
def test_dashboard_has_layout_switcher():
    """Dashboard renders layout switcher."""
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.get('/modern/')
    assert b'layout-switcher' in response.content


@pytest.mark.django_db
def test_dashboard_has_sidebar_with_navigation():
    """Sidebar contains navigation sections."""
    user = User.objects.create_user(username='alice', password='Secret123')
    client = Client()
    client.force_login(user)
    response = client.get('/modern/')
    content = response.content.decode('utf-8')
    assert 'sidebar' in content
    assert 'Cập nhật số liệu' in content
    assert 'Trang chủ' in content
