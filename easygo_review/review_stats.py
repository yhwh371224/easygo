"""Google rating + review counts shown across the site.

The Google numbers come from the latest GoogleRatingSnapshot (refreshed weekly
by `manage.py refresh_google_rating`); until the first successful fetch the
last hand-entered values below are used, so a missing key or a failed fetch
never breaks or blanks the page.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('easygo')

FALLBACK_RATING = '4.8'
FALLBACK_COUNT = 376
CACHE_KEY = 'review_stats:v1'
CACHE_SECONDS = 60 * 60

PLACES_URL = 'https://places.googleapis.com/v1/places/{place_id}'
SEARCH_URL = 'https://places.googleapis.com/v1/places:searchText'


def get_review_stats():
    stats = cache.get(CACHE_KEY)
    if stats is not None:
        return stats
    from easygo_review.models import GoogleRatingSnapshot, Post

    snap = GoogleRatingSnapshot.objects.first()
    stats = {
        'google_rating': f"{snap.rating:.1f}" if snap else FALLBACK_RATING,
        'google_review_count': snap.review_count if snap else FALLBACK_COUNT,
        'site_review_count': Post.objects.filter(is_published=True).count(),
    }
    cache.set(CACHE_KEY, stats, CACHE_SECONDS)
    return stats


def clear_review_stats_cache():
    cache.delete(CACHE_KEY)


def _headers(field_mask):
    return {
        'X-Goog-Api-Key': settings.GOOGLE_PLACES_API_KEY,
        'X-Goog-FieldMask': field_mask,
    }


def find_place_ids(query='EasyGo Airport Shuttle'):
    """[(place_id, name, address, rating, count)] — to look up GOOGLE_PLACE_ID once."""
    # EasyGo's profile is a pure service-area business (no public address);
    # without this flag Text Search never returns it.
    body = {'textQuery': query, 'includePureServiceAreaBusinesses': True}
    r = requests.post(SEARCH_URL, json=body, timeout=15, headers=_headers(
        'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount'))
    r.raise_for_status()
    return [
        (p['id'], p.get('displayName', {}).get('text', ''), p.get('formattedAddress', ''),
         p.get('rating'), p.get('userRatingCount'))
        for p in r.json().get('places', [])
    ]


def fetch_google_rating(place_id):
    """(rating, review_count) from Places API (New). Raises on any failure."""
    r = requests.get(PLACES_URL.format(place_id=place_id), timeout=15,
                     headers=_headers('rating,userRatingCount'))
    r.raise_for_status()
    data = r.json()
    rating, count = data.get('rating'), data.get('userRatingCount')
    if rating is None or not count:
        raise ValueError(f'Places API returned no rating/count: {data}')
    return float(rating), int(count)
