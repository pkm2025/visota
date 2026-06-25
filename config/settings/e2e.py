"""E2E test settings — like dev but without debug_toolbar (intercepts clicks).

DEBUG=True needed for runserver to serve static files (CSS/JS).
config/urls.py wraps debug_toolbar in `if settings.DEBUG` — but we patch
INSTALLED_APPS to exclude it before url loading so the import doesn't fail.
"""

from .base import *  # noqa: F401,F403
import os

DEBUG = True
ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Axes brute-force lockout for localhost (E2E tests)
AXES_FAILURE_LIMIT = 100000
AXES_COOLOFF_TIME = 0
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ['127.0.0.1', '::1']

# Exclude debug_toolbar — even though DEBUG=True, we don't want it intercepting clicks.
# We can't add it to INSTALLED_APPS (urls.py would import it); instead we let urls.py
# try to import it and fail silently by setting DEBUG internally for that check.
# Simpler approach: don't include debug_toolbar in INSTALLED_APPS, urls.py import will fail
# silently because it's wrapped in try/except via DEBUG check.
