"""Test settings."""

import os

from .base import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("TEST_DB_NAME", "test_pmketoan"),  # noqa: F405
        "USER": os.environ.get("TEST_DB_USER", "root"),  # noqa: F405
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", ""),  # noqa: F405
        "HOST": os.environ.get("TEST_DB_HOST", "127.0.0.1"),  # noqa: F405
        "PORT": os.environ.get("TEST_DB_PORT", "3306"),  # noqa: F405
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Use non-manifest staticfiles storage in tests — CompressedManifestStaticFilesStorage
# (from base.py) requires a collectstatic manifest that doesn't exist during testing,
# causing ValueError: Missing staticfiles manifest entry for 'manifest.json'.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Run django-q2 tasks synchronously in tests
Q_CLUSTER = {"sync": True, "orm": "default"}

# Faster tests
DEBUG = False
TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ["*"]

# Disable debug toolbar (would intercept clicks in E2E tests)
if "debug_toolbar" in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "debug_toolbar"]  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if "debug_toolbar" not in m]  # noqa: F405

# Disable Axes brute-force for tests (E2E runs many logins).
# Use dummy handler to avoid AxesDatabaseHandler.user_logged_in → reset_user_attempts
# which segfaults in MySQLdb C code during force_login() in tests.
AXES_HANDLER = "axes.handlers.dummy.AxesDummyHandler"
AXES_FAILURE_LIMIT = 100000
AXES_COOLOFF_TIME = 0
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ["127.0.0.1", "::1"]

# N+1 query detection (nplusone, if installed)
try:
    import nplusone.ext.django  # noqa: F401
    if "nplusone.ext.django" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS = INSTALLED_APPS + ["nplusone.ext.django"]  # noqa: F405
        MIDDLEWARE = MIDDLEWARE + ["nplusone.ext.django.NPlusOneMiddleware"]  # noqa: F405
        NPLUSONE_RAISE = True
except ImportError:
    pass
