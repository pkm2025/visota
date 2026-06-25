"""Template filters for number formatting (Vietnamese Dong)."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value):
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal("0")


@register.filter
def vnd(value):
    """Format number as Vietnamese Dong with thousand separators."""
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


@register.filter
def subtract(value, arg):
    """value - arg."""
    return _to_decimal(value) - _to_decimal(arg)


@register.filter
def multiply(value, arg):
    """value × arg."""
    return _to_decimal(value) * _to_decimal(arg)


@register.filter
def divide(value, arg):
    """value ÷ arg (returns 0 on zero divisor)."""
    divisor = _to_decimal(arg)
    if not divisor:
        return Decimal("0")
    return _to_decimal(value) / divisor
