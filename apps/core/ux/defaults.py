"""Smart UX defaults by user role and layout availability."""

ROLE_DEFAULT_UX = {
    'admin':            {'layout': 'modern',  'style': 'standard'},
    'chief_accountant': {'layout': 'classic', 'style': 'standard'},
    'accountant':       {'layout': 'modern',  'style': 'standard'},
    'data_entry':       {'layout': 'modern',  'style': 'quick'},
    'sales':            {'layout': 'modern',  'style': 'guided'},
    'manager':          {'layout': 'modern',  'style': 'standard'},
    'auditor':          {'layout': 'classic', 'style': 'standard'},
    'customer':         {'layout': 'portal',  'style': 'standard'},
}

DEFAULT_UX = {'layout': 'modern', 'style': 'standard'}

AVAILABLE_LAYOUTS = [
    {'code': 'modern',  'name': 'Modern',  'icon': 'bi-window-stack',  'url_prefix': '/modern/'},
    {'code': 'classic', 'name': 'Classic', 'icon': 'bi-table',         'url_prefix': '/classic/'},
    {'code': 'mobile',  'name': 'Mobile',  'icon': 'bi-phone',         'url_prefix': '/mobile/'},
    {'code': 'portal',  'name': 'Portal',  'icon': 'bi-person-circle', 'url_prefix': '/portal/'},
]


def suggest_ux_for_role(role_code: str) -> dict[str, str]:
    """Suggest UX defaults for a given user role."""
    return ROLE_DEFAULT_UX.get(role_code, DEFAULT_UX.copy())


def get_available_layouts() -> list[dict]:
    """Return list of available layout packs (for switcher UI)."""
    return AVAILABLE_LAYOUTS
