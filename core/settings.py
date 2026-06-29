"""
Django settings for core project (Production Ready 🚀)
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta
from celery.schedules import crontab




# =====================================================
# BASE DIR
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =====================================================
# ENV LOAD
# =====================================================
load_dotenv()


# =====================================================
# SECURITY
# =====================================================
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "fallback-secret-key"
)

DEBUG = os.getenv(
    "DEBUG",
    "True"
) == "True"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "*"
).split(",")


# =====================================================
# APPLICATIONS
# =====================================================
INSTALLED_APPS = [

    # django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',

    'rest_framework_simplejwt',

    'rest_framework_simplejwt.token_blacklist',

    'corsheaders',

    'channels',

    # local apps
    'apps.users',

    'apps.hospitals',

    'apps.blood_requests',

    'apps.admin_panel',

    'apps.notifications',
]


# =====================================================
# MIDDLEWARE
# =====================================================
MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',

    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =====================================================
# URL / WSGI / ASGI
# =====================================================
ROOT_URLCONF = 'core.urls'

WSGI_APPLICATION = 'core.wsgi.application'

ASGI_APPLICATION = 'core.asgi.application'


# =====================================================
# TEMPLATES
# =====================================================
TEMPLATES = [
    {
        'BACKEND':
            'django.template.backends.django.DjangoTemplates',

        'DIRS': [],

        'APP_DIRS': True,

        'OPTIONS': {

            'context_processors': [

                'django.template.context_processors.request',

                'django.contrib.auth.context_processors.auth',

                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# =====================================================
# DATABASE
# =====================================================
DATABASES = {

    'default': {

        'ENGINE':
            'django.db.backends.postgresql',

        'NAME':
            os.getenv(
                'DB_NAME',
                'blood_db'
            ),

        'USER':
            os.getenv(
                'DB_USER',
                'postgres'
            ),

        'PASSWORD':
            os.getenv(
                'DB_PASSWORD',
                'postgres'
            ),

        'HOST':
            os.getenv(
                'DB_HOST',
                'db'
            ),

        'PORT':
            os.getenv(
                'DB_PORT',
                '5432'
            ),
    }
}


# =====================================================
# REDIS CACHE
# =====================================================
CACHES = {

    "default": {

        "BACKEND":
            "django_redis.cache.RedisCache",

        "LOCATION":
            "redis://redis:6379/1",

        "OPTIONS": {

            "CLIENT_CLASS":
                "django_redis.client.DefaultClient",

        }
    }
}


# =====================================================
# CHANNELS (WEBSOCKET)
# =====================================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}


# =====================================================
# AUTH USER MODEL
# =====================================================
AUTH_USER_MODEL = 'users.User'


# =====================================================
# PASSWORD VALIDATORS
# =====================================================
AUTH_PASSWORD_VALIDATORS = [

    {
        'NAME':
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.MinimumLengthValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.CommonPasswordValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =====================================================
# INTERNATIONALIZATION
# =====================================================
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# =====================================================
# STATIC / MEDIA
# =====================================================
STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# =====================================================
# DEFAULT AUTO FIELD
# =====================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =====================================================
# DJANGO REST FRAMEWORK
# =====================================================
REST_FRAMEWORK = {

    'DEFAULT_AUTHENTICATION_CLASSES': (

        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (

        'rest_framework.permissions.AllowAny',
    ),

    'DEFAULT_THROTTLE_CLASSES': [

        'rest_framework.throttling.AnonRateThrottle',

        'rest_framework.throttling.UserRateThrottle',
    ],

    'DEFAULT_THROTTLE_RATES': {

        'anon': '10000/day',

        'user': '100000/day',
    }
}


# =====================================================
# JWT SETTINGS
# =====================================================
SIMPLE_JWT = {

    'ACCESS_TOKEN_LIFETIME':
        timedelta(days=7),

    'REFRESH_TOKEN_LIFETIME':
        timedelta(days=30),

    'ROTATE_REFRESH_TOKENS':
        True,

    'BLACKLIST_AFTER_ROTATION':
        True,

    'UPDATE_LAST_LOGIN':
        True,
}


# =====================================================
# CELERY
# =====================================================
CELERY_BROKER_URL = "redis://redis:6379/0"

CELERY_RESULT_BACKEND = "redis://redis:6379/0"

CELERY_ACCEPT_CONTENT = ['json']

CELERY_TASK_SERIALIZER = 'json'


# =====================================================
# CELERY BEAT
# =====================================================
CELERY_BEAT_SCHEDULE = {

    'fallback-every-minute': {

        'task':
            'apps.blood_requests.tasks.fallback_requests',

        'schedule': 60.0,
    },
}


# =====================================================
# CORS
# =====================================================

# DEVELOPMENT
if DEBUG:

    CORS_ALLOW_ALL_ORIGINS = True

else:

    # PRODUCTION
    CORS_ALLOWED_ORIGINS = [

        "https://yourdomain.com",

        "https://api.yourdomain.com",
    ]


# =====================================================
# CSRF TRUSTED ORIGINS
# =====================================================
CSRF_TRUSTED_ORIGINS = [

    "https://yourdomain.com",

    "https://api.yourdomain.com",
]


# =====================================================
# SECURITY SETTINGS
# =====================================================
SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = 'DENY'

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)

CSRF_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_SECURE = not DEBUG


# =====================================================
# PRODUCTION SSL SETTINGS
# =====================================================
if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True


# =====================================================
# LOGGING
# =====================================================
LOGGING = {

    'version': 1,

    'disable_existing_loggers': False,

    'handlers': {

        'console': {

            'class':
                'logging.StreamHandler',
        },
    },

    'root': {

        'handlers': ['console'],

        'level': 'INFO',
    },
}