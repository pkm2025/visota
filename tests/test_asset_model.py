import pytest
from decimal import Decimal
from datetime import date
from apps.assets.models import FixedAsset, AssetCategory, AssetUsingDepartment
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy móc', level='group',
        is_for_tool=False, default_gl_account='2112',
        default_depreciation_rate=Decimal('0.20'),
        default_useful_life_months=60,
    )
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_BH', name='BH',
        default_expense_account='641',
    )
    return company, cat, dept


def test_asset_creation(setup):
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS001', asset_name='Xe Toyota',
        category=cat, using_department=dept,
        original_cost=Decimal('500000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='2112',
        depreciation_account='2141',
        expense_account='642',
    )
    assert a.pk is not None
    assert str(a) == 'TS001 - Xe Toyota'
    assert a.is_tool is False
    assert a.status == 'active'


def test_tool_creation(setup):
    """CCDC has is_tool=True and different GL accounts."""
    company, _, dept = setup
    from apps.assets.models import AssetCategory
    tool_cat = AssetCategory.objects.create(
        company=company, code='CCDC_NHOM', name='CCDC nhóm', level='group',
        is_for_tool=True, default_gl_account='142',
    )
    t = FixedAsset.objects.create(
        company=company, asset_code='CC01', asset_name='Kéo cắt',
        category=tool_cat, using_department=dept,
        original_cost=Decimal('1000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),  # 100% over 1 year
        useful_life_months=12,
        start_date=date(2026, 1, 1),
        gl_account='142',
        depreciation_account='142',  # CCDC uses same account
        expense_account='642',
        is_tool=True,
    )
    assert t.is_tool is True


def test_asset_defaults(setup):
    company, cat, dept = setup
    a = FixedAsset(
        company=company, asset_code='X', asset_name='Y',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        start_date=date(2026, 1, 1),
    )
    assert a.status == 'active'
    assert a.salvage_value == Decimal('0')
    assert a.accumulated_depreciation == Decimal('0')


def test_asset_net_book_value(setup):
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
        accumulated_depreciation=Decimal('300'),
    )
    assert a.net_book_value == Decimal('700')


def test_monthly_depreciation_straight_line(setup):
    """20% per year of 500M = 100M/year = ~8.33M/month."""
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('500000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
    )
    monthly = a.calculate_monthly_depreciation()
    # 500M * 20% / 12 = 8.333M
    assert monthly == Decimal('8333333.3333')


def test_monthly_depreciation_zero_after_full(setup):
    """Once fully depreciated, monthly = 0."""
    company, cat, dept = setup
    a = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),
        useful_life_months=12,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='214', expense_account='642',
        accumulated_depreciation=Decimal('1000'),  # fully depreciated
        status='fully_depreciated',
    )
    assert a.calculate_monthly_depreciation() == Decimal('0')
