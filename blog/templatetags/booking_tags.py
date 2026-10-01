from django import template

from blog.models import FullyBookedDate

register = template.Library()


@register.simple_tag
def fully_booked_dates():
    """Upcoming dates marked full in the admin calendar: {region slug | '*': [ISO dates]}."""
    return FullyBookedDate.upcoming_by_region()
