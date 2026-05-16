from decouple import config

from .base import ENVIRONMENT


if ENVIRONMENT == 'production':
    ALLOWED_HOSTS = config(
        'PRO_ALLOWED_HOSTS',
        cast=lambda v: [s.strip() for s in v.split(',')]
    )
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = False
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_AGE = 3600
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ("'self'",),
            'script-src': (
                "'self'",
                'https://cdnjs.cloudflare.com',
                'https://ajax.googleapis.com',
                'https://www.googletagmanager.com',
                'https://challenges.cloudflare.com',
                'https://*.paypal.com',
                'https://*.paypalobjects.com',
                "'unsafe-inline'",
                # NONCE,
            ),
            'style-src': (
                "'self'",
                'https://fonts.googleapis.com',
                "'unsafe-inline'",
            ),
            'font-src': (
                "'self'",
                'https://fonts.gstatic.com',
            ),
            'img-src': (
                "'self'",
                "data:",
                'https://s3.ap-southeast-2.amazonaws.com/easygoshuttle.com.au/',
                'https://www.paypalobjects.com',
                'https://*.paypal.com',
                'https://www.google-analytics.com',
            ),
            'connect-src': (
                "'self'",
                'https://challenges.cloudflare.com',
                'https://*.paypal.com',
                'https://*.paypalobjects.com',
                'https://www.google-analytics.com',
                'https://analytics.google.com',
                'https://www.googletagmanager.com',
            ),
            'frame-src': (
                "'self'",
                'https://challenges.cloudflare.com',
                'https://*.paypal.com',
            ),
            'frame-ancestors': ("'self'",),
        }
    }
else:
    ALLOWED_HOSTS = config(
        'DEV_ALLOWED_HOSTS',
        default='127.0.0.1,localhost',
        cast=lambda v: [s.strip() for s in v.split(',')]
    )
    TURNSTILE_DISABLED = True
    SESSION_COOKIE_SECURE = False
    SESSION_EXPIRE_AT_BROWSER_CLOSE = False

CORS_ALLOWED_ORIGINS = [
    "https://easygoshuttle.com.au",
    "https://www.easygoshuttle.com.au",
]

CSRF_TRUSTED_ORIGINS = [
    'https://easygoshuttle.com.au',
    'https://www.easygoshuttle.com.au',
]

CORS_ALLOW_METHODS = ['GET', 'POST']
CORS_ALLOW_HEADERS = ['Content-Type', 'X-CSRFToken']

BLOCKED_IP_FILE = "/etc/django/blocked_ips.txt"
BLOCKED_EMAIL_FILE = "/etc/django/blocked_emails.txt"
