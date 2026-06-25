"""Production settings — visota.net."""
import os
from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'visota.net,www.visota.net').split(',')

SECRET_KEY = os.environ['SECRET_KEY']

# Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static + Media
STATIC_ROOT = os.environ.get('STATIC_ROOT', '/opt/visota/staticfiles/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/opt/visota/media/')

# Database (read from env)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'visota'),
        'USER': os.environ.get('DB_USER', 'visota'),
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Email (SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'noreply@visota.net')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'Visota <{EMAIL_HOST_USER}>'

# Axes — allow localhost, stricter for external
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True

# django-q2
Q_CLUSTER = {
    'name': 'visota',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'retry': 120,
    'orm': 'default',
}

# Cache (DB-backed, no Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 300,
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get('LOG_FILE', '/var/log/visota/django.log'),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {'handlers': ['file'], 'level': 'INFO', 'propagate': True},
        'apps': {'handlers': ['file'], 'level': 'INFO', 'propagate': True},
    },
}

# Sentry (optional)
if sentry_dsn := os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(dsn=sentry_dsn, integrations=[DjangoIntegration()], traces_sample_rate=0.1)
