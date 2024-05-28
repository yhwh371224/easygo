from django import template

register = template.Library()

@register.filter
def filter_range(value):
    return range(int(value))

@register.filter
def subtract_from_five(value):
    return range(5 - int(value))