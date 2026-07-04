"""Production settings — visota.net (Docker + WhiteNoise + Traefik)."""
import os
from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'visota.net,www.visota.net,localhost,web').split(',')

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-change-in-prod')

# ===== Security =====
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') != 'False'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') != 'False'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ===== Static + Media =====
# WhiteNoise serves static files directly from Gunicorn — no Nginx needed
STATIC_ROOT = os.environ.get('STATIC_ROOT', '/app/staticfiles/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/app/media/')
# Base URL for WeasyPrint to resolve relative image URLs (logos, stamps) when rendering PDFs.
# Validate scheme to prevent SSRF (file://, data://, etc.) if env var is tampered.
from urllib.parse import urlparse
_default_base_url = 'https://visota.net'
_parsed_base = urlparse(os.environ.get('BASE_URL', _default_base_url) or _default_base_url)
if _parsed_base.scheme not in ('http', 'https'):
    BASE_URL = _default_base_url
else:
    BASE_URL = _parsed_base.geturl()

# WhiteNoise caching headers (immutable + max-age)
WHITENOISE_MAX_AGE = 31536000  # 1 year
WHITENOISE_MANIFEST_STRICT = False  # Don't crash if file missing

# ===== Database =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'visota'),
        'USER': os.environ.get('DB_USER', 'visota'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ===== Email =====
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'noreply@visota.net')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'Visota <{EMAIL_HOST_USER}>'

# ===== Axes (brute-force protection) =====
AXES_FAILURE_LIMIT = int(os.environ.get('AXES_FAILURE_LIMIT', '5'))
AXES_COOLOFF_TIME = int(os.environ.get('AXES_COOLOFF_TIME', '1'))
AXES_RESET_ON_SUCCESS = True

# ===== django-q2 =====
Q_CLUSTER = {
    'name': 'visota',
    'workers': int(os.environ.get('Q_WORKERS', '4')),
    'recycle': 500,
    'timeout': 60,
    'retry': 120,
    'orm': 'default',
}

# ===== Cache =====
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 300,
    }
}

# ===== Logging (structured JSON with PII scrubbing) =====
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'gunicorn': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
    },
}

# Enable structured JSON logging with PII scrubbing in production
if os.environ.get('STRUCTURED_LOGGING', 'true').lower() in ('true', '1', 'yes'):
    from apps.core.logging_utils import configure_structured_logging
    configure_structured_logging()

# ===== Metrics (Prometheus format via /metrics endpoint) =====
PROMETHEUS_METRICS_ENABLED = os.environ.get('PROMETHEUS_METRICS_ENABLED', 'false').lower() in ('true', '1')

# ===== Sentry (optional) =====
if sentry_dsn := os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(dsn=sentry_dsn, integrations=[DjangoIntegration()], traces_sample_rate=0.1)
