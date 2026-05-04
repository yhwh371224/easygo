def region_price_detail(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    request.region = region
    from basecamp.views.misc_inquirys import price_detail
    return price_detail(request)


def region_inquiry_details1(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    request.region = region
    from basecamp.views.inquirys import inquiry_details1
    return inquiry_details1(request)


def region_p2p_detail(request, region_slug):
    from basecamp.views.inquirys import p2p_detail
    return p2p_detail(request)


def region_p2p_booking(request, region_slug):
    from basecamp.views.pages import p2p_booking
    return p2p_booking(request)


def region_p2p_multi(request, region_slug):
    from basecamp.views.pages import p2p_multi
    return p2p_multi(request)


def region_p2p_booking_detail(request, region_slug):
    from basecamp.views.bookings import p2p_booking_detail
    return p2p_booking_detail(request)
