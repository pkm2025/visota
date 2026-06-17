import pytest
from decimal import Decimal
from datetime import date
from apps.assets.models import (
    FixedAsset, AssetCategory, AssetUsingDepartment, AssetDepreciation,
)
from apps.assets.services import DepreciationService
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance
from apps.core.models import Company


@pytest.fixture
def setup(db):
    company = Company.objects.create(code='TCO', name='Test')
    cat = AssetCategory.objects.create(
        company=company, code='MAY_MOC', name='Máy', level='group',
        is_for_tool=False, default_gl_account='211',
        default_depreciation_rate=Decimal('0.20'),
        default_useful_life_months=60,
    )
    dept = AssetUsingDepartment.objects.create(
        company=company, code='BP_QL', name='QLDN',
        default_expense_account='642',
    )
    return company, cat, dept


def test_depreciation_creates_voucher(setup):
    """Running depreciation generates voucher N642/C2141."""
    company, cat, dept = setup
    asset = FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='Xe',
        category=cat, using_department=dept,
        original_cost=Decimal('1200000000'),  # 1.2B
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),  # 20%/year = 240M/year = 20M/month
        useful_life_months=60,
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
    )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)

    # Should create 1 voucher, 1 AssetDepreciation entry
    assert result['assets_processed'] == 1
    assert result['total_depreciation'] == Decimal('20000000.0000')

    # Voucher exists with N642/C2141
    voucher = AccountingVoucher.objects.get(source='depreciation')
    assert voucher.is_posted
    assert voucher.voucher_type == 'depreciation'

    lines = voucher.lines.all()
    codes = {l.account_code for l in lines}
    assert '642' in codes  # expense debit
    assert '2141' in codes  # accumulated credit

    # N642 = 20M
    exp_line = lines.get(account_code='642')
    assert exp_line.debit_vnd == Decimal('20000000.0000')

    # Asset accumulated_depreciation updated
    asset.refresh_from_db()
    assert asset.accumulated_depreciation == Decimal('20000000.0000')

    # AssetDepreciation history row
    dep_history = AssetDepreciation.objects.get(asset=asset, period='2026-06')
    assert dep_history.depreciation_amount == Decimal('20000000.0000')


def test_depreciation_skips_fully_depreciated(setup):
    company, cat, dept = setup
    FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('1.0'),
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
        accumulated_depreciation=Decimal('1000'),
        status='fully_depreciated',
    )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)
    assert result['assets_processed'] == 0
    assert result['total_depreciation'] == Decimal('0')


def test_depreciation_aggregates_multiple_assets(setup):
    """Multiple assets in same expense account → 1 voucher with aggregated lines."""
    company, cat, dept = setup
    for i in range(3):
        FixedAsset.objects.create(
            company=company, asset_code=f'TS0{i+1}', asset_name=f'Asset {i+1}',
            category=cat, using_department=dept,
            original_cost=Decimal('1200000000'),
            depreciation_method='straight_line',
            depreciation_rate=Decimal('0.20'),
            start_date=date(2026, 1, 1),
            gl_account='211', depreciation_account='2141', expense_account='642',
        )

    service = DepreciationService(company=company)
    result = service.calculate_period(2026, 6)

    # 3 assets, total 3 * 20M = 60M
    assert result['assets_processed'] == 3
    assert result['total_depreciation'] == Decimal('60000000.0000')

    # Still just 1 voucher with 2 lines (N642=60M, C2141=60M)
    voucher = AccountingVoucher.objects.get(source='depreciation')
    lines = voucher.lines.all()
    assert lines.count() == 2  # 1 debit + 1 credit
    exp_line = lines.get(account_code='642')
    assert exp_line.debit_vnd == Decimal('60000000.0000')


def test_depreciation_idempotent(setup):
    """Running twice for same period does NOT double-depreciate."""
    company, cat, dept = setup
    FixedAsset.objects.create(
        company=company, asset_code='TS01', asset_name='X',
        category=cat, using_department=dept,
        original_cost=Decimal('1200000000'),
        depreciation_method='straight_line',
        depreciation_rate=Decimal('0.20'),
        start_date=date(2026, 1, 1),
        gl_account='211', depreciation_account='2141', expense_account='642',
    )

    service = DepreciationService(company=company)
    service.calculate_period(2026, 6)  # First run: 20M
    result = service.calculate_period(2026, 6)  # Second run: skip

    assert result['assets_processed'] == 0
    assert result['total_depreciation'] == Decimal('0')
    assert result['skipped_already_depreciated'] == 1
