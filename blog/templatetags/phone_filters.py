from django import template

register = template.Library()

@register.filter
def format_au_phone(value):
    """Convert +61XXXXXXXXX to 0XXX XXX XXX format."""
    if not value:
        return value
    number = str(value).strip().replace(' ', '')
    if number.startswith('+61'):
        number = '0' + number[3:]
    if len(number) == 10:
        return f"{number[:4]} {number[4:7]} {number[7:]}"
    return number
