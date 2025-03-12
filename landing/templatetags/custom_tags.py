from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def get_pricing_rule(subject, profile):
    """Get pricing rule for a subject based on profile's grade and board"""
    return subject.pricing_rules.filter(grade=profile.grade, board=profile.board).first()

@register.filter
def multiply(value, arg):
    """Multiply the arg and the value"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


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
def filter_by_day(classes, day):
    """Filter classes by the given day."""
    try:
        if isinstance(day, str):
            # If day is a date string
            day_date = datetime.strptime(day, "%Y-%m-%d").date()
            return [cls for cls in classes if cls.start_time.date() == day_date]
        else:
            # If day is a weekday number (0-6)
            return [cls for cls in classes if cls.start_time.weekday() == int(day)]
    except (ValueError, TypeError, AttributeError):
        return []


@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def multiply(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) * float(arg)
    except:
        return 0


@register.filter
def split(value, arg):
    """Split a string by the specified separator."""
    return value.split(arg)


@register.filter
def replace_negative(timestring):
    """Remove negative sign from timesince output"""
    if isinstance(timestring, str) and timestring.startswith("-"):
        return timestring[1:]
    return timestring
