from django import template

register = template.Library()

@register.filter
def filter_range(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    return range(value)

@register.filter
def subtract_from_five(value):
    return range(5 - int(value))