"""Template tags for pulling legal references from DB into templates."""

from django import template

from apps.core.models import LegalReference

register = template.Library()


@register.simple_tag
def legal_reference_list(limit=10):
    """Return active legal references, ordered by code."""
    try:
        return list(LegalReference.objects.filter(status="active").order_by("code")[:limit])
    except Exception:
        # If table doesn't exist or other DB error, return empty
        return []
