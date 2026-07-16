"""Tests for Modern UI dashboard view."""

import pytest
from django.test import Client
from apps.core.models import Company
from apps.identity.models import User


@pytest.fixture
def company_with_session():
    """Create a company and yield (company, authenticated client) pair."""
    company = Company.objects.create(
        code="DASH", name="Dash Co", tax_code="0100000001", accounting_regime="tt133"
    )
    user = User.objects.create_superuser(
        username="alice", password="Secret123", email="alice@test.local", full_name="Alice"
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["current_company_id"] = company.id
    session.save()
    return company, client, user


def test_dashboard_requires_login():
    """Unauthenticated users are redirected to login."""
    client = Client()
    response = client.get("/modern/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_dashboard_loads_for_authenticated_user(company_with_session):
    """Authenticated users see dashboard with greeting."""
    _, client, _ = company_with_session

    response = client.get("/modern/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Tổng quan" in content


@pytest.mark.django_db
def test_dashboard_has_layout_switcher(company_with_session):
    """Dashboard does not show layout switcher when only one layout has routes.

    VAL-UX-001: Dead layout switcher links (/classic/, /mobile/, /portal/) removed.
    Only 'modern' layout has URL routes, so switcher is hidden.
    """
    _, client, _ = company_with_session
    response = client.get("/modern/")
    # Switcher should not render when only 1 layout available
    assert b"layout-switcher" not in response.content


@pytest.mark.django_db
def test_dashboard_has_sidebar_with_navigation(company_with_session):
    """Sidebar contains navigation sections."""
    _, client, _ = company_with_session
    response = client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "sidebar" in content
    assert "Cập nhật số liệu" in content
    assert "Trang chủ" in content


@pytest.mark.django_db
def test_dashboard_has_mobile_home_screen(company_with_session):
    """Dashboard includes mobile-only compact metrics + quick actions (d-md-none)."""
    _, client, _ = company_with_session
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
def test_dashboard_ceo_view_has_cash_pnl_ar(company_with_session):
    """CEO view shows cash position, P&L, and AR aging widgets."""
    _, client, _ = company_with_session
    response = client.get("/modern/?view=ceo")
    content = response.content.decode("utf-8")
    assert "Tiền hiện có" in content
    assert "Lãi/Lỗ tháng này" in content
    assert "Công nợ phải thu" in content
    assert "Lịch thuế sắp tới" in content
