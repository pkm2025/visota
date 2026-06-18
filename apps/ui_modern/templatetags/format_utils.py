"""Template filters for number formatting (Vietnamese Dong)."""

from django import template

register = template.Library()


@register.filter
def vnd(value):
    """Format number as Vietnamese Dong with thousand separators.

    Returns the integer value formatted with commas (e.g. 1234567 -> "1,234,567").
    Safe for Decimal, int, float, str inputs. Returns input unchanged on failure.
    """
    if value is None or value == "":
        return value
    try:
        return f"{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return value


@register.filter
def vnd_decimal(value):
    """Like :func:`vnd` but preserves up to 4 decimal places when present."""
    if value is None or value == "":
        return value
    try:
        f = float(value)
    except (ValueError, TypeError):
        return value
    if abs(f - round(f)) < 1e-9:
        return f"{int(round(f)):,}"
    return f"{f:,.4f}"
