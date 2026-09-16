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

def survey_discount(request):
    """홈 배너 문구의 할인 금액. 설정값을 그대로 내려서 .env 에서 금액을
    바꾸면 배너와 메일이 같이 따라오게 한다."""
    return {
        'SURVEY_DISCOUNT_AMOUNT': getattr(settings, 'SURVEY_DISCOUNT_AMOUNT', 10)
    }


def bank_settings(request):
    return {
        'DEFAULT_BANK': getattr(settings, 'DEFAULT_BANK_CODE', 'anz')
    }

def navbar_defaults(request):
    return {
        'navbar_theme': 'navbar-dark'  # 기본값
    }

def google_analytics(request):
    if settings.DEBUG:
        return {}
    return {'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', '')}

def rebook_error(request):
    return {'rebook_error': request.session.pop('rebook_error', None)}

def google_review_url(request):
    return {'google_review_url': getattr(settings, 'GOOGLE_REVIEW_URL', '')}
