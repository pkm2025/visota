"""Tests for LegalReference model."""

from datetime import date

import pytest

from apps.core.models import LegalReference


@pytest.fixture
def cleanup(db):
    LegalReference.objects.all().delete()


def test_create_legal_reference(db, cleanup):
    """A LegalReference can be created with full fields."""
    ref = LegalReference.objects.create(
        code='TT133',
        name='TT133/2016',
        full_name='Thông tư 133/2016/TT-BTC - Chế độ kế toán DN nhỏ và vừa',
        issuing_body='Bộ Tài chính',
        issue_date=date(2016, 8, 1),
        effective_date=date(2017, 1, 1),
        applicable_to=['accounting'],
        status='active',
        url='https://thuvienphapluat.vn/',
    )
    assert ref.pk is not None
    assert ref.code == 'TT133'
    assert 'accounting' in ref.applicable_to
    assert ref.status == 'active'


def test_list_active_references(db, cleanup):
    """Active references can be listed and filtered."""
    LegalReference.objects.create(
        code='TT133', name='TT133', full_name='x', issuing_body='BTC',
        issue_date=date(2016, 8, 1), effective_date=date(2017, 1, 1),
        applicable_to=['accounting'], status='active',
    )
    LegalReference.objects.create(
        code='TT99', name='TT99', full_name='x', issuing_body='BTC',
        issue_date=date(2025, 6, 1), effective_date=date(2026, 1, 1),
        applicable_to=['accounting'], status='active',
    )
    active = LegalReference.objects.filter(status='active')
    assert active.count() == 2
    accounting = LegalReference.objects.filter(applicable_to__contains=['accounting'])
    assert accounting.count() == 2


def test_superseded_reference(db, cleanup):
    """A superseded reference links to its replacement."""
    tt200 = LegalReference.objects.create(
        code='TT200', name='TT200', full_name='x', issuing_body='BTC',
        issue_date=date(2014, 12, 22), effective_date=date(2015, 1, 1),
        applicable_to=['accounting'], status='superseded',
    )
    tt99 = LegalReference.objects.create(
        code='TT99', name='TT99', full_name='x', issuing_body='BTC',
        issue_date=date(2025, 6, 1), effective_date=date(2026, 1, 1),
        applicable_to=['accounting'], status='active',
    )
    tt200.replaced_by = tt99
    tt200.save()
    tt200.refresh_from_db()
    assert tt200.status == 'superseded'
    assert tt200.replaced_by_id == tt99.id
