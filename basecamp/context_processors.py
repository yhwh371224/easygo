from django.conf import settings


def turnstile_site_key(request):
    return {
        'CLOUDFLARE_TURNSTILE_SITE_KEY': settings.CLOUDFLARE_TURNSTILE_SITE_KEY,
        'TURNSTILE_DISABLED': getattr(settings, 'TURNSTILE_DISABLED', False),
    }

def add_custom_context(request):
    return {
        'is_nav_sidebar_enabled': False,
        'is_popup': False,
        'site_header': 'EasyGo Administration',
        'site_title': 'EasyGo Admin',   
        'subtitle': 'Welcome to the admin panel',  
    }

def bank_settings(request):
    return {
        'DEFAULT_BANK': getattr(settings, 'DEFAULT_BANK_CODE', 'anz')
    }

def navbar_defaults(request):
    return {
        'navbar_theme': 'navbar-dark'  # 기본값
    }