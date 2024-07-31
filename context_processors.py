from django.conf import settings


def recaptcha_site_key(request):
    return {
        'RECAPTCHA_V2_SITE_KEY': settings.RECAPTCHA_V2_SITE_KEY,
        'RECAPTCHA_V3_SITE_KEY': settings.RECAPTCHA_V3_SITE_KEY,
    }

def add_custom_context(request):
    return {
        'is_nav_sidebar_enabled': False,
        'is_popup': False,
        'site_header': 'EasyGo Administration',
        'site_title': 'EasyGo Admin',   
        'subtitle': 'Welcome to the admin panel',  
    }