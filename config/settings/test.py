"""Test settings."""
from .base import *  # noqa: F401,F403
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('TEST_DB_NAME', 'test_pmketoan'),  # noqa: F405
        'USER': os.environ.get('TEST_DB_USER', 'root'),  # noqa: F405
        'PASSWORD': os.environ.get('TEST_DB_PASSWORD', ''),  # noqa: F405
        'HOST': os.environ.get('TEST_DB_HOST', '127.0.0.1'),  # noqa: F405
        'PORT': os.environ.get('TEST_DB_PORT', '3306'),  # noqa: F405
    }
}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Run django-q2 tasks synchronously in tests
Q_CLUSTER = {'sync': True, 'orm': 'default'}

# Faster tests
DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['*']

# Disable debug toolbar (would intercept clicks in E2E tests)
if 'debug_toolbar' in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'debug_toolbar']  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]  # noqa: F405

# Disable Axes brute-force for tests (E2E runs many logins)
AXES_FAILURE_LIMIT = 100000
AXES_COOLOFF_TIME = 0
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ['127.0.0.1', '::1']

