"""Tests for the PMKetoan → Visota ERP rebranding.

Validates:
- DEFAULT_BRAND uses "Visota ERP"
- Company model has hide_visota_branding field
- NinjaAPI title is "Visota ERP API"
- Auth view classes use Visota prefix
- Notification from_email uses Visota domain
- No PMKetoan string in rendered HTML templates
- Report PDF footer shows Visota ERP
- PWA manifest has correct names
- Logo SVG uses letter V
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apps.core.middleware import DEFAULT_BRAND
from apps.core.models import Company

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# DEFAULT_BRAND tests (VAL-BRAND-008)
# ---------------------------------------------------------------------------


class TestDefaultBrand:
    def test_default_brand_name_is_visota(self):
        assert DEFAULT_BRAND["name"] == "Visota ERP"

    def test_default_brand_has_hide_visota_branding_key(self):
        assert "hide_visota_branding" in DEFAULT_BRAND
        assert "hide_pmketoan_branding" not in DEFAULT_BRAND

    def test_default_brand_logo_path(self):
        assert "logo" in DEFAULT_BRAND


# ---------------------------------------------------------------------------
# Company model field tests (VAL-BRAND-031, VAL-BRAND-032)
# ---------------------------------------------------------------------------


class TestCompanyModelBranding:
    def test_company_has_hide_visota_branding_field(self):
        """Company model must have hide_visota_branding field."""
        field_names = {f.name for f in Company._meta.get_fields()}
        assert "hide_visota_branding" in field_names

    def test_company_does_not_have_hide_pmketoan_branding(self):
        """Old field name must be gone."""
        field_names = {f.name for f in Company._meta.get_fields()}
        assert "hide_pmketoan_branding" not in field_names

    def test_hide_visota_branding_defaults_false(self):
        c = Company(code="X", name="X")
        assert c.hide_visota_branding is False


# ---------------------------------------------------------------------------
# API title tests (VAL-BRAND-036)
# ---------------------------------------------------------------------------


class TestApiBranding:
    def test_api_title_is_visota(self):
        from apps.core.api import api

        assert api.title == "Visota ERP API"


# ---------------------------------------------------------------------------
# Auth view class tests (VAL-BRAND-039)
# ---------------------------------------------------------------------------


class TestAuthViewClasses:
    def test_login_view_class_name_is_visota(self):
        from apps.ui_modern.views.auth_views import VisotaLoginView

        assert VisotaLoginView.__name__ == "VisotaLoginView"

    def test_logout_view_class_name_is_visota(self):
        from apps.ui_modern.views.auth_views import VisotaLogoutView

        assert VisotaLogoutView.__name__ == "VisotaLogoutView"

    def test_pmketoan_login_view_class_does_not_exist(self):
        """Old class name should no longer be importable."""
        import importlib

        mod = importlib.import_module("apps.ui_modern.views.auth_views")
        assert not hasattr(mod, "PMKetoanLoginView")


# ---------------------------------------------------------------------------
# Notification from_email tests (VAL-BRAND-038)
# ---------------------------------------------------------------------------


class TestNotificationEmail:
    def test_from_email_uses_visota_domain(self):
        from apps.notifications.services import EmailService

        # The DEFAULT_FROM_EMAIL in settings overrides the service default.
        # In test settings, Django sets it to 'webmaster@localhost'.
        # We verify the service default (when DEFAULT_FROM_EMAIL is unset).
        import inspect

        source = inspect.getsource(EmailService.get_config)
        assert "pmketoan" not in source.lower()
        assert "visota" in source.lower()


# ---------------------------------------------------------------------------
# Migration tests (VAL-BRAND-031)
# ---------------------------------------------------------------------------


class TestMigrationExists:
    def test_rename_migration_exists(self):
        migration_dir = BASE_DIR / "apps" / "core" / "migrations"
        files = list(migration_dir.glob("*.py"))
        migration_names = [f.stem for f in files]
        # The migration should reference the rename
        rename_found = False
        for f in files:
            if f.stem == "__init__":
                continue
            content = f.read_text(encoding="utf-8")
            if "hide_pmketoan_branding" in content and "hide_visota_branding" in content:
                rename_found = True
                break
        assert rename_found, "No migration found renaming hide_pmketoan_branding"


# ---------------------------------------------------------------------------
# Static file content tests
# ---------------------------------------------------------------------------


class TestStaticFiles:
    def test_manifest_json_has_visota_names(self):
        manifest_path = BASE_DIR / "static" / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["name"] == "Visota ERP"
        assert data["short_name"] == "Visota"

    def test_logo_svg_uses_letter_v(self):
        logo_path = BASE_DIR / "static" / "images" / "logo.svg"
        content = logo_path.read_text(encoding="utf-8")
        assert ">V<" in content
        assert "aria-label" in content
        assert "Visota" in content

    def test_service_worker_no_pmketoan(self):
        sw_path = BASE_DIR / "static" / "sw.js"
        content = sw_path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota ERP" in content

    def test_mobile_js_no_pmketoan(self):
        js_path = BASE_DIR / "static" / "modern" / "js" / "mobile.js"
        content = js_path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content


# ---------------------------------------------------------------------------
# Template content tests (VAL-BRAND-001 to VAL-BRAND-006)
# ---------------------------------------------------------------------------


class TestTemplateContents:
    def test_layout_html_no_pmketoan(self):
        path = BASE_DIR / "templates" / "modern" / "base" / "layout.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota ERP" in content

    def test_right_sidebar_no_pmketoan(self):
        path = BASE_DIR / "templates" / "modern" / "base" / "_right_sidebar.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota" in content

    def test_report_pdf_footer_visota(self):
        path = BASE_DIR / "templates" / "modern" / "reporting" / "report_export_pdf.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota" in content

    def test_blog_list_no_pmketoan(self):
        path = BASE_DIR / "templates" / "public" / "blog_list.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota" in content

    def test_blog_detail_no_pmketoan(self):
        path = BASE_DIR / "templates" / "public" / "blog_detail.html"
        content = path.read_text(encoding="utf-8")
        assert "PMKetoan" not in content
        assert "Visota" in content


# ---------------------------------------------------------------------------
# Login page render test (VAL-BRAND-011, VAL-BRAND-012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginPageRendering:
    def test_login_page_shows_visota_brand(self):
        from django.test import Client

        client = Client()
        response = client.get("/auth/login/")
        content = response.content.decode("utf-8")
        assert response.status_code == 200
        assert "Visota ERP" in content
        assert "PMKetoan" not in content


# ---------------------------------------------------------------------------
# Middleware brand test (VAL-BRAND-008, VAL-BRAND-032)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBrandingMiddleware:
    def test_middleware_uses_hide_visota_branding(self, company):
        from django.test import RequestFactory

        from apps.core.middleware import BrandingMiddleware

        rf = RequestFactory()
        req = rf.get("/modern/")
        req.current_company = company

        middleware = BrandingMiddleware(lambda r: MagicMock())
        middleware(req)

        assert "hide_visota_branding" in req.brand
        assert "hide_pmketoan_branding" not in req.brand
