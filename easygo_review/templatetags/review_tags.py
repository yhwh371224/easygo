from django import template
from django.core.cache import cache
from django.utils.html import strip_tags
from django.utils.text import Truncator

from easygo_review.models import Post

register = template.Library()

CACHE_SECONDS = 60 * 30


def _display_name(name):
    """'Jenny Koschutzke' → 'Jenny K.' — full surnames stay on the review page only."""
    parts = (name or '').split()
    if not parts:
        return 'EasyGo customer'
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."


def _recent_reviews(keyword, limit):
    cache_key = f"review_testimonials:{(keyword or '').lower()}:{limit}"
    reviews = cache.get(cache_key)
    if reviews is not None:
        return reviews

    qs = Post.objects.filter(is_published=True, rating__gte=4).exclude(content='')
    picked = []
    if keyword:
        picked = list(qs.filter(content__icontains=keyword)[:limit])
    seen = {p.pk for p in picked}
    if len(picked) < limit:
        picked += [p for p in qs.exclude(pk__in=seen)[:limit - len(picked)]]

    reviews = [{
        'text': Truncator(strip_tags(p.get_markdown_content()).strip()).chars(320),
        'name': _display_name(p.name),
        'rating': p.rating,
        'date': p.date,
        'url': p.get_absolute_url(),
    } for p in picked]
    cache.set(cache_key, reviews, CACHE_SECONDS)
    return reviews


@register.inclusion_tag('easygo_review/includes/review_testimonials.html')
def review_testimonials(heading='What Our Customers Say', keyword='', limit=5):
    """Latest real customer reviews from /easygo_review/ as the testimonial slider.

    Reviews mentioning `keyword` (e.g. a city name) come first, then the
    latest others fill the rest.
    """
    return {'heading': heading, 'reviews': _recent_reviews(keyword, limit)}
