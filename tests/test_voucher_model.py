import pytest
from decimal import Decimal
from datetime import date
from apps.ledger.models import AccountingVoucher, VoucherLine
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(code='TCO', name='Test Co')


@pytest.fixture
def voucher(company):
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
        description='Test voucher',
        currency_code='VND', exchange_rate=Decimal('1'),
        status=AccountingVoucher.Status.DRAFT,
    )
    return v


def test_voucher_creation(voucher):
    assert voucher.pk is not None
    assert str(voucher) == 'BC0001 (2026-06-15)'


def test_voucher_status_choices():
    assert AccountingVoucher.Status.DRAFT == 0
    assert AccountingVoucher.Status.SUBSIDIARY == 1
    assert AccountingVoucher.Status.LEDGER == 2
    assert AccountingVoucher.Status.LOCKED == 3


def test_voucher_default_status_is_ledger():
    """If not set, defaults to LEDGER (status=2) per SIS behavior."""
    v = AccountingVoucher(
        company_id=1, fiscal_year=2026, period=6,
        voucher_no='X', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    assert v.status == AccountingVoucher.Status.LEDGER


def test_voucher_line_creation(voucher):
    line = VoucherLine.objects.create(
        voucher=voucher, line_no=1,
        account_code='111',
        debit_vnd=Decimal('1000'), credit_vnd=Decimal('0'),
    )
    assert line.pk is not None
    assert line.debit_vnd == Decimal('1000')


def test_voucher_unique_per_company_fy_type_no(company):
    AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no='BC0001', voucher_type='journal',
        voucher_date=date(2026, 6, 15),
    )
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        AccountingVoucher.objects.create(
            company=company, fiscal_year=2026, period=6,
            voucher_no='BC0001', voucher_type='journal',
            voucher_date=date(2026, 6, 16),
        )


def test_voucher_line_object_code_can_be_blank(voucher):
    """Most lines don't need object_code (customer/vendor)."""
    line = VoucherLine.objects.create(
        voucher=voucher, line_no=1,
        account_code='5111', debit_vnd=Decimal('0'), credit_vnd=Decimal('100'),
    )
    assert line.object_code == ''
    assert line.object_type == ''
