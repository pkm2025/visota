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
