import pytest
from apps.master_data.models import Product, Warehouse
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_product_creation(company):
    p = Product.objects.create(
        company=company, code='SP001', name='Pin AA',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    assert p.pk is not None
    assert str(p) == 'SP001 - Pin AA'
    assert p.cost_method == 'weighted_avg'
    assert p.default_vat_rate == 0.10


def test_warehouse_creation(company):
    w = Warehouse.objects.create(
        company=company, code='KHO_HN', name='Kho Hà Nội',
        warehouse_type='finished',
    )
    assert w.pk is not None
    assert str(w) == 'KHO_HN - Kho Hà Nội'


def test_product_unique_per_company(company):
    from django.db import IntegrityError
    from apps.core.models import Company
    Product.objects.create(
        company=company, code='SP001', name='A',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    other = Company.objects.create(code='OCO', name='Other')
    Product.objects.create(
        company=other, code='SP001', name='B',
        product_type='goods', unit_id='CAI',
        gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
    )
    with pytest.raises(IntegrityError):
        Product.objects.create(
            company=company, code='SP001', name='C',
            product_type='goods', unit_id='CAI',
            gl_account_inv='156', gl_account_cogs='632', gl_account_revenue='5111',
        )
