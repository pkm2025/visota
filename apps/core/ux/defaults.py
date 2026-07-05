"""Smart UX defaults by user role and layout availability."""

from typing import Any

ROLE_DEFAULT_UX = {
    "admin": {"layout": "modern", "style": "standard"},
    "chief_accountant": {"layout": "modern", "style": "standard"},
    "accountant": {"layout": "modern", "style": "standard"},
    "data_entry": {"layout": "modern", "style": "quick"},
    "sales": {"layout": "modern", "style": "guided"},
    "manager": {"layout": "modern", "style": "standard"},
    "auditor": {"layout": "modern", "style": "standard"},
    "customer": {"layout": "modern", "style": "standard"},
}

DEFAULT_UX = {"layout": "modern", "style": "standard"}

# Only "modern" has actual URL routes (classic/mobile/portal are dead links).
# AVAILABLE_LAYOUTS kept for reference but get_available_layouts() returns only
# layouts with working URL routes so the switcher never shows dead links.
_ALL_LAYOUTS = [
    {"code": "modern", "name": "Modern", "icon": "bi-window-stack", "url_prefix": "/modern/"},
    {"code": "classic", "name": "Classic", "icon": "bi-table", "url_prefix": "/classic/"},
    {"code": "mobile", "name": "Mobile", "icon": "bi-phone", "url_prefix": "/mobile/"},
    {"code": "portal", "name": "Portal", "icon": "bi-person-circle", "url_prefix": "/portal/"},
]

# Layouts that actually have URL routes registered (filter dead links).
AVAILABLE_LAYOUTS = [layout for layout in _ALL_LAYOUTS if layout["code"] == "modern"]


def suggest_ux_for_role(role_code: str) -> dict[str, str]:
    """Suggest UX defaults for a given user role."""
    ux = ROLE_DEFAULT_UX.get(role_code, DEFAULT_UX.copy())
    # Ensure suggested layout is one that actually exists (avoid dead links).
    valid_codes = {layout["code"] for layout in AVAILABLE_LAYOUTS}
    if ux["layout"] not in valid_codes:
        ux["layout"] = DEFAULT_UX["layout"]
    return ux


def get_available_layouts() -> list[dict[str, Any]]:
    """Return list of available layout packs (for switcher UI).

    Only layouts with actual URL routes are returned, so the footer switcher
    never shows dead links (e.g. /classic/, /mobile/, /portal/).
    """
    return AVAILABLE_LAYOUTS
