from django import template

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