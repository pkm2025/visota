import pytest
from apps.core.ux.registry import (
    InteractionStyle, InteractionStyleRegistry,
    GuidedStyle, StandardStyle, QuickStyle, BulkStyle,
)


def test_registry_has_standard():
    assert InteractionStyleRegistry.get('standard') is StandardStyle


def test_registry_has_guided():
    assert InteractionStyleRegistry.get('guided') is GuidedStyle


def test_registry_has_quick():
    assert InteractionStyleRegistry.get('quick') is QuickStyle


def test_registry_has_bulk():
    assert InteractionStyleRegistry.get('bulk') is BulkStyle


def test_registry_all_returns_4_builtins():
    codes = {s.code for s in InteractionStyleRegistry.all()}
    assert {'guided', 'standard', 'quick', 'bulk'}.issubset(codes)


def test_standard_supports_voucher_create():
    assert 'voucher.create' in StandardStyle.supported_operations


def test_guided_supports_voucher_create():
    assert 'voucher.create' in GuidedStyle.supported_operations


def test_bulk_does_not_support_period_closing():
    assert 'period.closing' not in BulkStyle.supported_operations


def test_standard_supports_period_closing():
    assert 'period.closing' in StandardStyle.supported_operations


def test_registry_can_register_custom():
    class CustomStyle(InteractionStyle):
        code = 'custom_test'
        name = 'Custom'
        supported_operations = ['test.op']
        template_prefix = 'test'
        url_suffix = 'custom-test'

    InteractionStyleRegistry.register(CustomStyle)
    assert InteractionStyleRegistry.get('custom_test') is CustomStyle


def test_for_operation_filters_supported():
    styles = InteractionStyleRegistry.for_operation('voucher.create')
    codes = {s.code for s in styles}
    assert 'standard' in codes
    assert 'guided' in codes


def test_for_operation_excludes_unsupported():
    """Bulk style doesn't support period.closing"""
    styles = InteractionStyleRegistry.for_operation('period.closing')
    codes = {s.code for s in styles}
    assert 'bulk' not in codes
    assert 'standard' in codes


def test_interaction_style_supports_helper():
    assert GuidedStyle.supports('voucher.create') is True
    assert GuidedStyle.supports('period.closing') is False


def test_interaction_style_get_template():
    template = GuidedStyle.get_template('invoice/create', 'form.html')
    assert template == 'guided/invoice/create/form.html'


def test_standard_url_suffix_is_empty():
    """Standard is default so URL has no suffix."""
    assert StandardStyle.url_suffix == ''
