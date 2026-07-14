"""Tests for modular sidebar module visibility system.

Covers ModuleVisibilityService, Company.enabled_modules persistence,
and the perm_tags has_module_access integration.
"""

import pytest

from apps.core.models import Company
from apps.core.module_config import (
    ADVANCED_MODULES,
    ALL_MODULES,
    CORE_MODULES,
    MODULE_LABELS,
    MODULE_PERMISSION_MAP,
    ModuleVisibilityService,
)

# --- Module configuration constants ---


def test_core_modules_contains_expected_modules():
    """Core modules must include kế toán, bán hàng, mua hàng, hóa đơn, kho, báo cáo."""
    expected = {"ke_toan", "ban_hang", "mua_hang", "hoa_don", "kho", "bao_cao"}
    assert expected == set(CORE_MODULES)


def test_advanced_modules_contains_expected_modules():
    """Advanced modules include HR, assets, CRM, budget, bidding, projects, etc."""
    expected = {
        "nhan_su",
        "tai_san",
        "crm",
        "ngan_sach",
        "dau_thau",
        "du_an",
        "vay",
        "bao_lanh",
    }
    assert expected == set(ADVANCED_MODULES)


def test_core_and_advanced_no_overlap():
    """Core and advanced module lists must not overlap."""
    assert set(CORE_MODULES).isdisjoint(set(ADVANCED_MODULES))


def test_all_modules_is_core_plus_advanced():
    """ALL_MODULES should contain all core and advanced modules."""
    assert set(ALL_MODULES) == set(CORE_MODULES) | set(ADVANCED_MODULES)


def test_every_module_has_label():
    """Every module in ALL_MODULES must have a label."""
    for m in ALL_MODULES:
        assert m in MODULE_LABELS, f"Module '{m}' missing label"
        assert MODULE_LABELS[m], f"Module '{m}' has empty label"


def test_every_module_has_permission_mapping():
    """Every module in ALL_MODULES must have a permission mapping."""
    for m in ALL_MODULES:
        assert m in MODULE_PERMISSION_MAP, f"Module '{m}' missing permission mapping"
        assert MODULE_PERMISSION_MAP[m], f"Module '{m}' has empty permission mapping"


def test_hr_maps_to_hr_permission():
    """nhan_su module maps to hr and payroll permissions."""
    assert "hr" in MODULE_PERMISSION_MAP["nhan_su"]
    assert "payroll" in MODULE_PERMISSION_MAP["nhan_su"]


def test_tai_san_maps_to_assets():
    """tai_san module maps to assets permission."""
    assert "assets" in MODULE_PERMISSION_MAP["tai_san"]


def test_crm_maps_to_crm():
    """crm module maps to crm permission."""
    assert "crm" in MODULE_PERMISSION_MAP["crm"]


def test_bao_lanh_maps_to_guarantees():
    """bao_lanh module maps to guarantees permission."""
    assert "guarantees" in MODULE_PERMISSION_MAP["bao_lanh"]


def test_vay_maps_to_loans():
    """vay module maps to loans permission."""
    assert "loans" in MODULE_PERMISSION_MAP["vay"]


# --- ModuleVisibilityService: DNSN (TT58) defaults ---


@pytest.fixture
def dnsn_company(db):
    """Create a TT58 DNSN company with default settings."""
    return Company.objects.create(
        code="DNSN01",
        name="DNSN Test Company",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt133_company(db):
    """Create a TT133 company."""
    return Company.objects.create(
        code="TT13301",
        name="TT133 Test Company",
        accounting_regime="tt133",
    )


class TestDNSNDefaultVisibility:
    """VAL-BRAND-017: Sidebar shows core modules by default for DNSN."""

    def test_core_modules_visible_for_dnsn(self, dnsn_company):
        """All core modules must be visible by default for DNSN."""
        svc = ModuleVisibilityService(dnsn_company)
        for m in CORE_MODULES:
            assert svc.is_module_visible(m), f"Core module '{m}' should be visible"

    def test_ke_toan_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("ke_toan") is True

    def test_ban_hang_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("ban_hang") is True

    def test_mua_hang_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("mua_hang") is True

    def test_hoa_don_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("hoa_don") is True

    def test_kho_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("kho") is True

    def test_bao_cao_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("bao_cao") is True


class TestDNSNAdvancedHidden:
    """VAL-BRAND-018: Sidebar hides advanced modules by default for DNSN."""

    def test_advanced_modules_hidden_for_dnsn(self, dnsn_company):
        """All advanced modules must be hidden by default for DNSN."""
        svc = ModuleVisibilityService(dnsn_company)
        for m in ADVANCED_MODULES:
            assert not svc.is_module_visible(m), f"Advanced module '{m}' should be hidden"

    def test_nhan_su_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("nhan_su") is False

    def test_tai_san_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("tai_san") is False

    def test_crm_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("crm") is False

    def test_ngan_sach_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("ngan_sach") is False

    def test_dau_thau_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("dau_thau") is False

    def test_du_an_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("du_an") is False

    def test_vay_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("vay") is False

    def test_bao_lanh_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("bao_lanh") is False


class TestDNSNPermissionModuleVisibility:
    """Permission-level module checks for DNSN."""

    def test_hr_permission_hidden(self, dnsn_company):
        """hr permission module should be hidden for DNSN by default."""
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("hr") is False

    def test_assets_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("assets") is False

    def test_crm_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("crm") is False

    def test_budget_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("budget") is False

    def test_bidding_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("bidding") is False

    def test_projects_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("projects") is False

    def test_loans_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("loans") is False

    def test_guarantees_permission_hidden(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("guarantees") is False

    def test_ledger_permission_visible(self, dnsn_company):
        """ledger permission module should be visible (maps to ke_toan core)."""
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("ledger") is True

    def test_sales_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("sales") is True

    def test_purchasing_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("purchasing") is True

    def test_einvoice_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("einvoice") is True

    def test_inventory_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("inventory") is True

    def test_reporting_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("reporting") is True


# --- VAL-BRAND-019: Advanced modules can be enabled ---


class TestDNSNEnableAdvanced:
    """Advanced modules can be enabled and appear in sidebar."""

    def test_enable_nhan_su_makes_it_visible(self, dnsn_company):
        """VAL-BRAND-019: Enable HR in settings, it should be visible."""
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("nhan_su") is False

        svc.enable_module("nhan_su")
        dnsn_company.save()

        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("nhan_su") is True

    def test_enable_tai_san_makes_permission_visible(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("tai_san")
        dnsn_company.save()

        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_permission_module_visible("assets") is True

    def test_enable_crm(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("crm")
        dnsn_company.save()
        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("crm") is True

    def test_enable_multiple_modules(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.set_enabled_modules(["nhan_su", "tai_san", "du_an"])
        dnsn_company.save()
        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("nhan_su") is True
        assert svc2.is_module_visible("tai_san") is True
        assert svc2.is_module_visible("du_an") is True
        # Others still hidden
        assert svc2.is_module_visible("crm") is False

    def test_disable_module(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("nhan_su")
        svc.disable_module("nhan_su")
        dnsn_company.save()
        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("nhan_su") is False

    def test_cannot_enable_core_module_as_advanced(self, dnsn_company):
        """Enabling a core module via enable_module should be a no-op."""
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("ke_toan")  # should be ignored
        # Core modules are always visible regardless
        assert svc.is_module_visible("ke_toan") is True


# --- VAL-BRAND-019: Persistence across sessions ---


class TestModuleVisibilityPersistence:
    """Module visibility persists across sessions (DB persistence)."""

    def test_enabled_modules_persist_in_db(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("nhan_su")
        svc.enable_module("tai_san")
        dnsn_company.save()

        # Reload from DB
        dnsn_company.refresh_from_db()
        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("nhan_su") is True
        assert svc2.is_module_visible("tai_san") is True

    def test_disabled_modules_persist(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("crm")
        svc.disable_module("crm")
        dnsn_company.save()
        dnsn_company.refresh_from_db()
        svc2 = ModuleVisibilityService(dnsn_company)
        assert svc2.is_module_visible("crm") is False

    def test_new_company_has_no_enabled_modules(self, db):
        c = Company.objects.create(code="NEW1", name="New", accounting_regime="tt58")
        svc = ModuleVisibilityService(c)
        assert svc.get_enabled_display_modules() == []


# --- Non-DNSN companies ---


class TestNonDNSNVisibility:
    """Non-DNSN companies (TT133/TT200) see all modules by default."""

    def test_all_advanced_visible_for_tt133(self, tt133_company):
        svc = ModuleVisibilityService(tt133_company)
        for m in ADVANCED_MODULES:
            assert svc.is_module_visible(m), f"Advanced '{m}' should be visible for TT133"

    def test_all_core_visible_for_tt133(self, tt133_company):
        svc = ModuleVisibilityService(tt133_company)
        for m in CORE_MODULES:
            assert svc.is_module_visible(m), f"Core '{m}' should be visible for TT133"


# --- Hệ thống always visible ---


class TestHeThongAlwaysVisible:
    """VAL-BRAND-020: Hệ thống section always visible."""

    def test_he_thong_visible_dnsn(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("he_thong") is True

    def test_he_thong_visible_tt133(self, tt133_company):
        svc = ModuleVisibilityService(tt133_company)
        assert svc.is_module_visible("he_thong") is True

    def test_he_thong_visible_no_company(self):
        svc = ModuleVisibilityService(None)
        assert svc.is_module_visible("he_thong") is True


# --- Edge cases ---


class TestEdgeCases:
    """Edge cases and safety checks."""

    def test_no_company_returns_false_for_modules(self):
        """With no company, regular modules are not visible."""
        svc = ModuleVisibilityService(None)
        assert svc.is_module_visible("nhan_su") is False
        assert svc.is_module_visible("ke_toan") is False

    def test_unknown_module_returns_false(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_module_visible("nonexistent") is False

    def test_unknown_permission_module_returns_false(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        assert svc.is_permission_module_visible("nonexistent") is False

    def test_get_visible_display_modules_dnsn(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        visible = svc.get_visible_display_modules()
        assert "ke_toan" in visible
        assert "ban_hang" in visible
        assert "mua_hang" in visible
        assert "hoa_don" in visible
        assert "kho" in visible
        assert "bao_cao" in visible
        # Advanced not in visible
        assert "nhan_su" not in visible

    def test_get_hidden_display_modules_dnsn(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        hidden = svc.get_hidden_display_modules()
        assert "nhan_su" in hidden
        assert "tai_san" in hidden
        assert "crm" in hidden
        # Core not in hidden
        assert "ke_toan" not in hidden

    def test_get_visible_after_enable(self, dnsn_company):
        svc = ModuleVisibilityService(dnsn_company)
        svc.enable_module("nhan_su")
        svc.enable_module("du_an")
        dnsn_company.save()
        svc2 = ModuleVisibilityService(dnsn_company)
        visible = svc2.get_visible_display_modules()
        assert "nhan_su" in visible
        assert "du_an" in visible
        assert "tai_san" not in visible


# --- Company model field ---


class TestCompanyEnabledModulesField:
    """Company.enabled_modules field existence and persistence."""

    def test_company_has_enabled_modules_field(self):
        c = Company(code="X", name="X")
        assert hasattr(c, "enabled_modules")

    def test_enabled_modules_defaults_to_empty_dict(self):
        c = Company(code="X", name="X")
        assert c.enabled_modules == {}

    @pytest.mark.django_db
    def test_enabled_modules_persists(self):
        c = Company.objects.create(code="PERSIST1", name="Persist Test")
        c.enabled_modules = {"nhan_su": True, "crm": False}
        c.save()
        c.refresh_from_db()
        assert c.enabled_modules["nhan_su"] is True
        assert c.enabled_modules["crm"] is False
