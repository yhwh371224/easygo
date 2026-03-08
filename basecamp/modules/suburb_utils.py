from basecamp.area_home import get_home_suburbs


def get_sorted_suburbs():
    raw = get_home_suburbs()
    fixed = [
        "Hotels In City",
        "Sydney Int'l Airport",
        "Sydney Domestic Airport",
        "WhiteBay cruise terminal",
        "Overseas cruise terminal"
    ]
    remaining = sorted([item for item in raw if item not in fixed])
    return fixed + remaining
