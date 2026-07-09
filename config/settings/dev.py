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

# Run django-q2 tasks synchronously in dev mode so that interaction logging
# (and other async tasks) execute inline without requiring a separate
# `python manage.py qcluster` worker process. The dev server is typically run
# on its own; without sync mode, async_task enqueues rows to django_q_ormq
# that are never processed, silently dropping interaction logs and other
# background work. Q_CLUSTER is defined in base.py with sync=False; override
# here so dev behaves like the test settings.
Q_CLUSTER = {'name': 'PMKetoan', 'sync': True, 'orm': 'default'}

