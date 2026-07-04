"""Development settings."""
from .base import *  # noqa: F401,F403
import os

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Axes brute-force lockout for dev (frequent test runs)
AXES_FAILURE_LIMIT = 10000
AXES_COOLOFF_TIME = 1
# Only lock out remote, not localhost (for E2E tests)
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ['127.0.0.1', '::1']

# Enable django-silk for performance profiling (dev only, if installed)
try:
    import silk  # noqa: F401
    if 'silk' not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS = INSTALLED_APPS + ['silk']  # noqa: F405
        MIDDLEWARE = MIDDLEWARE + ['silk.middleware.SilkyMiddleware']  # noqa: F405
        SILKY_PYTHON_PROFILER = True
        SILKY_INTERCEPT_PERCENT = 10
except ImportError:
    pass

# Product analytics (GA4 — set GA4_MEASUREMENT_ID to enable)
GA4_MEASUREMENT_ID = os.environ.get('GA4_MEASUREMENT_ID', '')

