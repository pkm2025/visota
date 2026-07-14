"""Tests for TT58 company configuration: vat_method, tndn_method, entity_type,
tax_method_group computed property, and accounting_regime='tt58' choice.
"""

import pytest
from apps.core.models import Company


# --- Field existence & defaults ---

def test_company_has_vat_method_field():
    """Company model must have vat_method field."""
    c = Company(code='X', name='X')
    assert hasattr(c, 'vat_method')


def test_company_has_tndn_method_field():
    """Company model must have tndn_method field."""
    c = Company(code='X', name='X')
    assert hasattr(c, 'tndn_method')


def test_company_has_entity_type_field():
    """Company model must have entity_type field."""
    c = Company(code='X', name='X')
    assert hasattr(c, 'entity_type')


def test_company_vat_method_default_khau_tru():
    """vat_method defaults to khau_tru."""
    c = Company(code='X', name='X')
    assert c.vat_method == 'khau_tru'


def test_company_tndn_method_default_tinh_thue():
    """tndn_method defaults to tinh_thue."""
    c = Company(code='X', name='X')
    assert c.tndn_method == 'tinh_thue'


def test_company_entity_type_default_dnsn():
    """entity_type defaults to doanh_nghiep_sieu_nho."""
    c = Company(code='X', name='X')
    assert c.entity_type == 'doanh_nghiep_sieu_nho'


# --- accounting_regime includes tt58 ---

def test_accounting_regime_has_tt58_choice():
    """AccountingRegime choices must include 'tt58'."""
    choices = [code for code, _label in Company.AccountingRegime.choices]
    assert 'tt58' in choices


def test_company_can_set_regime_tt58():
    """A company can be created with accounting_regime='tt58'."""
    c = Company(code='X', name='X', accounting_regime='tt58')
    assert c.accounting_regime == 'tt58'


def test_accounting_regime_tt58_label():
    """TT58 choice has a human-readable label."""
    label = dict(Company.AccountingRegime.choices).get('tt58')
    assert label is not None
    assert 'TT58' in label or '58' in label


# --- vat_method choices ---

def test_vat_method_choices():
    """vat_method must have khau_tru and ty_le_phan_tram choices."""
    choices = [code for code, _label in Company.VatMethod.choices]
    assert 'khau_tru' in choices
    assert 'ty_le_phan_tram' in choices


# --- tndn_method choices ---

def test_tndn_method_choices():
    """tndn_method must have tinh_thue and ty_le_phan_tram choices."""
    choices = [code for code, _label in Company.TndnMethod.choices]
    assert 'tinh_thue' in choices
    assert 'ty_le_phan_tram' in choices


# --- entity_type choices ---

def test_entity_type_choices():
    """entity_type must have all three choices."""
    choices = [code for code, _label in Company.EntityType.choices]
    assert 'doanh_nghiep_sieu_nho' in choices
    assert 'ho_kinh_doanh' in choices
    assert 'ca_nhan_kinh_doanh' in choices


# --- tax_method_group computed property ---

def test_tax_method_group_property_exists():
    """Company must have tax_method_group property."""
    c = Company(code='X', name='X')
    assert hasattr(c, 'tax_method_group')


def test_tax_method_group_1_vat_pct_tndn_pct():
    """Group 1: vat=ty_le_phan_tram + tndn=ty_le_phan_tram."""
    c = Company(
        code='X', name='X',
        vat_method='ty_le_phan_tram',
        tndn_method='ty_le_phan_tram',
    )
    assert c.tax_method_group == 1


def test_tax_method_group_2_vat_pct_tndn_tinh_thue():
    """Group 2: vat=ty_le_phan_tram + tndn=tinh_thue."""
    c = Company(
        code='X', name='X',
        vat_method='ty_le_phan_tram',
        tndn_method='tinh_thue',
    )
    assert c.tax_method_group == 2


def test_tax_method_group_3_vat_khau_tru_tndn_pct():
    """Group 3: vat=khau_tru + tndn=ty_le_phan_tram."""
    c = Company(
        code='X', name='X',
        vat_method='khau_tru',
        tndn_method='ty_le_phan_tram',
    )
    assert c.tax_method_group == 3


def test_tax_method_group_4_vat_khau_tru_tndn_tinh_thue():
    """Group 4: vat=khau_tru + tndn=tinh_thue."""
    c = Company(
        code='X', name='X',
        vat_method='khau_tru',
        tndn_method='tinh_thue',
    )
    assert c.tax_method_group == 4


def test_tax_method_group_default_is_4():
    """Default vat=khau_tru + tndn=tinh_thue => Group 4."""
    c = Company(code='X', name='X')
    assert c.tax_method_group == 4


def test_tax_method_group_recomputes_on_change():
    """Changing vat_method or tndn_method recomputes the group."""
    c = Company(code='X', name='X')
    assert c.tax_method_group == 4  # default

    c.vat_method = 'ty_le_phan_tram'
    c.tndn_method = 'ty_le_phan_tram'
    assert c.tax_method_group == 1

    c.tndn_method = 'tinh_thue'
    assert c.tax_method_group == 2


# --- tax_method_group display label ---

def test_tax_method_group_label_exists():
    """Company must have a method to get the group display label."""
    c = Company(code='X', name='X')
    assert hasattr(c, 'tax_method_group_label')


def test_tax_method_group_label_group_1():
    """Group 1 label mentions GTGT tỷ lệ % and TNDN tỷ lệ %."""
    c = Company(
        code='X', name='X',
        vat_method='ty_le_phan_tram',
        tndn_method='ty_le_phan_tram',
    )
    label = c.tax_method_group_label
    assert '1' in label
    assert 'tỷ lệ' in label.lower() or 'Tỷ lệ' in label


def test_tax_method_group_label_group_4():
    """Group 4 label mentions khấu trừ and tính thuế."""
    c = Company(
        code='X', name='X',
        vat_method='khau_tru',
        tndn_method='tinh_thue',
    )
    label = c.tax_method_group_label
    assert '4' in label


# --- DB persistence ---

@pytest.mark.django_db
def test_tt58_company_persists_with_all_fields():
    """A TT58 company with all fields can be saved and retrieved."""
    c = Company.objects.create(
        code='TT58A',
        name='TT58 Company A',
        accounting_regime='tt58',
        vat_method='ty_le_phan_tram',
        tndn_method='ty_le_phan_tram',
        entity_type='doanh_nghiep_sieu_nho',
    )
    c.refresh_from_db()
    assert c.accounting_regime == 'tt58'
    assert c.vat_method == 'ty_le_phan_tram'
    assert c.tndn_method == 'ty_le_phan_tram'
    assert c.entity_type == 'doanh_nghiep_sieu_nho'
    assert c.tax_method_group == 1


@pytest.mark.django_db
def test_non_tt58_company_fields_default():
    """A non-TT58 company still has the fields with defaults."""
    c = Company.objects.create(
        code='TT133A',
        name='TT133 Company',
        accounting_regime='tt133',
    )
    c.refresh_from_db()
    assert c.vat_method == 'khau_tru'
    assert c.tndn_method == 'tinh_thue'
    assert c.entity_type == 'doanh_nghiep_sieu_nho'
    assert c.tax_method_group == 4


@pytest.mark.django_db
def test_changing_vat_method_updates_group():
    """Changing vat_method and saving updates tax_method_group."""
    c = Company.objects.create(
        code='CHG1',
        name='Change Test',
        accounting_regime='tt58',
        vat_method='khau_tru',
        tndn_method='tinh_thue',
    )
    assert c.tax_method_group == 4

    c.vat_method = 'ty_le_phan_tram'
    c.tndn_method = 'ty_le_phan_tram'
    c.save()
    c.refresh_from_db()
    assert c.tax_method_group == 1


# --- Non-TT58 regime unchanged ---

def test_existing_regimes_still_available():
    """TT133, TT200, Q48 choices must still exist."""
    choices = [code for code, _label in Company.AccountingRegime.choices]
    assert 'tt133' in choices
    assert 'tt200' in choices
    assert 'q48' in choices
