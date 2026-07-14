import pytest
from django.test import RequestFactory
from apps.core.middleware import TenantMiddleware, BrandingMiddleware
from apps.core.models import Company


@pytest.fixture
def rf():
    return RequestFactory()


def test_branding_middleware_sets_default_brand_for_anonymous(rf):
    req = rf.get('/modern/')
    req.user = type('AnonymousUser', (), {'is_authenticated': False})()

    middleware = BrandingMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)

    assert req.brand['name'] == 'Visota ERP'
    assert req.brand['primary_color'] == '#2563eb'


def test_branding_middleware_sets_company_brand(rf, company):
    req = rf.get('/modern/')
    req.user = type('User', (), {'is_authenticated': True})()
    req.current_company = company

    middleware = BrandingMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)

    assert req.brand['name'] == 'Test Company'
    assert req.brand['primary_color'] == '#2563eb'


def test_tenant_middleware_detects_layout_modern(rf):
    req = rf.get('/modern/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'modern'


def test_tenant_middleware_detects_layout_classic(rf):
    req = rf.get('/classic/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'classic'


def test_tenant_middleware_detects_layout_mobile(rf):
    req = rf.get('/mobile/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'mobile'


def test_tenant_middleware_detects_layout_portal(rf):
    req = rf.get('/portal/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'portal'


def test_tenant_middleware_defaults_to_modern(rf):
    req = rf.get('/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'modern'
