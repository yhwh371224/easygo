from django.conf import settings


def recaptcha_site_key(request):
    return {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
        'RECAPTCHA_V3_SITE_KEY': settings.RECAPTCHA_V3_SITE_KEY,
    }