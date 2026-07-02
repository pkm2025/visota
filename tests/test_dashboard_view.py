"""Tests for Modern UI dashboard view."""

import pytest
from django.test import Client
from apps.identity.models import User


def test_dashboard_requires_login():
    """Unauthenticated users are redirected to login."""
    client = Client()
    response = client.get("/modern/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_dashboard_loads_for_authenticated_user():
    """Authenticated users see dashboard with greeting."""
    user = User.objects.create_superuser(
        username="alice",
        password="Secret123",
        full_name="Alice",
        email="alice@test.local",
    )
    client = Client()
    client.force_login(user)

    response = client.get("/modern/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tổng quan" in content
    assert "Alice" in content


@pytest.mark.django_db
def test_dashboard_has_layout_switcher():
    """Dashboard renders layout switcher."""
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/")
    assert b"layout-switcher" in response.content


@pytest.mark.django_db
def test_dashboard_has_sidebar_with_navigation():
    """Sidebar contains navigation sections."""
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "sidebar" in content
    assert "Cập nhật số liệu" in content
    assert "Trang chủ" in content


@pytest.mark.django_db
def test_dashboard_has_mobile_home_screen():
    """Dashboard includes mobile-only compact metrics + quick actions (d-md-none)."""
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/")
    content = response.content.decode("utf-8")
    # Mobile section is hidden on desktop via d-md-none
    assert "d-md-none" in content
    # 3 key metrics labels
    assert "Tiền" in content
    assert "Doanh thu" in content
    assert "Công nợ" in content
    # Quick action buttons
    assert "Phiếu" in content
    assert "Duyệt" in content
    assert "Báo cáo" in content
    assert "Thông báo" in content


@pytest.mark.django_db
def test_dashboard_ceo_view_has_cash_pnl_ar():
    """CEO view shows cash position, P&L, and AR aging widgets."""
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local"
    )
    client = Client()
    client.force_login(user)
    response = client.get("/modern/?view=ceo")
    content = response.content.decode("utf-8")
    assert "Tiền hiện có" in content
    assert "Lãi/Lỗ tháng này" in content
    assert "Công nợ phải thu" in content
    assert "Lịch thuế sắp tới" in content
