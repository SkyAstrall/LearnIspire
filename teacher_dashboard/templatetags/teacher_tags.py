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
def filter_by_day(items, day):
    """
    Filter a list of items by day.

    This filter can handle two types of filtering:
    1. For Class objects: Filter by matching their start_time.date() with the provided day
    2. For Availability objects: Filter by matching their day_of_week attribute with the provided day

    Args:
        items: A queryset of Class or Availability objects
        day: Either a string date in format 'YYYY-MM-DD' or an integer day of week (0-6)

    Returns:
        Filtered list of items
    """
    result = []

    # Handle empty items
    if not items:
        return result

    # Try to determine the type of filtering based on the first item
    first_item = items[0] if isinstance(items, list) and len(items) > 0 else None

    if not first_item:
        # Try to get first item from queryset
        try:
            first_item = items.first()
        except:
            # If we can't get the first item, return empty list
            return result

    # Case 1: Filtering Availability objects by day_of_week
    if hasattr(first_item, "day_of_week"):
        try:
            day_int = int(day)
            return [item for item in items if item.day_of_week == day_int]
        except (ValueError, TypeError):
            # If day is not an integer, return empty list
            return result

    # Case 2: Filtering Class objects by start_time date
    elif hasattr(first_item, "start_time"):
        # Convert day string to datetime.date object if it's a string
        if isinstance(day, str):
            try:
                day_date = datetime.strptime(day, "%Y-%m-%d").date()
            except ValueError:
                return result
        else:
            day_date = day

        # Filter items where the date part of start_time matches day_date
        result = []
        for item in items:
            # Check if start_time is a datetime object (has date method)
            if hasattr(item.start_time, "date"):
                if item.start_time.date() == day_date:
                    result.append(item)

        return result

    # Default: Return empty list if items don't match any expected format
    return result


@register.filter
def add_days(date_str, days):
    """
    Add a number of days to a date string.

    Args:
        date_str: A string date in format 'YYYY-MM-DD'
        days: Number of days to add

    Returns:
        A date string in the same format
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    result = date_obj + timedelta(days=int(days))
    return result.strftime("%Y-%m-%d")


@register.filter
def split(value, delimiter):
    """
    Split a string into a list using the given delimiter.

    Args:
        value: The string to split
        delimiter: The delimiter to use

    Returns:
        A list of strings
    """
    return value.split(delimiter)


@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


