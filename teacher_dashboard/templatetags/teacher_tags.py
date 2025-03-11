from django import template
from datetime import datetime, timedelta


register = template.Library()
@register.filter
def add_days(value, days):
    """Add a given number of days to a date."""
    try:
        if isinstance(value, str):
            # Parse date string to date object
            value = datetime.strptime(value, "%Y-%m-%d").date()
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value


@register.filter
def days_until(start_date, end_date):
    """Calculate the number of days between two dates."""
    try:
        return (end_date - start_date).days
    except (ValueError, TypeError, AttributeError):
        return 0


@register.filter
def filter_by_day(slots, day):
    """Filter classes by the given day."""
    filtered_slots = []
    for slot in slots:
        if slot.day_of_week == int(day):
            filtered_slots.append(slot)
    return filtered_slots


@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def split(value, arg):
    """Split a string by the specified separator."""
    return value.split(arg)
