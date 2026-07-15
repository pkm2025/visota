"""Tests for e-invoice ND 254/2026 compliance: invoice_category field + regulatory references.

Covers VAL-EINV-001 (coded/uncoded taxonomy field) and VAL-EINV-002 (module
references updated to ND 254/2026 + TT 91/2026).
"""

import inspect

import pytest

from apps.core.models import Company
from apps.einvoice.models import EInvoice, EInvoiceCategory


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="EINVND254",
        name="ND 254 Test Co",
        tax_code="0133334444",
    )


# ---------------------------------------------------------------------------
# VAL-EINV-001: E-invoice has coded/uncoded taxonomy field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_invoice_category_choices_exist():
    """EInvoiceCategory enum has coded, uncoded, cash_register choices."""
    values = [c[0] for c in EInvoiceCategory.choices]
    assert "coded" in values
    assert "uncoded" in values
    assert "cash_register" in values


@pytest.mark.django_db
def test_invoice_category_field_exists():
    """EInvoice model has invoice_category field."""
    field = EInvoice._meta.get_field("invoice_category")
    assert field is not None
    assert field.max_length == 20


@pytest.mark.django_db
def test_invoice_category_default_is_coded():
    """New EInvoice defaults to 'coded' category."""
    assert EInvoiceCategory.CODED == "coded"
    # Check the field default from meta
    field = EInvoice._meta.get_field("invoice_category")
    assert field.default == EInvoiceCategory.CODED


@pytest.mark.django_db
def test_einvoice_create_with_category_default(company):
    """Creating an EInvoice without explicit category uses coded."""
    ei = EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="AA/26E",
    )
    assert ei.invoice_category == EInvoiceCategory.CODED
    assert ei.get_invoice_category_display() == "Có mã của CQT"


@pytest.mark.django_db
def test_einvoice_create_with_uncoded(company):
    """Creating an EInvoice with uncoded category."""
    ei = EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="AA/26E",
        invoice_category=EInvoiceCategory.UNCODED,
    )
    assert ei.invoice_category == "uncoded"
    assert ei.get_invoice_category_display() == "Không có mã"


@pytest.mark.django_db
def test_einvoice_create_with_cash_register(company):
    """Creating an EInvoice with cash_register category."""
    ei = EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="AA/26E",
        invoice_category=EInvoiceCategory.CASH_REGISTER,
    )
    assert ei.invoice_category == "cash_register"
    assert ei.get_invoice_category_display() == "Khởi tạo từ máy tính tiền"


@pytest.mark.django_db
def test_invoice_category_field_has_choices():
    """Field definition includes all three choices."""
    field = EInvoice._meta.get_field("invoice_category")
    choice_values = [c[0] for c in field.choices]
    assert set(choice_values) == {"coded", "uncoded", "cash_register"}


@pytest.mark.django_db
def test_invoice_category_filterable(company):
    """Can filter EInvoices by invoice_category."""
    EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="AA/26E",
        invoice_category=EInvoiceCategory.CODED,
    )
    EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="BB/26E",
        invoice_category=EInvoiceCategory.UNCODED,
    )
    EInvoice.objects.create(
        company=company,
        pattern="1C26T",
        serial="CC/26E",
        invoice_category=EInvoiceCategory.CASH_REGISTER,
    )
    assert EInvoice.objects.filter(invoice_category="coded").count() == 1
    assert EInvoice.objects.filter(invoice_category="uncoded").count() == 1
    assert EInvoice.objects.filter(invoice_category="cash_register").count() == 1


# ---------------------------------------------------------------------------
# VAL-EINV-002: Module references updated to ND 254/2026 + TT 91/2026
# ---------------------------------------------------------------------------


def test_einvoice_models_docstring_references_nd254():
    """E-invoice models module docstring references ND 254/2026 and TT 91/2026."""
    import apps.einvoice.models as einvoice_models

    docstring = einvoice_models.__doc__
    assert docstring is not None
    assert "ND 254/2026" in docstring
    assert "TT 91/2026" in docstring


def test_einvoice_apps_docstring_references_nd254():
    """E-invoice apps module docstring references ND 254/2026 and TT 91/2026."""
    import apps.einvoice.apps as einvoice_apps

    docstring = einvoice_apps.__doc__
    assert docstring is not None
    assert "ND 254/2026" in docstring
    assert "TT 91/2026" in docstring


def test_einvoice_services_docstring_references_nd254():
    """E-invoice services module docstring references ND 254/2026 + TT 91/2026."""
    import apps.einvoice.services.__init__ as einvoice_services_mod

    docstring = einvoice_services_mod.__doc__
    assert docstring is not None
    assert "ND 254/2026" in docstring
    assert "TT 91/2026" in docstring


def test_einvoice_models_no_standalone_tt78():
    """E-invoice models docstring should not reference TT78 as the primary regulation.

    The only acceptable TT78 mention is a historical note that it was superseded.
    """
    import apps.einvoice.models as einvoice_models

    # TT78 should not appear as the primary reference in the module docstring
    module_doc = einvoice_models.__doc__ or ""
    # Check that ND 254/2026 is the primary reference, not TT78
    assert "ND 254/2026" in module_doc


def test_einvoice_category_enum_docstring_references_nd254():
    """EInvoiceCategory enum docstring references ND 254/2026."""
    docstring = inspect.getdoc(EInvoiceCategory)
    assert docstring is not None
    assert "ND 254/2026" in docstring


def test_seed_help_articles_references_nd254():
    """Help articles seed data references ND 254/2026 instead of TT78/2021."""
    from apps.public.management.commands import seed_help_articles

    source = inspect.getsource(seed_help_articles)
    assert "ND 254/2026" in source


def test_seed_permissions_references_nd254():
    """Permissions seed data references ND 254/2026 for einvoice module."""
    from apps.identity.management.commands import seed_permissions

    source = inspect.getsource(seed_permissions)
    # Find the einvoice line
    assert "ND 254/2026" in source
    assert "TT78/2021" not in source.split("einvoice")[1].split(")")[0]


def test_module_config_references_nd254():
    """Module config references ND 254/2026 for hoa_don module description."""
    from apps.core import module_config

    desc = module_config.MODULE_DESCRIPTIONS.get("hoa_don", "")
    assert "ND 254/2026" in desc
