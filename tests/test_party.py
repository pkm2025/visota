import pytest
from apps.master_data.models import Customer, Vendor
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_customer_creation(company):
    c = Customer.objects.create(
        company=company, code='KH001', name='Công ty ABC',
        tax_code='0101234567', address='Hà Nội',
    )
    assert c.pk is not None
    assert str(c) == 'KH001 - Công ty ABC'
    assert c.is_active is True
    assert c.gl_account_receivable == '131'


def test_customer_code_unique_per_company(company):
    from django.db import IntegrityError
    from apps.core.models import Company
    Customer.objects.create(company=company, code='KH001', name='A')
    other = Company.objects.create(code='OCO', name='Other')
    Customer.objects.create(company=other, code='KH001', name='B')  # different co → OK
    with pytest.raises(IntegrityError):
        Customer.objects.create(company=company, code='KH001', name='C')


def test_vendor_creation(company):
    v = Vendor.objects.create(
        company=company, code='NCC001', name='Nhà cung cấp XYZ',
        tax_code='0307654321',
    )
    assert v.pk is not None
    assert str(v) == 'NCC001 - Nhà cung cấp XYZ'
    assert v.gl_account_payable == '331'


def test_customer_is_supplier_flag(company):
    """A customer can also be a vendor (one-time setup)."""
    c = Customer.objects.create(
        company=company, code='KH001', name='A',
        is_supplier=True,
    )
    assert c.is_supplier is True


def test_vendor_is_contractor_flag(company):
    v = Vendor.objects.create(
        company=company, code='NCC001', name='A',
        is_contractor=True,
    )
    assert v.is_contractor is True
