import logging
import os

from decouple import config
from datetime import datetime, timedelta 
from csp.constants import NONCE
from django.core.exceptions import DisallowedHost


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = config('SECRET_KEY')

ENVIRONMENT = config('ENVIRONMENT', default='production')

if ENVIRONMENT == 'production':
    DEBUG = config('DEBUG', cast=bool, default=False)
    ALLOWED_HOSTS = [
        'easygoshuttle.com.au', 
        'www.easygoshuttle.com.au', 
        '45.32.241.98']

    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = False
    X_FRAME_OPTIONS = 'DENY'
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ("'self'",),
            'script-src': (
                "'self'",
                'https://cdnjs.cloudflare.com',
                'https://challenges.cloudflare.com', 
                'https://www.paypal.com',
                'https://ajax.googleapis.com',
                NONCE,
            ),
            'frame-src': (
                "'self'",
                'https://challenges.cloudflare.com',
            ),
            'connect-src': (          
                "'self'",
                'https://challenges.cloudflare.com',
                'https://www.paypal.com',
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
            ),
            'frame-ancestors': ("'self'",),
        }
    }
    SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'
    
    COMPRESS_OFFLINE = True

else:
   DEBUG = True
   ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
   COMPRESS_OFFLINE = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'blog.apps.BlogConfig',
    'basecamp.apps.BasecampConfig', 
    'easygo_review.apps.EasygoReviewConfig',
    'admin_honeypot',
    # 'honeypot',  
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'storages',
    'compressor',
    'corsheaders',
    'paypal.standard.ipn',
    'markdownx',
    'csp',
    'axes',    
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },

    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
        'email_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/email_reminders.log'),
            'formatter': 'verbose',
        },
        'sms_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/sms.log'),
            'formatter': 'verbose',
        },
        'console': {  
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'blog.management.commands.booking_reminder': {
            'handlers': ['email_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'sms': {
            'handlers': ['sms_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'easygo': {
            'handlers': ['file', 'console'],  
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


CELERY_BROKER_URL = config('CELERY_BROKER', 'redis://redis:6379')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Australia/Sydney'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

SITE_ID = 1
SITE_URL = 'https://easygoshuttle.com.au'

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',     
    'htmlmin.middleware.HtmlMinifyMiddleware', 
    'htmlmin.middleware.MarkRequestMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  
    'main.middlewares.login_control.AccountLoginMethodMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'main.middlewares.block_ip_middleware.BlockIPEmailMiddleware',  
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 
    'allauth.account.middleware.AccountMiddleware',    
    'axes.middleware.AxesMiddleware',
]

AXES_FAILURE_LIMIT = 7  
AXES_COOLOFF_TIME = timedelta(minutes=60)  
AXES_LOCKOUT_MESSAGE = "Access locked. Please contact the office"

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',                
                'csp.context_processors.nonce',
                'basecamp.context_processors.add_custom_context',
                'basecamp.context_processors.bank_settings',
                'basecamp.context_processors.turnstile_site_key', 

            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
    # 'backup': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'NAME': config('DB_NAME'),
    #     'USER': config('DB_USER'),
    #     'PASSWORD': config('DB_USER_PASSWORD'),
    #     'HOST': config('DB_HOST', default='localhost'),
    #     'PORT': '3306',
    # },
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Australia/Sydney'

USE_I18N = True

USE_L10N = True

USE_TZ = True

AUTHENTICATION_BACKENDS = (    
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'blog.auth_backends.PostEmailBackend',
)

BLOCKED_IP_FILE = "/etc/django/blocked_ips.txt"
BLOCKED_EMAIL_FILE = "/etc/django/blocked_emails.txt"

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID'),
            'secret': config('GOOGLE_CLIENT_SECRET'),
            'key': ''
        }
    }
}

SOCIALACCOUNT_LOGIN_ON_GET=True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "LOCATION": os.path.join(BASE_DIR, 'media'),
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

COMPRESS_ENABLED = not DEBUG  
COMPRESS_CSS_HASHING_METHOD = 'content'
COMPRESS_FILTERS = {
    'css':[
        'compressor.filters.css_default.CssAbsoluteFilter',
    ],
    'js':[
        'compressor.filters.jsmin.JSMinFilter',
    ]
}

HTML_MINIFY = True
KEEP_COMMENTS_ON_MINIFYING = True

LOGIN_REDIRECT_URL = '/easygo_review/'
LOGOUT_REDIRECT_URL = '/'

CORS_ALLOWED_ORIGINS = [
    "https://easygoshuttle.com.au",
    "https://www.easygoshuttle.com.au",
    
]

CORS_ALLOW_METHODS = [ 'GET', 'POST', ]

CORS_ALLOW_HEADERS = [ 'Content-Type', 'X-CSRFToken', ]

#PayPal settings
PAYPAL_MODE = 'live'  
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET')
PAYPAL_RECEIVER_EMAIL = 'info@easygoshuttle.com.au'
PAYPAL_IPN_URL = 'https://easygoshuttle.com.au/paypal_ipn/'

# Stripe settings
STRIPE_MODE = 'live' 
STRIPE_LIVE_SECRET_KEY = config('STRIPE_LIVE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY')

# Email settings
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_BACKEND = config('EMAIL_BACKEND')

# Service Account Files
GMAIL_SERVICE_ACCOUNT_FILE = config('GMAIL_SERVICE_ACCOUNT_FILE')
CALENDAR_SERVICE_ACCOUNT_FILE = config('CALENDAR_SERVICE_ACCOUNT_FILE')

# Cloudfare Turnstile settings
TURNSTILE_DISABLED = (ENVIRONMENT != 'production')
CLOUDFLARE_TURNSTILE_SITE_KEY = config('CLOUDFLARE_TURNSTILE_SITE_KEY')
CLOUDFLARE_TURNSTILE_SECRET_KEY = config('CLOUDFLARE_TURNSTILE_SECRET_KEY')

# Honeypot settings
# HONEYPOT_FIELD_NAME = 'phone_verify'  # replaced by Cloudflare Turnstile
# HONEYPOT_VALUE = ''

# MySQL Backup Database Configuration
MYSQL_CONFIG = {
    'user': config('DB_USER'),
    'password': config('DB_USER_PASSWORD'),
    'host': config('DB_HOST'),
    'database': config('DB_NAME')
}

# Banking details (anz, commbank, westpac, nab)
DEFAULT_BANK_CODE = 'nab'

# GOOGLE REVIEW URL
GOOGLE_REVIEW_URL = config('GOOGLE_REVIEW_URL')

MARKDOWNX_MEDIA_PATH = datetime.now().strftime('markdownx/%Y/%m/%d/')

SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'my_session_cookie'
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = '/'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SIGNED = True

RECIPIENT_EMAIL = config('RECIPIENT_EMAIL')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

logging.getLogger('django.security.DisallowedHost').setLevel(logging.CRITICAL)
