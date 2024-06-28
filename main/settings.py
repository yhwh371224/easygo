import logging
import os

from decouple import config
from datetime import datetime, timedelta 


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = config('SECRET_KEY')

ENVIRONMENT = config('ENVIRONMENT', default='production')

if ENVIRONMENT == 'production':
    DEBUG = config('DEBUG', cast=bool, default=True)
    ALLOWED_HOSTS = ['easygoshuttle.com.au', 'www.easygoshuttle.com.au', '149.28.188.33', '33.188.28.149.in-addr.arpa']

    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True

else:
    DEBUG = True
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'blog.apps.BlogConfig',
    'basecamp.apps.BasecampConfig', 
    'easygo_review.apps.EasygoReviewConfig',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'storages',
    'compressor',
    'corsheaders',
    'paypal.standard.ipn',
    'admin_honeypot',
    'crispy_forms',
    'crispy_bootstrap4',
    'markdownx',
    'axes',
    
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',  # Use curly braces for formatting
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',  # Adjust the logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),  # Adjust the path and filename
            'formatter': 'verbose',  # Use the 'verbose' formatter
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',  # Adjust the logging level as needed
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

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware', 
    'htmlmin.middleware.HtmlMinifyMiddleware', 
    'htmlmin.middleware.MarkRequestMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
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
                'context_processors.recaptcha_site_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

# DATABASES = {
#   'default': {
#       'ENGINE': 'django.db.backends.mysql',
#       'NAME': config('DB_NAME'),
#       'USER': config('DB_USER'),
#       'PASSWORD': config('DB_USER_PASSWORD'),
#       'HOST': config('DB_HOST'),
#       'PORT': '3306',
#       'OPTIONS': {
#           'charset': 'utf8mb4',
#       },      
#   }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
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

WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year in seconds

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

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, '_media')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "LOCATION": os.path.join(BASE_DIR, 'media'),
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
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
        'compressor.filters.cssmin.rCSSMinFilter',
    ],
    'js':[
        'compressor.filters.jsmin.JSMinFilter',
    ]
}

HTML_MINIFY = True
KEEP_COMMENTS_ON_MINIFYING = True

LOGIN_REDIRECT_URL = '/easygo_review/'
LOGOUT_REDIRECT_URL = '/home/'

CORS_ALLOWED_ORIGINS = [
    "https://easygoshuttle.com.au",
    
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

RECAPTCHA_V2_SITE_KEY = config('RECAPTCHA_V2_SITE_KEY')
RECAPTCHA_V2_SECRET_KEY = config('RECAPTCHA_V2_SECRET_KEY')

RECAPTCHA_V3_SITE_KEY = config('RECAPTCHA_V3_SITE_KEY')
RECAPTCHA_V3_SECRET_KEY = config('RECAPTCHA_V3_SECRET_KEY')

MARKDOWNX_MEDIA_PATH = datetime.now().strftime('markdownx/%Y/%m/%d/')

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = 'bootstrap4'

RECIPIENT_EMAIL = config('RECIPIENT_EMAIL')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




