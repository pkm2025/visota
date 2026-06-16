"""Context processors available in all templates."""

from apps.core.ux.defaults import get_available_layouts


def branding(request):
    """Expose brand info, current layout, and available layouts to templates."""
    return {
        "brand": getattr(request, "brand", {}),
        "current_layout": getattr(request, "current_layout", "modern"),
        "current_company": getattr(request, "current_company", None),
        "available_layouts": get_available_layouts(),
    }
