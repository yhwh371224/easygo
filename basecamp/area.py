def get_suburbs():
    suburbs = {
        'Hotels In CBD': {
            'price': 35,
            'image_url': '/static/basecamp/photos/maps/sydney-city-hotels.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $35, and private rides starting from $60',
            'extra': ''
        },
        'Chatswood': {
            'price': 70,
            'image_url': '/static/basecamp/photos/maps/chatswood.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $70, and private rides starting from $90',
            'extra': '*additional $10 per person*'
        },
        'St Ives': {
            'price': 90,
            'image_url': '/static/basecamp/photos/maps/st-ives.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $90, and private rides starting from $100',
            'extra': '*additional $10 per person*'
        },
        'Ryde': {
            'price': 70,
            'image_url': '/static/basecamp/photos/maps/ryde.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $70, and private rides starting from $90',
            'extra': '*additional $10 per person*'
        },
        'Hornsby': {
            'price': 110,
            'image_url': '/static/basecamp/photos/maps/hornsby.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $110, and private rides starting from $125',
            'extra': '*additional $10 per person*'
        },
        'Blacktown': {
            'price': 110,
            'image_url': '/static/basecamp/photos/maps/blacktown.webp',
            'description': 'EasyGo Airport Shuttle offers shared rides starting from $110, and private rides starting from $125',
            'extra': '*additional $10 per person*'
        },

    }
    return suburbs

suburbs = get_suburbs()


# 캐러셀 이름 → Sydney RegionSuburb slug
_CAROUSEL_SLUGS = {'Hotels In CBD': 'sydney-cbd'}


def get_carousel_suburbs():
    """홈 캐러셀용. get_suburbs() 의 하드코딩 가격과 문구("shared rides starting from
    $35")는 실제 견적·"100% private" 안내와 안 맞아서, 가격과 설명을 실제 가격 규칙으로
    다시 만든다. RegionSuburb 를 못 찾으면 그 카드는 원래 값을 그대로 쓴다."""
    from django.utils.text import slugify
    from regions.models import RegionSuburb

    cards = get_suburbs()
    slugs = {name: _CAROUSEL_SLUGS.get(name, slugify(name)) for name in cards}
    found = {
        s.slug: s for s in
        RegionSuburb.objects.filter(region__slug='sydney', is_active=True, slug__in=slugs.values())
    }
    for name, card in cards.items():
        suburb = found.get(slugs[name])
        price = suburb.from_price if suburb else None
        if not price:
            continue
        card['price'] = price
        card['description'] = f"Private airport transfer for 1–2 passengers from ${price}."
        card['extra'] = '*additional $10 per person from the 3rd passenger*'
    return cards
