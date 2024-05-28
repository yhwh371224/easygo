from django import template

register = template.Library()

def filter_range(start, end):
    return range(start, end)