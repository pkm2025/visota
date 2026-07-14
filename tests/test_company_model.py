import pytest
from apps.core.models import Company
from apps.core.managers import CompanyQuerySet


def test_company_creation(company):
    assert company.pk is not None
    assert company.code == 'TEST'
    assert str(company) == 'Test Company'


def test_company_str_representation(company):
    assert 'Test Company' in str(company)


def test_company_default_regime_is_tt133():
    c = Company(code='X', name='X')
    assert c.accounting_regime == 'tt133'


def test_company_default_currency_vnd():
    c = Company(code='X', name='X')
    assert c.default_currency == 'VND'


def test_company_queryset_returns_company_queryset():
    assert isinstance(Company.objects.all(), CompanyQuerySet)


def test_company_branding_fields_default():
    c = Company(code='X', name='X')
    assert c.brand_primary_color == '#2563eb'
    assert c.default_layout == 'modern'
    assert c.hide_visota_branding is False
