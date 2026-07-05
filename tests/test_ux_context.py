import pytest
from apps.core.ux.context import UXContext
from apps.core.ux.defaults import suggest_ux_for_role, get_available_layouts


def test_default_ux_context():
    ux = UXContext(layout='modern', style='standard', workflow='scratch')
    assert ux.layout == 'modern'
    assert ux.style == 'standard'
    assert ux.workflow == 'scratch'


def test_ux_context_get_template_path():
    ux = UXContext(layout='modern', style='guided', workflow='scratch')
    path = ux.get_template('invoice/create', 'form.html')
    assert path == 'modern/invoice/create/guided/form.html'


def test_ux_context_get_template_with_default_name():
    ux = UXContext(layout='modern', style='standard')
    path = ux.get_template('voucher/create')
    assert path == 'modern/voucher/create/standard/form.html'


def test_default_style_for_layout_mobile_is_guided():
    assert UXContext.default_style_for_layout('mobile') == 'guided'


def test_default_style_for_layout_portal_is_standard():
    assert UXContext.default_style_for_layout('portal') == 'standard'


def test_default_style_for_layout_modern_is_standard():
    assert UXContext.default_style_for_layout('modern') == 'standard'


def test_default_style_for_layout_classic_is_standard():
    assert UXContext.default_style_for_layout('classic') == 'standard'


def test_default_style_for_unknown_layout_is_standard():
    assert UXContext.default_style_for_layout('unknown') == 'standard'


def test_suggest_ux_for_role_accountant():
    ux = suggest_ux_for_role('accountant')
    assert ux['layout'] == 'modern'
    assert ux['style'] == 'standard'


def test_suggest_ux_for_role_sales_is_guided():
    ux = suggest_ux_for_role('sales')
    assert ux['style'] == 'guided'


def test_suggest_ux_for_role_admin():
    ux = suggest_ux_for_role('admin')
    assert ux['layout'] == 'modern'


def test_suggest_ux_for_role_customer_is_portal():
    # /portal/ route doesn't exist - customer role falls back to default 'modern'
    ux = suggest_ux_for_role('customer')
    assert ux['layout'] == 'modern'


def test_suggest_ux_for_unknown_role_falls_back_to_default():
    ux = suggest_ux_for_role('unknown_role')
    assert ux['layout'] == 'modern'
    assert ux['style'] == 'standard'


def test_get_available_layouts():
    # Only layouts with actual URL routes are exposed (no dead links)
    layouts = get_available_layouts()
    codes = [l['code'] for l in layouts]
    assert 'modern' in codes
    assert 'classic' not in codes
    assert 'mobile' not in codes
    assert 'portal' not in codes


def test_ux_context_from_request(rf):
    """Test extraction from a request object."""
    req = rf.get('/modern/invoices/new/?style=quick&workflow=template')
    req.session = {}
    ux = UXContext.from_request(req)
    assert ux.layout == 'modern'
    assert ux.style == 'quick'
    assert ux.workflow == 'template'


def test_ux_context_from_request_uses_session_default(rf, db):
    """Without ?style= query, falls back to session-stored preference."""
    req = rf.get('/modern/invoices/new/')
    req.session = {'ux_style_modern': 'bulk'}
    ux = UXContext.from_request(req)
    assert ux.style == 'bulk'


def test_ux_context_from_request_uses_layout_default(rf):
    """Mobile layout defaults to guided if no session pref."""
    req = rf.get('/mobile/invoices/new/')
    req.session = {}
    ux = UXContext.from_request(req)
    assert ux.style == 'guided'


@pytest.fixture
def rf():
    from django.test import RequestFactory
    return RequestFactory()
