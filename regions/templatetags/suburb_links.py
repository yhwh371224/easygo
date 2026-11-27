"""{% suburb_url region_slug suburb_slug 'shuttle' %} — 서버브 페이지 주소.

shuttle/transfer 가 합쳐진 서버브(regions/suburb_merge.py)는 남은 페이지 주소를 줘서
내부 링크가 301 을 거치지 않게 한다. 합치기가 꺼져 있으면 요청한 서비스 주소 그대로.
"""

from django import template

from regions.suburb_merge import suburb_url as _suburb_url

register = template.Library()


@register.simple_tag
def suburb_url(region_slug, suburb_slug, service='shuttle'):
    return _suburb_url(region_slug, suburb_slug, service)
