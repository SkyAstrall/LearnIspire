from django import template
from django.utils import timezone
from datetime import datetime, timedelta

register = template.Library()


@register.filter
def add_days(value, days):
    """Add specified number of days to a date string."""
    try:
        if isinstance(value, str):
            value = datetime.strptime(value, "%Y-%m-%d").date()

        new_date = value + timedelta(days=int(days))
        return new_date
    except Exception:
        return value


@register.filter
def filter_by_day(classes, day_date):
    """Filter class queryset by specific day."""
    try:
        if isinstance(day_date, str):
            day_date = datetime.strptime(day_date, "%Y-%m-%d").date()

        filtered_classes = []
        for cls in classes:
            class_date = cls.start_time.date()
            if class_date == day_date:
                filtered_classes.append(cls)

        return filtered_classes
    except Exception:
        return []


@register.filter
def format_time_remaining(value):
    """Format time remaining in countdown format."""
    try:
        target_time = timezone.localtime(value)
        now = timezone.localtime(timezone.now())

        if now > target_time:
            return "Time elapsed"

        diff = target_time - now
        total_seconds = diff.total_seconds()

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception:
        return "00:00:00"


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary using key."""
    return dictionary.get(key)


@register.simple_tag
def get_verbose_name(obj, field_name):
    """Get verbose name of a model field."""
    try:
        return obj._meta.get_field(field_name).verbose_name.title()
    except Exception:
        return field_name.replace("_", " ").title()


@register.filter
def format_currency(value):
    """Format value as Indian currency."""
    try:
        value = float(value)
        if value >= 10000000:  # 1 crore
            value_cr = value / 10000000
            return f"₹{value_cr:.2f} Cr"
        elif value >= 100000:  # 1 lakh
            value_lakh = value / 100000
            return f"₹{value_lakh:.2f} L"
        else:
            return f"₹{value:,.2f}"
    except (ValueError, TypeError):
        return value


@register.filter
def time_ago(value):
    """Format datetime as time ago string."""
    try:
        now = timezone.now()
        diff = now - value

        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f"{days} {'day' if days == 1 else 'days'} ago"
        elif seconds < 2592000:
            weeks = int(seconds // 604800)
            return f"{weeks} {'week' if weeks == 1 else 'weeks'} ago"
        else:
            return value.strftime("%d %b %Y")
    except Exception:
        return str(value)


# New filters for payment system

@register.filter
def get_pricing_rule(subject, profile):
    """
    Get pricing rule for a subject based on student profile.
    
    Usage: {{ subject|get_pricing_rule:profile }}
    """
    from common.models import PricingRule
    
    if not subject or not profile or not profile.grade or not profile.board:
        return None
    
    return PricingRule.objects.filter(
        subject=subject,
        grade=profile.grade,
        board=profile.board,
        is_active=True
    ).first()


@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument.
    
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0