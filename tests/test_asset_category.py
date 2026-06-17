import pytest
from apps.assets.models import AssetCategory, AssetUsingDepartment
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test')


def test_asset_category_creation(company):
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy móc thiết bị',
        level='group', is_for_tool=False,
        default_gl_account='2112',
        default_depreciation_rate=0.20,
        default_useful_life_months=60,
    )
    assert cat.pk is not None
    assert str(cat) == 'MAY_MOC - Máy móc thiết bị'


def test_asset_category_levels():
    """Categories have 3 levels: type, group, subgroup."""
    assert hasattr(AssetCategory, 'level')
    choices = [c[0] for c in AssetCategory._meta.get_field('level').choices]
    assert 'type' in choices
    assert 'group' in choices
    assert 'subgroup' in choices


def test_asset_category_for_tool_flag(company):
    """CCDC categories have is_for_tool=True; TSCĐ=False."""
    AssetCategory.objects.create(
        company=company, code='TOOL', name='CCDC', level='type', is_for_tool=True,
    )
    cat = AssetCategory.objects.get(code='TOOL')
    assert cat.is_for_tool is True


def test_using_department_creation(company):
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_BH', name='Bộ phận Bán hàng',
        default_expense_account='641',
    )
    assert dept.pk is not None
    assert str(dept) == 'BP_BH - Bộ phận Bán hàng'
