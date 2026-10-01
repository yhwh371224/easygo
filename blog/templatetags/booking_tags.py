from django import template

from blog.models import FullyBookedDate

register = template.Library()


@register.simple_tag
def fully_booked_dates():
    """Upcoming dates marked full in the admin calendar, as ISO strings."""
    return FullyBookedDate.upcoming_iso()
