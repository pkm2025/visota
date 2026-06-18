"""Template filter to add HTML attributes to form field widgets.

Usage:
    {{ form.field|attr:"class:form-control" }}
    {{ form.field|attr:"rows:3" }}
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="attr")
def attr_filter(field, spec):
    """Add attribute(s) to a bound form field's widget.

    spec is a string of "name:value" pairs separated by "|".
    Each "name:value" sets widget attr name -> value.
    """
    if field is None:
        return ""
    if not hasattr(field, "as_widget"):
        return field
    if not spec:
        return field
    attrs = {}
    # Existing widget attrs
    existing = getattr(field.field.widget, "attrs", {}) or {}
    attrs.update(existing)
    for piece in str(spec).split("|"):
        if ":" in piece:
            name, value = piece.split(":", 1)
            attrs[name.strip()] = value.strip()
    return mark_safe(field.as_widget(attrs=attrs))
