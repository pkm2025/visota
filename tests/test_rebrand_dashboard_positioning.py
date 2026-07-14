"""Tests for DNSN dashboard and positioning rebranding.

Validates:
- VAL-BRAND-013: Login page has DNSN positioning text
- VAL-BRAND-014: Dashboard displays DNSN-relevant widgets
- VAL-BRAND-015: Dashboard does not show advanced metrics by default
- VAL-BRAND-016: Dashboard mobile view shows compact DNSN metrics
- VAL-BRAND-029: Landing page positioning targets DNSN
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models.dnsn import DnsnLedgerBalance

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Login page DNSN positioning (VAL-BRAND-013)
# ---------------------------------------------------------------------------


class TestLoginPageDnsnPositioning:
    def test_login_page_has_dnsn_positioning_text(self):
        """VAL-BRAND-013: Login page has visible positioning text targeting DNSN."""
        client = Client()
        response = client.get("/auth/login/")
        content = response.content.decode("utf-8")
        assert response.status_code == 200
        # Must reference micro/small enterprises (DNSN or siêu nhỏ)
        assert "siêu nhỏ" in content.lower() or "DNSN" in content
        assert "doanh nghiệp" in content.lower()

    def test_login_template_has_dnsn_tagline(self):
        """Login template file contains DNSN positioning text."""
        path = BASE_DIR / "templates" / "modern" / "auth" / "login.html"
        content = path.read_text(encoding="utf-8")
        assert "siêu nhỏ" in content.lower() or "DNSN" in content
        assert "auth-tagline" in content


# ---------------------------------------------------------------------------
# Dashboard DNSN widgets (VAL-BRAND-014)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDnsnDashboardWidgets:
    """VAL-BRAND-014: Dashboard displays DNSN-relevant widgets."""

    def _setup_dnsn_company_and_user(self):
        company = Company.objects.create(
            code="DNSN1",
            name="DN Sieu Nho Test",
            accounting_regime=Company.AccountingRegime.TT58,
            entity_type=Company.EntityType.DOANH_NGHIEP_SIEU_NHO,
            vat_method=Company.VatMethod.KHAU_TRU,
            tndn_method=Company.TndnMethod.TINH_THUE,
        )
        user = User.objects.create_superuser(
            username="dnsn_admin",
            password="Secret123",
            email="dnsn@test.local",
        )
        return company, user

    def test_dnsn_dashboard_shows_revenue_widget(self):
        """Dashboard for TT58 company shows doanh thu hôm nay widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Doanh thu hôm nay" in content

    def test_dnsn_dashboard_shows_cost_widget(self):
        """Dashboard for TT58 company shows chi phí widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Chi phí" in content

    def test_dnsn_dashboard_shows_profit_widget(self):
        """Dashboard for TT58 company shows lợi nhuận widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Lợi nhuận" in content

    def test_dnsn_dashboard_shows_tax_widget(self):
        """Dashboard for TT58 company shows thuế phải nộp widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Thuế phải nộp" in content

    def test_dnsn_dashboard_shows_receivable_widget(self):
        """Dashboard for TT58 company shows công nợ phải thu widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Công nợ phải thu" in content

    def test_dnsn_dashboard_shows_inventory_widget(self):
        """Dashboard for TT58 company shows tồn kho widget."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Tồn kho" in content

    def test_dnsn_dashboard_context_has_metrics(self):
        """Dashboard view context includes all DNSN metric values."""
        company, user = self._setup_dnsn_company_and_user()
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        ctx = response.context
        assert ctx["is_dnsn"] is True
        assert "dnsn_revenue_today" in ctx
        assert "dnsn_period_cost" in ctx
        assert "dnsn_period_profit" in ctx
        assert "dnsn_tax_payable" in ctx
        assert "dnsn_receivable_total" in ctx
        assert "dnsn_inventory_value" in ctx


# ---------------------------------------------------------------------------
# Dashboard no advanced metrics (VAL-BRAND-015)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDnsnDashboardNoAdvancedMetrics:
    """VAL-BRAND-015: Dashboard does not show advanced metrics by default."""

    def test_dnsn_dashboard_no_ceo_accountant_toggle(self):
        """DNSN dashboard does not show CEO/Accountant view toggle."""
        Company.objects.create(
            code="DNSN2",
            name="DN Sieu Nho Test 2",
            accounting_regime=Company.AccountingRegime.TT58,
        )
        user = User.objects.create_superuser(
            username="dnsn_admin2", password="Secret123", email="dnsn2@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        # The CEO/Accountant toggle should not be present for DNSN
        assert "Kế toán" not in content or "view=accountant" not in content

    def test_dnsn_dashboard_no_project_profitability(self):
        """DNSN dashboard does not show project profitability widget."""
        Company.objects.create(
            code="DNSN3",
            name="DN Sieu Nho Test 3",
            accounting_regime=Company.AccountingRegime.TT58,
        )
        user = User.objects.create_superuser(
            username="dnsn_admin3", password="Secret123", email="dnsn3@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "project profitability" not in content.lower()
        assert "multi-entity" not in content.lower()
        assert "consolidation" not in content.lower()

    def test_non_dnsn_dashboard_shows_standard_view(self):
        """Non-TT58 company dashboard still shows standard CEO/Accountant view."""
        Company.objects.create(
            code="TT133C",
            name="TT133 Company",
            accounting_regime=Company.AccountingRegime.TT133,
        )
        user = User.objects.create_superuser(
            username="tt133_admin", password="Secret123", email="tt133@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        ctx = response.context
        assert ctx["is_dnsn"] is False


# ---------------------------------------------------------------------------
# Mobile dashboard compact DNSN metrics (VAL-BRAND-016)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDnsnMobileDashboard:
    """VAL-BRAND-016: Mobile dashboard shows compact DNSN metrics."""

    def test_dnsn_mobile_has_compact_metrics(self):
        """DNSN dashboard has mobile-only compact metrics (d-md-none)."""
        Company.objects.create(
            code="DNSN4",
            name="DN Sieu Nho Mobile",
            accounting_regime=Company.AccountingRegime.TT58,
        )
        user = User.objects.create_superuser(
            username="dnsn_mobile", password="Secret123", email="mobile@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        # Mobile section exists
        assert "d-md-none" in content
        # Compact DNSN metric labels
        assert "Tiền" in content
        assert "Doanh thu" in content
        assert "Lợi nhuận" in content
        assert "Công nợ" in content

    def test_dnsn_mobile_has_quick_actions(self):
        """DNSN mobile dashboard has quick action buttons."""
        Company.objects.create(
            code="DNSN5",
            name="DN Sieu Nho QA",
            accounting_regime=Company.AccountingRegime.TT58,
        )
        user = User.objects.create_superuser(
            username="dnsn_qa", password="Secret123", email="qa@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        content = response.content.decode("utf-8")
        assert "Phiếu" in content
        assert "Báo cáo" in content


# ---------------------------------------------------------------------------
# Landing page DNSN positioning (VAL-BRAND-029)
# ---------------------------------------------------------------------------


class TestLandingPageDnsnPositioning:
    """VAL-BRAND-029: Landing page positioning targets DNSN."""

    def test_landing_template_has_dnsn_copy(self):
        """Landing page template references micro/small enterprises."""
        path = BASE_DIR / "templates" / "public" / "landing.html"
        content = path.read_text(encoding="utf-8")
        # Must reference DNSN, siêu nhỏ, or doanh nghiệp siêu nhỏ
        assert "siêu nhỏ" in content.lower() or "DNSN" in content

    def test_landing_meta_description_targets_dnsn(self):
        """Landing page meta description mentions DNSN/siêu nhỏ."""
        path = BASE_DIR / "templates" / "public" / "landing.html"
        content = path.read_text(encoding="utf-8")
        # Find meta description
        assert "siêu nhỏ" in content.lower() or "DNSN" in content
        assert "doanh nghiệp" in content.lower()

    def test_landing_hero_targets_dnsn(self):
        """Landing page hero section targets DNSN."""
        path = BASE_DIR / "templates" / "public" / "landing.html"
        content = path.read_text(encoding="utf-8")
        # Hero should mention siêu nhỏ or DNSN
        assert "siêu nhỏ" in content.lower() or "DNSN" in content
        assert "hộ kinh doanh" in content.lower()

    def test_landing_no_pmketoan(self):
        """Landing page does not contain PMKetoan."""
        path = BASE_DIR / "templates" / "public" / "landing.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota" in content


# ---------------------------------------------------------------------------
# Dashboard metrics computation from DNSN ledger data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDnsnDashboardMetricsComputation:
    """Verify DNSN dashboard correctly computes metrics from DnsnLedgerBalance."""

    def test_dashboard_with_dnsn_balance_data(self):
        """Dashboard correctly reads revenue, cost, and tax from DnsnLedgerBalance."""
        today = date.today()
        company = Company.objects.create(
            code="DNSN6",
            name="DN Sieu Nho Data",
            accounting_regime=Company.AccountingRegime.TT58,
            vat_method=Company.VatMethod.KHAU_TRU,
            tndn_method=Company.TndnMethod.TINH_THUE,
        )
        # Create ledger balances
        DnsnLedgerBalance.objects.create(
            company=company,
            fiscal_year=today.year,
            period=today.month,
            ledger_type="s2b",
            opening_revenue=Decimal("0"),
            period_revenue=Decimal("50000000"),
            closing_revenue=Decimal("50000000"),
            opening_cost=Decimal("0"),
            period_cost=Decimal("35000000"),
            closing_cost=Decimal("35000000"),
        )
        DnsnLedgerBalance.objects.create(
            company=company,
            fiscal_year=today.year,
            period=today.month,
            ledger_type="s3b",
            opening_vat=Decimal("0"),
            period_vat=Decimal("5000000"),
            closing_vat=Decimal("5000000"),
        )
        DnsnLedgerBalance.objects.create(
            company=company,
            fiscal_year=today.year,
            period=today.month,
            ledger_type="s2d",
            opening_cash=Decimal("100000000"),
            period_cash=Decimal("50000000"),
            closing_cash=Decimal("150000000"),
        )

        user = User.objects.create_superuser(
            username="dnsn_data", password="Secret123", email="data@test.local"
        )
        client = Client()
        client.force_login(user)
        response = client.get("/modern/")
        ctx = response.context

        assert ctx["is_dnsn"] is True
        assert ctx["dnsn_period_revenue"] == Decimal("50000000")
        assert ctx["dnsn_period_cost"] == Decimal("35000000")
        assert ctx["dnsn_period_profit"] == Decimal("15000000")
        assert ctx["dnsn_vat_payable"] == Decimal("5000000")
        assert ctx["dnsn_cash_total"] == Decimal("150000000")
