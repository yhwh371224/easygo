import os
from datetime import datetime

from decouple import config


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET_KEY = config('SECRET_KEY')
SECRET_ADMIN_URL = config('SECRET_ADMIN_URL', default='secure-admin-x9k2p7')

ENVIRONMENT = config('ENVIRONMENT', default='production')
DEBUG = config('DEBUG', cast=bool, default=False)
if ENVIRONMENT != 'production':
    DEBUG = True

SITE_ID = 1
SITE_URL = 'https://easygoshuttle.com.au'

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
    'email_agent.apps.EmailAgentConfig',
    'posting_agent.apps.PostingAgentConfig',
    'articles.apps.ArticlesConfig',
    'regions.apps.RegionsConfig',
    'admin_honeypot',
    'allauth',
    'allauth.account',
    'storages',
    'corsheaders',
    'paypal.standard.ipn',
    'markdownx',
    'csp',
    'axes',
]

MIDDLEWARE = [
    'main.middlewares.cloudflare.CloudflareMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'htmlmin.middleware.HtmlMinifyMiddleware',
    'htmlmin.middleware.MarkRequestMiddleware',
    'csp.middleware.CSPMiddleware',
    'main.middlewares.login_control.AccountLoginMethodMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'main.middlewares.block_ip_middleware.BlockIPEmailMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'main.middlewares.csrf_exempt_urls.CsrfExemptMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'axes.middleware.AxesMiddleware',
    'regions.middleware.RegionMiddleware',
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
                'csp.context_processors.nonce',
                'basecamp.context_processors.add_custom_context',
                'basecamp.context_processors.bank_settings',
                'basecamp.context_processors.turnstile_site_key',
                'basecamp.context_processors.navbar_defaults',
                'regions.context_processors.region_config',
                'basecamp.context_processors.google_analytics',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Sydney'
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

APPEND_SLASH = True
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
MARKDOWNX_MEDIA_PATH = datetime.now().strftime('markdownx/%Y/%m/%d/')

LOGIN_REDIRECT_URL = '/easygo_review/'
LOGOUT_REDIRECT_URL = '/'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
if ENVIRONMENT != 'production':
    STATICFILES_DIRS.append(os.path.join(BASE_DIR, 'docs'))

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "LOCATION": os.path.join(BASE_DIR, 'media'),
    },
    "staticfiles": {
        # "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

HTML_MINIFY = True
KEEP_COMMENTS_ON_MINIFYING = True

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'my_session_cookie'
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = '/'
SESSION_COOKIE_SIGNED = True

DEFAULT_BANK_CODE = 'anz'
GOOGLE_ANALYTICS_ID = 'G-YZ51V54FK0'
