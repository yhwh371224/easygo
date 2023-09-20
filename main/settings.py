import os
import logging
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from decouple import config


sentry_sdk.init(
    dsn= config("dsn"),
    integrations=[DjangoIntegration()],
    
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = config('SECRET_KEY')

#DEBUG = True
DEBUG = config('DEBUG', cast=bool, default=True)


ALLOWED_HOSTS = ['easygoshuttle.com.au', 'www.easygoshuttle.com.au', '54.206.144.94']


INSTALLED_APPS = [
    'suit',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'blog.apps.BlogConfig',
    'basecamp.apps.BasecampConfig',
    'crispy_forms',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',    
    'rangefilter',
    'twilio',
    'storages',
    'compressor',
    'django_celery_beat',
    'paypal.standard.ipn',
    'corsheaders',
    'admin_honeypot',
    'defender',

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
            'level': 'INFO',  # Adjust the logging level as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),  # Adjust the path and filename
            'formatter': 'verbose',  # Use the 'verbose' formatter
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',  # Adjust the logging level as needed
            'propagate': True,
        },
        'google_calendar': {  # Create a custom logger for your Google Calendar integration
            'handlers': ['file'],
            'level': 'INFO',  # Adjust the logging level as needed
            'propagate': True,
        },
    },
}


# CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_BROKER_URL = config('CELERY_BROKER', 'redis://redis:6379')
CELERY_RESULT_BACKEND = config('CELERY_BACKEND', 'redis://redis:6379')
if CELERY_RESULT_BACKEND == 'django-db':
    INSTALLED_APPS += ['django_celery_results',]
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Australia/Sydney'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware', 
    'htmlmin.middleware.HtmlMinifyMiddleware', 
    'htmlmin.middleware.MarkRequestMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'defender.middleware.FailedLoginMiddleware',

]

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
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

# DATABASES = {
#   'default': {
#       'ENGINE': 'django.db.backends.postgresql_psycopg2',
#       'NAME': config('DB_NAME'),
#       'USER': config('DB_USER'),
#       'PASSWORD': config('DB_USER_PASSWORD'),
#       'HOST': config('DB_HOST'),
#       'PORT': '5432',
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
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
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
    'django.contrib.auth.backends.ModelBackend',   
    'allauth.account.auth_backends.AuthenticationBackend',
)


ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

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


LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/home/'


#PayPal settings
PAYPAL_MODE = 'live'  
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET')
PAYPAL_RECEIVER_EMAIL = 'info@easygoshuttle.com.au'
PAYPAL_IPN_URL = 'https://easygoshuttle.com.au/paypal_ipn/'


#CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://easygoshuttle.com.au',
    'https://easygoshuttle.com.au',
]


# Email settings
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_BACKEND = config('EMAIL_BACKEND')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000 
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
