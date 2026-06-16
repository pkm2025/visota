# Phase 0: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup PMKetoan project foundation — Django 5.2 + MariaDB + multi-tenant + identity + UX framework skeleton + Modern UI shell. Verify against SIS original.

**Architecture:** Django monolith with shared backend (models/services) + plugin-based UI layer. Multi-tenant via `company_id` column. MariaDB as DB, DB cache, and django-q2 broker. systemd deployment (no Docker).

**Tech Stack:** Python 3.12, Django 5.2 LTS, django-ninja, django-q2, MariaDB 11.4, HTMX 2.x, Alpine.js 3.x, Bootstrap 5.3, pytest, uv.

---

## File Structure

```
pmketoan/
├── apps/
│   ├── __init__.py
│   ├── core/                           # Created Task 3-4
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                   # Company
│   │   ├── managers.py                 # CompanyQuerySet, CompanyManager
│   │   ├── middleware.py               # TenantMiddleware
│   │   ├── context_processors.py       # brand, current_layout
│   │   ├── ux/                         # Created Task 8-9
│   │   │   ├── __init__.py
│   │   │   ├── registry.py             # InteractionStyleRegistry
│   │   │   ├── workflows.py            # WorkflowRegistry
│   │   │   ├── context.py              # UXContext
│   │   │   └── defaults.py
│   │   └── migrations/
│   ├── identity/                       # Created Task 5-7
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                   # User, Role, Permission
│   │   ├── backends.py                 # RBAC auth backend
│   │   ├── context_processors.py       # user_permissions
│   │   └── migrations/
│   └── ui_modern/                      # Created Task 10-12
│       ├── __init__.py
│       ├── apps.py
│       ├── urls.py
│       ├── views/
│       │   ├── __init__.py
│       │   ├── auth_views.py           # login, logout
│       │   ├── dashboard_views.py
│       │   └── health_views.py
│       └── forms/
│           └── auth_forms.py
├── config/
│   ├── __init__.py
│   ├── settings/                       # Created Task 2
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── test.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── templates/
│   ├── modern/                         # Created Task 10-12
│   │   ├── base/
│   │   │   └── layout.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   └── dashboard/
│   │       └── index.html
│   └── shared/
│       └── _layout_switcher.html
├── static/
│   ├── modern/css/main.css
│   ├── shared/css/variables.css
│   └── vendor/                         # Bootstrap, HTMX, Alpine
├── deploy/
│   ├── systemd/
│   │   ├── pmketoan-web.service        # Task 15
│   │   └── pmketoan-qcluster.service
│   └── nginx/
│       └── pmketoan.conf               # Task 16
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── factories.py
├── scripts/
│   └── install_vendor_assets.sh
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── pyproject.toml
├── uv.lock
├── package.json
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## Task 1: Project bootstrap

**Files:**
- Create: `pyproject.toml`, `manage.py`, `.gitignore`, `.python-version`, `requirements/base.txt`, `requirements/dev.txt`, `requirements/prod.txt`

- [ ] **Step 1: Initialize git repo and uv project**

```bash
cd /Users/dkm/dev/pmketoan
git init
echo "3.12" > .python-version
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "pmketoan"
version = "0.1.0"
description = "Vietnamese accounting software — PMKetoan"
requires-python = ">=3.12"
dependencies = [
    "Django>=5.2,<5.3",
    "django-ninja>=1.2",
    "mysqlclient>=2.2",
    "django-q2>=2.0",
    "django-extensions>=3.2",
    "django-debug-toolbar>=4.4",
    "django-allauth>=60.0",
    "django-axes>=6.5",
    "python-dateutil>=2.9",
    "PyYAML>=6.0",
    "weasyprint>=60.0",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-cov>=5.0",
    "pytest-mock>=3.14",
    "factory-boy>=3.3",
    "faker>=25.0",
    "pytest-xdist>=3.5",
    "ruff>=0.5",
    "mypy>=1.10",
    "django-stubs>=5.0",
    "pre-commit>=3.7",
    "ipython>=8.0",
    "ipdb>=0.13",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
addopts = "-v --cov=apps --cov-report=term-missing --reuse-db"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "C4", "RET", "SIM"]

[tool.mypy]
python_version = "3.12"
plugins = ["mypy_django_plugin.main"]
strict = true

[[tool.mypy.overrides]]
module = "django.*"
ignore_missing_imports = true
```

- [ ] **Step 3: Create requirements files (mirror of pyproject for pip users)**

`requirements/base.txt`:
```
Django>=5.2,<5.3
django-ninja>=1.2
mysqlclient>=2.2
django-q2>=2.0
django-extensions>=3.2
django-allauth>=60.0
django-axes>=6.5
python-dateutil>=2.9
PyYAML>=6.0
weasyprint>=60.0
openpyxl>=3.1
```

`requirements/dev.txt`:
```
-r base.txt
Django>=5.2,<5.3
django-debug-toolbar>=4.4
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-mock>=3.14
factory-boy>=3.3
faker>=25.0
pytest-xdist>=3.5
ruff>=0.5
mypy>=1.10
django-stubs>=5.0
pre-commit>=3.7
ipython>=8.0
ipdb>=0.13
```

`requirements/prod.txt`:
```
-r base.txt
gunicorn>=22.0
sentry-sdk>=2.0
```

- [ ] **Step 4: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.eggs/
build/
dist/

# Virtual env
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.mypy_cache/
.ruff_cache/

# Environment
.env
.env.local
.env.*.local

# Django
*.log
*.pot
*.pyc
local_settings.py
db.sqlite3
db.sqlite3-journal
media/
staticfiles/

# OS
.DS_Store
Thumbs.db

# uv
uv.lock.tmp
```

- [ ] **Step 5: Create manage.py**

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

- [ ] **Step 6: Install dependencies and verify**

```bash
cd /Users/dkm/dev/pmketoan
curl -LsSf https://astral.sh/uv/install.sh | sh  # if not installed
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements/dev.txt
python -c "import django; print(django.get_version())"
```

Expected output: `5.2.x`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements/ manage.py .gitignore .python-version
git commit -m "feat: bootstrap project with Django 5.2 + uv"
```

---

## Task 2: Django settings + URL routing

**Files:**
- Create: `config/__init__.py`, `config/settings/__init__.py`, `config/settings/base.py`, `config/settings/dev.py`, `config/settings/test.py`, `config/settings/prod.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`

- [ ] **Step 1: Create config/settings/base.py**

```python
"""Base Django settings for PMKetoan."""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-change-in-prod')

DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'django_extensions',
    'django_q2',
    'axes',

    # Local — shared backend
    'apps.core',
    'apps.identity',

    # Local — UI layout packs
    'apps.ui_modern',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'apps.core.middleware.TenantMiddleware',
    'apps.core.middleware.BrandingMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.branding',
                'apps.identity.context_processors.user_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'pmketoan'),
        'USER': os.environ.get('DB_USER', 'pmketoan'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'devpass'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'identity.User'
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'apps.identity.backends.RoleBasedBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/modern/'
LOGOUT_REDIRECT_URL = '/auth/login/'

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('vi', 'Tiếng Việt'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache: Django DB cache (no Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 3600,
        'OPTIONS': {'MAX_ENTRIES': 100000},
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# django-q2: broker = Django ORM
Q_CLUSTER = {
    'name': 'PMKetoan',
    'workers': 4,
    'recycle': 500,
    'timeout': 600,
    'retry': 720,
    'queue_limit': 1000,
    'bulk': 5,
    'orm': 'default',
    'sync': False,
    'catch_up': True,
    'max_attempts': 3,
}

# Axes (brute-force protection)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour
AXES_RESET_ON_SUCCESS = True

# Security defaults (overridden in prod)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
```

- [ ] **Step 2: Create config/settings/dev.py**

```python
"""Development settings."""
from .base import *  # noqa: F401,F403
import os

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

- [ ] **Step 3: Create config/settings/test.py**

```python
"""Test settings."""
from .base import *  # noqa: F401,F403

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
```

- [ ] **Step 4: Create config/settings/prod.py**

```python
"""Production settings."""
import os
from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')

SECRET_KEY = os.environ['SECRET_KEY']

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

STATIC_ROOT = '/home/pmketoan/app/staticfiles/'
MEDIA_ROOT = '/home/pmketoan/app/media/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/pmketoan/django.log',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 10,
            'formatter': 'verbose',
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
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
    )
```

- [ ] **Step 5: Create config/__init__.py, config/settings/__init__.py, wsgi.py, asgi.py**

`config/__init__.py`:
```python
```

`config/settings/__init__.py`:
```python
```

`config/wsgi.py`:
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
application = get_wsgi_application()
```

`config/asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
application = get_asgi_application()
```

- [ ] **Step 6: Create config/urls.py (minimal — will extend in Task 12)**

```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/modern/', permanent=False)),
    path('modern/', include('apps.ui_modern.urls')),
]
```

- [ ] **Step 7: Create empty apps package structure**

```bash
mkdir -p apps/core/migrations apps/identity/migrations apps/ui_modern/views apps/ui_modern/forms
touch apps/__init__.py apps/core/__init__.py apps/core/migrations/__init__.py
touch apps/identity/__init__.py apps/identity/migrations/__init__.py
touch apps/ui_modern/__init__.py apps/ui_moden/views/__init__.py apps/ui_modern/forms/__init__.py
```

- [ ] **Step 8: Verify Django starts (will fail — apps not yet created)**

```bash
python manage.py check
```

Expected: Error about missing apps — that's OK, fix in next tasks.

- [ ] **Step 9: Commit**

```bash
git add config/ apps/
git commit -m "feat: Django settings + URL routing skeleton"
```

---

## Task 3: Core app — Company model

**Files:**
- Create: `apps/core/apps.py`, `apps/core/models.py`, `apps/core/managers.py`
- Test: `tests/test_company_model.py`

- [ ] **Step 1: Write failing test**

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
import pytest
from apps.core.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(
        code='TEST',
        name='Test Company',
        tax_code='0101234567',
        accounting_regime='tt133',
    )
```

`tests/test_company_model.py`:
```python
import pytest
from apps.core.models import Company
from apps.core.managers import CompanyQuerySet


def test_company_creation(company):
    assert company.pk is not None
    assert company.code == 'TEST'
    assert str(company) == 'Test Company'


def test_company_str_representation(company):
    assert 'Test Company' in str(company)


def test_company_default_regime_is_tt133():
    c = Company(code='X', name='X')
    assert c.accounting_regime == 'tt133'


def test_company_default_currency_vnd():
    c = Company(code='X', name='X')
    assert c.default_currency == 'VND'


def test_company_queryset_returns_company_queryset():
    assert isinstance(Company.objects.all(), CompanyQuerySet)


def test_company_branding_fields_default():
    c = Company(code='X', name='X')
    assert c.brand_primary_color == '#2563eb'
    assert c.default_layout == 'modern'
    assert c.hide_pmketoan_branding is False
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_company_model.py -v
```

Expected: ImportError or ModuleNotFoundError for `apps.core.models`.

- [ ] **Step 3: Create apps/core/apps.py**

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
```

- [ ] **Step 4: Create apps/core/managers.py**

```python
"""Custom managers and querysets for multi-tenant models."""
from django.db import models


class CompanyQuerySet(models.QuerySet):
    """QuerySet that supports multi-tenant filtering by company_id."""

    def for_company(self, company_id):
        return self.filter(company_id=company_id)

    def active(self):
        return self.filter(is_active=True)


class CompanyManager(models.Manager.from_queryset(CompanyQuerySet)):
    """Manager that auto-filters by current company if set in thread-local."""

    use_in_migrations = True


class CompanyOwnedModel(models.Model):
    """Abstract base for models that belong to a Company (multi-tenant)."""

    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='+',
        db_index=True,
    )

    objects = CompanyManager()

    class Meta:
        abstract = True
```

- [ ] **Step 5: Create apps/core/models.py**

```python
"""Core models: Company (tenant) and branding."""
from django.db import models
from django.core.validators import RegexValidator

from .managers import CompanyQuerySet


HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Color must be in hex format: #RRGGBB',
)


class Company(models.Model):
    """Tenant entity. Multi-tenant isolation via company_id column."""

    class AccountingRegime(models.TextChoices):
        TT133 = 'tt133', 'TT133/2016 (DN nhỏ và vừa)'
        TT200 = 'tt200', 'TT200/2014 (DN lớn)'
        Q48 = 'q48', 'QĐ48/2006 (cũ)'

    # Legal info
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255, blank=True)
    short_name = models.CharField(max_length=100, blank=True)
    tax_code = models.CharField(max_length=20, blank=True, db_index=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    legal_representative = models.CharField(max_length=255, blank=True)
    chief_accountant = models.CharField(max_length=255, blank=True)

    # Configuration
    accounting_regime = models.CharField(
        max_length=10,
        choices=AccountingRegime.choices,
        default=AccountingRegime.TT133,
    )
    default_currency = models.CharField(max_length=3, default='VND')
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    # Branding
    brand_name = models.CharField(max_length=255, blank=True)
    brand_logo = models.ImageField(upload_to='brands/logos/', null=True, blank=True)
    brand_logo_dark = models.ImageField(upload_to='brands/logos/', null=True, blank=True)
    brand_favicon = models.ImageField(upload_to='brands/favicons/', null=True, blank=True)
    brand_primary_color = models.CharField(
        max_length=7, default='#2563eb', validators=[HEX_COLOR_VALIDATOR]
    )
    brand_accent_color = models.CharField(
        max_length=7, default='#16a34a', validators=[HEX_COLOR_VALIDATOR]
    )
    brand_sidebar_color = models.CharField(max_length=20, default='light')

    default_layout = models.CharField(max_length=20, default='modern')

    # White-label
    hide_pmketoan_branding = models.BooleanField(default=False)
    custom_css = models.TextField(blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyQuerySet.as_manager()

    class Meta:
        db_table = 'company'
        verbose_name = 'Company (Tenant)'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return self.brand_name or self.name
```

- [ ] **Step 6: Create migration**

```bash
python manage.py makemigrations core
```

Expected: Creates `apps/core/migrations/0001_initial.py`.

- [ ] **Step 7: Run migration**

```bash
python manage.py migrate
```

Expected: `Applying core.0001_initial... OK`.

- [ ] **Step 8: Run tests**

```bash
pytest tests/test_company_model.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/core/ tests/
git commit -m "feat(core): Company model with branding fields"
```

---

## Task 4: Core middleware — Tenant + Branding

**Files:**
- Create: `apps/core/middleware.py`, `apps/core/context_processors.py`
- Test: `tests/test_middleware.py`

- [ ] **Step 1: Write failing test**

`tests/test_middleware.py`:
```python
import pytest
from django.test import RequestFactory
from apps.core.middleware import TenantMiddleware, BrandingMiddleware
from apps.core.models import Company


@pytest.fixture
def rf():
    return RequestFactory()


def test_branding_middleware_sets_default_brand_for_anonymous(rf):
    req = rf.get('/modern/')
    req.user = type('AnonymousUser', (), {'is_authenticated': False})()

    middleware = BrandingMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)

    assert req.brand['name'] == 'PMKetoan'
    assert req.brand['primary_color'] == '#2563eb'


def test_branding_middleware_sets_company_brand(rf, company):
    req = rf.get('/modern/')
    req.user = type('User', (), {'is_authenticated': True})()
    req.current_company = company

    middleware = BrandingMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)

    assert req.brand['name'] == 'Test Company'
    assert req.brand['primary_color'] == '#2563eb'


def test_tenant_middleware_detects_layout_modern(rf):
    req = rf.get('/modern/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'modern'


def test_tenant_middleware_detects_layout_classic(rf):
    req = rf.get('/classic/dashboard/')
    middleware = TenantMiddleware(lambda r: type('Response', (), {'status_code': 200})())
    middleware(req)
    assert req.current_layout == 'classic'
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_middleware.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create apps/core/middleware.py**

```python
"""Tenant and branding middleware."""
from django.conf import settings

DEFAULT_BRAND = {
    'name': 'PMKetoan',
    'logo': '/static/images/logo.svg',
    'logo_dark': '/static/images/logo-dark.svg',
    'primary_color': '#2563eb',
    'accent_color': '#16a34a',
    'favicon': '/static/images/favicon.ico',
    'hide_pmketoan_branding': False,
    'custom_css': '',
}


class TenantMiddleware:
    """Detect current layout from URL path."""

    LAYOUT_PREFIXES = {
        '/modern/': 'modern',
        '/classic/': 'classic',
        '/mobile/': 'mobile',
        '/portal/': 'portal',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_layout = self._detect_layout(request.path)
        request.current_company = self._get_current_company(request)
        return self.get_response(request)

    def _detect_layout(self, path):
        for prefix, layout in self.LAYOUT_PREFIXES.items():
            if path.startswith(prefix):
                return layout
        return 'modern'

    def _get_current_company(self, request):
        if not hasattr(request, 'session'):
            return None
        company_id = request.session.get('current_company_id')
        if not company_id:
            return None
        from apps.core.models import Company
        return Company.objects.filter(id=company_id, is_active=True).first()


class BrandingMiddleware:
    """Set request.brand from current company."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company = getattr(request, 'current_company', None)
        if company:
            request.brand = {
                'name': company.display_name,
                'logo': company.brand_logo.url if company.brand_logo else DEFAULT_BRAND['logo'],
                'logo_dark': company.brand_logo_dark.url if company.brand_logo_dark else DEFAULT_BRAND['logo_dark'],
                'primary_color': company.brand_primary_color,
                'accent_color': company.brand_accent_color,
                'favicon': company.brand_favicon.url if company.brand_favicon else DEFAULT_BRAND['favicon'],
                'hide_pmketoan_branding': company.hide_pmketoan_branding,
                'custom_css': company.custom_css,
            }
        else:
            request.brand = DEFAULT_BRAND.copy()
        return self.get_response(request)
```

- [ ] **Step 4: Create apps/core/context_processors.py**

```python
"""Context processors available in all templates."""
from apps.core.ux.defaults import get_available_layouts


def branding(request):
    """Expose brand info to templates."""
    return {
        'brand': getattr(request, 'brand', {}),
        'current_layout': getattr(request, 'current_layout', 'modern'),
        'current_company': getattr(request, 'current_company', None),
        'available_layouts': get_available_layouts(),
    }
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_middleware.py -v
```

Expected: All 4 tests PASS (after Task 8 creates `apps/core/ux/defaults.py`).

- [ ] **Step 6: Commit**

```bash
git add apps/core/middleware.py apps/core/context_processors.py tests/test_middleware.py
git commit -m "feat(core): Tenant + Branding middleware"
```

---

## Task 5: Identity app — User model

**Files:**
- Create: `apps/identity/apps.py`, `apps/identity/models.py` (User only)
- Test: `tests/test_user_model.py`

- [ ] **Step 1: Write failing test**

`tests/test_user_model.py`:
```python
import pytest
from apps.identity.models import User


def test_user_creation(db):
    u = User.objects.create_user(
        username='alice',
        email='alice@example.com',
        password='SecretPass123',
        full_name='Alice Nguyen',
    )
    assert u.pk is not None
    assert u.check_password('SecretPass123')
    assert u.is_active is True
    assert u.is_superuser is False


def test_create_superuser(db):
    u = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='AdminPass123',
    )
    assert u.is_staff is True
    assert u.is_superuser is True


def test_user_str_shows_full_name(db):
    u = User(username='alice', full_name='Alice Nguyen')
    assert str(u) == 'Alice Nguyen (alice)'


def test_user_without_full_name_shows_username(db):
    u = User(username='alice')
    assert str(u) == 'alice'
```

- [ ] **Step 2: Run test (fail)**

```bash
pytest tests/test_user_model.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create apps/identity/apps.py**

```python
from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.identity'
    verbose_name = 'Identity & Access'
```

- [ ] **Step 4: Create apps/identity/models.py (User only — Role/Permission in Task 6)**

```python
"""User, Role, Permission models."""
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom User model with Vietnamese-friendly fields."""

    full_name = models.CharField(max_length=255, blank=True)
    full_name_en = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True)

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.full_name:
            return f'{self.full_name} ({self.username})'
        return self.username
```

- [ ] **Step 5: Create migration**

```bash
python manage.py makemigrations identity
```

- [ ] **Step 6: Run migration**

```bash
python manage.py migrate
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_user_model.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/identity/ tests/test_user_model.py
git commit -m "feat(identity): custom User model"
```

---

## Task 6: Identity app — Role, Permission, UserCompanyRole

**Files:**
- Modify: `apps/identity/models.py` (add Role, Permission, UserCompanyRole)
- Test: `tests/test_rbac.py`

- [ ] **Step 1: Write failing test**

`tests/test_rbac.py`:
```python
import pytest
from apps.identity.models import User, Role, Permission, UserCompanyRole
from apps.core.models import Company


def test_role_creation(db, company):
    role = Role.objects.create(
        company=company,
        code='accountant',
        name='Kế toán viên',
    )
    assert role.pk is not None
    assert str(role) == 'Kế toán viên'


def test_permission_unique_code(db):
    Permission.objects.create(code='gl.voucher.view', name='View vouchers')
    with pytest.raises(Exception):
        Permission.objects.create(code='gl.voucher.view', name='Duplicate')


def test_user_company_role(db, company):
    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='accountant', name='KT')

    ucr = UserCompanyRole.objects.create(
        user=user, company=company, role=role, is_default=True,
    )
    assert ucr.pk is not None


def test_user_has_permission_through_role(db, company):
    from apps.identity.services import UserService

    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='accountant', name='KT')
    perm = Permission.objects.create(code='gl.voucher.view', name='View')
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)

    service = UserService(user, company)
    assert service.has_permission('gl.voucher.view') is True
    assert service.has_permission('gl.voucher.delete') is False
```

- [ ] **Step 2: Run tests (fail)**

```bash
pytest tests/test_rbac.py -v
```

Expected: ImportError for Role/Permission/UserCompanyRole.

- [ ] **Step 3: Modify apps/identity/models.py — append Role/Permission**

```python
# Append to apps/identity/models.py (keep User above)

class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permission'
        ordering = ['module', 'code']

    def __str__(self):
        return f'{self.code} ({self.name})'


class Role(models.Model):
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='roles', null=True, blank=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True)

    class Meta:
        db_table = 'role'
        unique_together = [('company', 'code')]
        ordering = ['name']

    def __str__(self):
        return self.name


class UserCompanyRole(models.Model):
    user = models.ForeignKey(
        'identity.User', on_delete=models.CASCADE, related_name='company_roles',
    )
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='user_roles',
    )
    role = models.ForeignKey(
        'identity.Role', on_delete=models.PROTECT, related_name='user_company_roles',
    )
    is_default = models.BooleanField(default=False)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'user_company_role'
        unique_together = [('user', 'company', 'role')]

    def __str__(self):
        return f'{self.user} @ {self.company} = {self.role}'
```

- [ ] **Step 4: Create apps/identity/services.py**

```python
"""Identity services: permission checks, role management."""
from django.core.cache import cache


class UserService:
    """Service layer for user operations."""

    CACHE_KEY = 'user_perms_{user_id}_{company_id}'

    def __init__(self, user, company):
        self.user = user
        self.company = company

    def has_permission(self, perm_code: str) -> bool:
        if self.user.is_superuser:
            return True
        perms = self._get_permissions()
        return perm_code in perms

    def _get_permissions(self) -> set[str]:
        cache_key = self.CACHE_KEY.format(
            user_id=self.user.id, company_id=self.company.id if self.company else 0,
        )
        perms = cache.get(cache_key)
        if perms is None:
            perms = self._load_permissions()
            cache.set(cache_key, perms, timeout=300)
        return perms

    def _load_permissions(self) -> set[str]:
        from apps.identity.models import UserCompanyRole
        if not self.company:
            return set()
        ucrs = UserCompanyRole.objects.filter(
            user=self.user, company=self.company,
        ).select_related('role').prefetch_related('role__permissions')
        perms = set()
        for ucr in ucrs:
            for p in ucr.role.permissions.all():
                perms.add(p.code)
        return perms

    def invalidate_cache(self):
        cache.delete(self.CACHE_KEY.format(
            user_id=self.user.id,
            company_id=self.company.id if self.company else 0,
        ))
```

- [ ] **Step 5: Create migration**

```bash
python manage.py makemigrations identity
python manage.py migrate
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_rbac.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/identity/ tests/test_rbac.py
git commit -m "feat(identity): Role + Permission + UserCompanyRole"
```

---

## Task 7: Identity auth backend

**Files:**
- Create: `apps/identity/backends.py`, `apps/identity/context_processors.py`
- Test: `tests/test_auth_backend.py`

- [ ] **Step 1: Write failing test**

`tests/test_auth_backend.py`:
```python
import pytest
from apps.identity.backends import RoleBasedBackend
from apps.identity.models import User, Role, Permission, UserCompanyRole
from apps.core.models import Company


def test_authenticate_with_username(db):
    User.objects.create_user(username='alice', password='Secret123')
    backend = RoleBasedBackend()
    user = backend.authenticate(
        None, username='alice', password='Secret123',
    )
    assert user is not None
    assert user.username == 'alice'


def test_authenticate_with_email(db):
    User.objects.create_user(
        username='alice', email='alice@example.com', password='Secret123',
    )
    backend = RoleBasedBackend()
    user = backend.authenticate(
        None, username='alice@example.com', password='Secret123',
    )
    assert user is not None


def test_authenticate_wrong_password(db):
    User.objects.create_user(username='alice', password='Secret123')
    backend = RoleBasedBackend()
    user = backend.authenticate(None, username='alice', password='wrong')
    assert user is None


def test_user_has_perm_via_role(db, company):
    user = User.objects.create_user(username='alice', password='Secret123')
    role = Role.objects.create(company=company, code='acc', name='KT')
    perm = Permission.objects.create(code='gl.voucher.view', name='View')
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)

    backend = RoleBasedBackend()
    # Simulate request with company
    class FakeReq:
        current_company = company
        session = {}

    assert backend.has_perm(FakeReq(), 'gl.voucher.view', user) is True
```

- [ ] **Step 2: Run tests (fail)**

```bash
pytest tests/test_auth_backend.py -v
```

- [ ] **Step 3: Create apps/identity/backends.py**

```python
"""Role-based authentication backend."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from apps.identity.services import UserService

User = get_user_model()


class RoleBasedBackend(ModelBackend):
    """Authenticate via username or email. Permissions come from roles."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        # Try username first, then email
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            # Track IP for security audit
            if request is not None:
                from apps.identity.audit import record_login
                record_login(user, request)
            return user
        return None

    def has_perm(self, user_obj, perm, obj=None):
        # Permission check via role-based service
        request = getattr(user_obj, '_request', None)
        company = getattr(request, 'current_company', None) if request else None
        if company is None:
            return False
        service = UserService(user_obj, company)
        return service.has_permission(perm)
```

- [ ] **Step 4: Create apps/identity/audit.py**

```python
"""Audit logging for auth events."""
from django.utils import timezone


def record_login(user, request):
    """Record successful login for audit purposes."""
    ip = (
        request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or request.META.get('REMOTE_ADDR')
    )
    user.last_login_ip = ip
    user.failed_login_count = 0
    user.save(update_fields=['last_login_ip', 'failed_login_count'])
```

- [ ] **Step 5: Create apps/identity/context_processors.py**

```python
"""Identity context processors."""


def user_permissions(request):
    """Expose permission helper to templates."""
    user = getattr(request, 'user', None)
    company = getattr(request, 'current_company', None)

    if not user or not user.is_authenticated or not company:
        return {'has_perm': lambda code: False}

    from apps.identity.services import UserService
    service = UserService(user, company)

    return {
        'has_perm': service.has_permission,
        'user_service': service,
    }
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_auth_backend.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/identity/ tests/test_auth_backend.py
git commit -m "feat(identity): role-based auth backend"
```

---

## Task 8: UX framework — InteractionStyleRegistry

**Files:**
- Create: `apps/core/ux/__init__.py`, `apps/core/ux/registry.py`
- Test: `tests/test_ux_registry.py`

- [ ] **Step 1: Write failing test**

`tests/test_ux_registry.py`:
```python
import pytest
from apps.core.ux.registry import (
    InteractionStyle, InteractionStyleRegistry,
    GuidedStyle, StandardStyle, QuickStyle, BulkStyle,
)


def test_registry_has_standard():
    assert InteractionStyleRegistry.get('standard') is StandardStyle


def test_registry_all_returns_4_builtins():
    codes = {s.code for s in InteractionStyleRegistry.all()}
    assert {'guided', 'standard', 'quick', 'bulk'}.issubset(codes)


def test_standard_supports_voucher_create():
    assert 'voucher.create' in StandardStyle.supported_operations


def test_guided_supports_voucher_create():
    assert 'voucher.create' in GuidedStyle.supported_operations


def test_bulk_does_not_support_period_closing():
    assert 'period.closing' not in BulkStyle.supported_operations


def test_registry_can_register_custom():
    class CustomStyle(InteractionStyle):
        code = 'custom_test'
        name = 'Custom'
        supported_operations = ['test.op']
        template_prefix = 'test'
        url_suffix = 'custom-test'

    InteractionStyleRegistry.register(CustomStyle)
    assert InteractionStyleRegistry.get('custom_test') is CustomStyle


def test_for_operation_filters_supported():
    styles = InteractionStyleRegistry.for_operation('voucher.create')
    codes = {s.code for s in styles}
    assert 'standard' in codes
    assert 'guided' in codes
```

- [ ] **Step 2: Run tests (fail)**

```bash
pytest tests/test_ux_registry.py -v
```

- [ ] **Step 3: Create apps/core/ux/__init__.py**

```python
```

- [ ] **Step 4: Create apps/core/ux/registry.py**

```python
"""UX framework: InteractionStyleRegistry (plugin system for UX variants)."""

CORE_OPERATIONS = [
    'voucher.create', 'voucher.edit',
    'sales_invoice.create', 'sales_invoice.edit',
    'purchase_invoice.create', 'purchase_invoice.edit',
    'customer.create', 'vendor.create', 'product.create',
    'stock_voucher.create',
    'period.closing',
]


class InteractionStyle:
    """Base class for interaction styles (Guided, Standard, Quick, Bulk)."""

    code: str = ''
    name: str = ''
    description: str = ''
    template_prefix: str = ''
    url_suffix: str = ''
    required_permission: str | None = None
    supported_operations: list[str] = []

    @classmethod
    def get_template(cls, operation: str, template_name: str = 'form.html') -> str:
        return f'{cls.template_prefix}/{operation}/{template_name}'

    @classmethod
    def supports(cls, operation: str) -> bool:
        return operation in cls.supported_operations


class GuidedStyle(InteractionStyle):
    """Wizard-style for newcomers."""
    code = 'guided'
    name = 'Hướng dẫn'
    description = 'Wizard từng bước cho người mới'
    template_prefix = 'guided'
    url_suffix = 'guided'
    required_permission = None
    supported_operations = [
        'voucher.create', 'voucher.edit',
        'sales_invoice.create', 'sales_invoice.edit',
        'purchase_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class StandardStyle(InteractionStyle):
    """Default full form for accountants."""
    code = 'standard'
    name = 'Tiêu chuẩn'
    description = 'Form đầy đủ cho kế toán chuyên nghiệp'
    template_prefix = 'standard'
    url_suffix = ''  # default, no URL suffix
    required_permission = None
    supported_operations = CORE_OPERATIONS[:]


class QuickStyle(InteractionStyle):
    """Minimal form for fast data entry."""
    code = 'quick'
    name = 'Nhanh'
    description = 'Minimal fields, smart defaults'
    template_prefix = 'quick'
    url_suffix = 'quick'
    required_permission = None
    supported_operations = [
        'voucher.create',
        'sales_invoice.create',
        'purchase_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class BulkStyle(InteractionStyle):
    """Paste from Excel for batch entry."""
    code = 'bulk'
    name = 'Hàng loạt'
    description = 'Paste Excel, preview, bulk create'
    template_prefix = 'bulk'
    url_suffix = 'bulk'
    required_permission = None
    supported_operations = [
        'voucher.create',
        'sales_invoice.create',
        'customer.create', 'vendor.create', 'product.create',
    ]


class InteractionStyleRegistry:
    """Registry of available interaction styles."""

    _registry: dict[str, type[InteractionStyle]] = {}

    @classmethod
    def register(cls, style_class: type[InteractionStyle]) -> None:
        cls._registry[style_class.code] = style_class

    @classmethod
    def get(cls, code: str) -> type[InteractionStyle] | None:
        return cls._registry.get(code)

    @classmethod
    def all(cls) -> list[type[InteractionStyle]]:
        return list(cls._registry.values())

    @classmethod
    def all_codes(cls) -> list[str]:
        return list(cls._registry.keys())

    @classmethod
    def for_operation(cls, operation: str) -> list[type[InteractionStyle]]:
        return [s for s in cls.all() if s.supports(operation)]

    @classmethod
    def for_user(cls, user, operation: str) -> list[type[InteractionStyle]]:
        result = []
        for s in cls.for_operation(operation):
            if not s.required_permission:
                result.append(s)
            elif user.is_superuser:
                result.append(s)
            else:
                # Check permission (simplified; full impl in Identity service)
                from apps.identity.services import UserService
                company = getattr(user, '_current_company', None)
                if company and UserService(user, company).has_permission(s.required_permission):
                    result.append(s)
        return result


# Register built-in styles
InteractionStyleRegistry.register(GuidedStyle)
InteractionStyleRegistry.register(StandardStyle)
InteractionStyleRegistry.register(QuickStyle)
InteractionStyleRegistry.register(BulkStyle)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_ux_registry.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/core/ux/ tests/test_ux_registry.py
git commit -m "feat(core/ux): InteractionStyleRegistry with 4 built-in styles"
```

---

## Task 9: UX framework — UXContext + defaults

**Files:**
- Create: `apps/core/ux/context.py`, `apps/core/ux/defaults.py`
- Test: `tests/test_ux_context.py`

- [ ] **Step 1: Write failing test**

`tests/test_ux_context.py`:
```python
import pytest
from apps.core.ux.context import UXContext
from apps.core.ux.defaults import suggest_ux_for_role, get_available_layouts


def test_default_ux_context():
    ux = UXContext(layout='modern', style='standard', workflow='scratch')
    assert ux.layout == 'modern'
    assert ux.style == 'standard'
    assert ux.workflow == 'scratch'


def test_ux_context_get_template_path():
    ux = UXContext(layout='modern', style='guided', workflow='scratch')
    path = ux.get_template('invoice/create', 'form.html')
    assert path == 'modern/invoice/create/guided/form.html'


def test_default_style_for_layout_mobile_is_guided():
    assert UXContext.default_style_for_layout('mobile') == 'guided'


def test_default_style_for_layout_portal_is_standard():
    assert UXContext.default_style_for_layout('portal') == 'standard'


def test_default_style_for_layout_modern_is_standard():
    assert UXContext.default_style_for_layout('modern') == 'standard'


def test_suggest_ux_for_role_accountant():
    ux = suggest_ux_for_role('accountant')
    assert ux['layout'] == 'modern'
    assert ux['style'] == 'standard'


def test_suggest_ux_for_role_sales_is_guided():
    ux = suggest_ux_for_role('sales')
    assert ux['style'] == 'guided'


def test_get_available_layouts():
    layouts = get_available_layouts()
    codes = [l['code'] for l in layouts]
    assert 'modern' in codes
    assert 'classic' in codes
```

- [ ] **Step 2: Run tests (fail)**

```bash
pytest tests/test_ux_context.py -v
```

- [ ] **Step 3: Create apps/core/ux/context.py**

```python
"""UXContext: tracks which layout × style × workflow is active."""
from dataclasses import dataclass


@dataclass
class UXContext:
    """User's current UX variant: layout + interaction style + workflow."""

    layout: str = 'modern'
    style: str = 'standard'
    workflow: str = 'scratch'

    @classmethod
    def from_request(cls, request) -> 'UXContext':
        layout = getattr(request, 'current_layout', 'modern')
        session = getattr(request, 'session', {})

        style = (
            getattr(request, 'GET', {}).get('style')
            or session.get(f'ux_style_{layout}')
            or cls.default_style_for_layout(layout)
        )

        workflow = (
            getattr(request, 'GET', {}).get('workflow', 'scratch')
        )

        return cls(layout=layout, style=style, workflow=workflow)

    @staticmethod
    def default_style_for_layout(layout: str) -> str:
        defaults = {
            'mobile': 'guided',
            'portal': 'standard',
            'modern': 'standard',
            'classic': 'standard',
        }
        return defaults.get(layout, 'standard')

    def get_template(self, operation: str, template_name: str = 'form.html') -> str:
        """Return full template path: e.g. 'modern/invoice/create/guided/form.html'."""
        return f'{self.layout}/{operation}/{self.style}/{template_name}'

    def get_list_template(self, module: str, template_name: str = 'list.html') -> str:
        """List views don't vary by style — just layout."""
        return f'{self.layout}/{module}/{template_name}'
```

- [ ] **Step 4: Create apps/core/ux/defaults.py**

```python
"""Smart UX defaults by user role and layout availability."""

ROLE_DEFAULT_UX = {
    'admin':            {'layout': 'modern',  'style': 'standard'},
    'chief_accountant': {'layout': 'classic', 'style': 'standard'},
    'accountant':       {'layout': 'modern',  'style': 'standard'},
    'data_entry':       {'layout': 'modern',  'style': 'quick'},
    'sales':            {'layout': 'modern',  'style': 'guided'},
    'manager':          {'layout': 'modern',  'style': 'standard'},
    'auditor':          {'layout': 'classic', 'style': 'standard'},
    'customer':         {'layout': 'portal',  'style': 'standard'},
}

DEFAULT_UX = {'layout': 'modern', 'style': 'standard'}

AVAILABLE_LAYOUTS = [
    {'code': 'modern',  'name': 'Modern',  'icon': 'bi-window-stack', 'url_prefix': '/modern/'},
    {'code': 'classic', 'name': 'Classic', 'icon': 'bi-table',        'url_prefix': '/classic/'},
    {'code': 'mobile',  'name': 'Mobile',  'icon': 'bi-phone',        'url_prefix': '/mobile/'},
    {'code': 'portal',  'name': 'Portal',  'icon': 'bi-person-circle','url_prefix': '/portal/'},
]


def suggest_ux_for_role(role_code: str) -> dict[str, str]:
    """Suggest UX defaults for a given user role."""
    return ROLE_DEFAULT_UX.get(role_code, DEFAULT_UX.copy())


def get_available_layouts() -> list[dict]:
    """Return list of available layout packs (for switcher UI)."""
    return AVAILABLE_LAYOUTS
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_ux_context.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/core/ux/ tests/test_ux_context.py
git commit -m "feat(core/ux): UXContext + smart defaults by role"
```

---

## Task 10: ui_modern app — base layout

**Files:**
- Create: `apps/ui_modern/apps.py`, `apps/ui_moden/urls.py`, `apps/ui_modern/views/__init__.py`, `apps/ui_modern/views/dashboard_views.py`, `templates/modern/base/layout.html`, `templates/modern/dashboard/index.html`, `templates/shared/_layout_switcher.html`
- Static: `static/shared/css/variables.css`, `static/modern/css/main.css`

- [ ] **Step 1: Create apps/ui_modern/apps.py**

```python
from django.apps import AppConfig


class UiModernConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ui_modern'
    label = 'ui_modern'
    verbose_name = 'UI — Modern'
```

- [ ] **Step 2: Create base layout template**

`templates/modern/base/layout.html`:
```html
{% load static %}
<!DOCTYPE html>
<html lang="vi" data-layout="{{ current_layout }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>{% block title %}{{ brand.name }}{% endblock %}</title>

    <link rel="icon" href="{{ brand.favicon }}">

    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap.min.css' %}">
    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap-icons.min.css' %}">
    <link rel="stylesheet" href="{% static 'shared/css/variables.css' %}">
    <link rel="stylesheet" href="{% static 'modern/css/main.css' %}">

    {% if brand.custom_css %}
    <style>{{ brand.custom_css|safe }}</style>
    {% endif %}

    {% block extra_css %}{% endblock %}
</head>
<body class="layout-modern" style="--brand-primary: {{ brand.primary_color }}; --brand-accent: {{ brand.accent_color }};">
    <!-- Top bar -->
    <header class="topbar">
        <div class="topbar-left">
            <a href="{% url 'ui_modern:dashboard' %}" class="brand-logo">
                {% if brand.logo %}
                    <img src="{{ brand.logo }}" alt="{{ brand.name }}" height="32">
                {% else %}
                    <strong>{{ brand.name }}</strong>
                {% endif %}
            </a>
        </div>
        <div class="topbar-center">
            <input type="search" placeholder="Tìm kiếm..." class="form-control form-control-sm global-search">
        </div>
        <div class="topbar-right">
            <button class="btn btn-sm btn-light"><i class="bi bi-bell"></i></button>
            <button class="btn btn-sm btn-light"><i class="bi bi-gear"></i></button>
            {% if user.is_authenticated %}
            <div class="dropdown">
                <button class="btn btn-sm btn-light dropdown-toggle" data-bs-toggle="dropdown">
                    <i class="bi bi-person"></i> {{ user.username }}
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/auth/profile/">Hồ sơ</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="/auth/logout/">Đăng xuất</a></li>
                </ul>
            </div>
            {% else %}
            <a href="/auth/login/" class="btn btn-sm btn-primary">Đăng nhập</a>
            {% endif %}
        </div>
    </header>

    <div class="layout-body">
        <!-- Sidebar -->
        <aside class="sidebar">
            <nav>
                <a href="{% url 'ui_modern:dashboard' %}" class="nav-item">
                    <i class="bi bi-house"></i> Trang chủ
                </a>
                <div class="nav-section">
                    <div class="nav-section-title">Cập nhật số liệu</div>
                    <a href="#" class="nav-item"><i class="bi bi-receipt"></i> Phiếu kế toán</a>
                    <a href="#" class="nav-item"><i class="bi bi-arrow-repeat"></i> Kết chuyển cuối kỳ</a>
                </div>
                <div class="nav-section">
                    <div class="nav-section-title">Sổ sách</div>
                    <a href="#" class="nav-item"><i class="bi bi-journal-book"></i> Nhật ký chung</a>
                    <a href="#" class="nav-item"><i class="bi bi-book"></i> Sổ cái</a>
                </div>
                <div class="nav-section">
                    <div class="nav-section-title">Báo cáo</div>
                    <a href="#" class="nav-item"><i class="bi bi-bar-chart"></i> BCĐ tài khoản</a>
                    <a href="#" class="nav-item"><i class="bi bi-file-earmark-bar-graph"></i> BCTC</a>
                </div>
                <div class="nav-section">
                    <div class="nav-section-title">Danh mục</div>
                    <a href="#" class="nav-item"><i class="bi bi-list-ul"></i> Hệ thống TK</a>
                </div>
            </nav>
        </aside>

        <!-- Main content -->
        <main class="main-content">
            {% if messages %}
            <div class="messages">
                {% for message in messages %}
                <div class="alert alert-{{ message.tags|default:'info' }} alert-dismissible">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            {% block content %}{% endblock %}
        </main>
    </div>

    {% include 'shared/_layout_switcher.html' %}

    <script src="{% static 'vendor/js/bootstrap.bundle.min.js' %}"></script>
    <script src="{% static 'vendor/js/htmx.min.js' %}"></script>
    <script src="{% static 'vendor/js/alpine.min.js' %}" defer></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Create dashboard view + template**

`apps/ui_modern/views/dashboard_views.py`:
```python
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'modern/dashboard/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tổng quan'
        return ctx
```

`apps/ui_modern/views/__init__.py`:
```python
from .dashboard_views import DashboardView

__all__ = ['DashboardView']
```

`templates/modern/dashboard/index.html`:
```html
{% extends 'modern/base/layout.html' %}

{% block content %}
<div class="container-fluid py-4">
    <h1>Tổng quan</h1>
    <p class="text-muted">Chào {{ user.full_name|default:user.username }}, đây là dashboard của bạn.</p>

    <div class="row mt-4">
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <div class="text-muted small">Chứng từ hôm nay</div>
                    <div class="h3 mb-0">—</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <div class="text-muted small">Công nợ KH</div>
                    <div class="h3 mb-0">—</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <div class="text-muted small">Công nợ NCC</div>
                    <div class="h3 mb-0">—</div>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <div class="text-muted small">Tồn kho</div>
                    <div class="h3 mb-0">—</div>
                </div>
            </div>
        </div>
    </div>

    <div class="row mt-4">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">Chứng từ gần đây</div>
                <div class="card-body">
                    <p class="text-muted text-center py-4">
                        Chưa có dữ liệu. Đây là placeholder sẽ được thay bằng grid master-detail.
                    </p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">Công việc trong ngày</div>
                <div class="card-body">
                    <p class="text-muted text-center py-4">Trống</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Create urls.py**

`apps/ui_modern/urls.py`:
```python
from django.urls import path
from .views import DashboardView

app_name = 'ui_modern'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
```

- [ ] **Step 5: Create static files**

`static/shared/css/variables.css`:
```css
:root {
    --brand-primary: #2563eb;
    --brand-accent: #16a34a;

    --color-primary: var(--brand-primary);
    --color-primary-hover: color-mix(in srgb, var(--brand-primary) 85%, black);
    --color-primary-light: color-mix(in srgb, var(--brand-primary) 10%, white);

    --color-success: #16a34a;
    --color-warning: #d97706;
    --color-danger: #dc2626;

    --color-text: #111827;
    --color-text-muted: #6b7280;
    --color-bg: #ffffff;
    --color-bg-subtle: #f9fafb;
    --color-bg-muted: #f3f4f6;
    --color-border: #e5e7eb;

    --sidebar-width: 256px;
    --topbar-height: 56px;
}
```

`static/modern/css/main.css`:
```css
/* Modern UI layout */
* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--color-bg-subtle);
    color: var(--color-text);
    font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.5;
}

.topbar {
    height: var(--topbar-height);
    background: var(--color-bg);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    padding: 0 16px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.topbar-left { width: var(--sidebar-width); padding-right: 16px; }
.topbar-center { flex: 1; max-width: 480px; }
.topbar-right { margin-left: auto; display: flex; gap: 8px; align-items: center; }

.global-search {
    background: var(--color-bg-muted);
    border: 1px solid transparent;
}
.global-search:focus {
    background: var(--color-bg);
    border-color: var(--color-primary);
    outline: none;
}

.layout-body { display: flex; min-height: calc(100vh - var(--topbar-height)); }

.sidebar {
    width: var(--sidebar-width);
    background: var(--color-bg);
    border-right: 1px solid var(--color-border));
    padding: 16px 0;
    overflow-y: auto;
    position: sticky;
    top: var(--topbar-height);
    height: calc(100vh - var(--topbar-height));
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    color: var(--color-text);
    text-decoration: none;
    font-size: 14px;
}
.nav-item:hover {
    background: var(--color-primary-light);
    color: var(--color-primary);
}
.nav-item i { font-size: 16px; }

.nav-section { margin-top: 16px; }
.nav-section-title {
    padding: 4px 16px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--color-text-muted);
    font-weight: 600;
}

.main-content {
    flex: 1;
    padding: 0;
    background: var(--color-bg-subtle);
}

.stat-card {
    border: 1px solid var(--color-border);
    border-radius: 8px;
    transition: box-shadow 0.15s;
}
.stat-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.layout-switcher {
    position: fixed;
    bottom: 16px;
    right: 16px;
    z-index: 1000;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: 24px;
    padding: 4px;
    display: flex;
    gap: 2px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
.layout-switcher a {
    padding: 8px 12px;
    text-decoration: none;
    color: var(--color-text-muted);
    border-radius: 20px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.layout-switcher a:hover { background: var(--color-bg-muted); color: var(--color-text); }
.layout-switcher a.active { background: var(--color-primary-light); color: var(--color-primary); }
```

`templates/shared/_layout_switcher.html`:
```html
<div class="layout-switcher">
    {% for layout in available_layouts %}
    <a href="{{ layout.url_prefix }}"
       class="{% if current_layout == layout.code %}active{% endif %}"
       title="{{ layout.name }}">
        <i class="bi {{ layout.icon }}"></i>
        <span class="d-none d-md-inline">{{ layout.name }}</span>
    </a>
    {% endfor %}
</div>
```

- [ ] **Step 6: Run check**

```bash
python manage.py check
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add apps/ui_modern/ templates/ static/
git commit -m "feat(ui_modern): base layout + dashboard placeholder"
```

---

## Task 11: Login page (verify against SIS)

**Files:**
- Create: `apps/ui_modern/views/auth_views.py`, `apps/ui_modern/forms/auth_forms.py`, `templates/modern/auth/login.html`
- Modify: `apps/ui_modern/urls.py`, `config/urls.py`

- [ ] **Step 1: VERIFY SIS LOGIN SCREEN**

Open https://pkm.erpsme.vn/ in browser. Note key elements:
- Logo (PMKetoan-style)
- Two inputs: "Tên đăng nhập" + "Mật khẩu ..."
- "Đăng nhập" button
- Brand colors (blue/clean)
- Warranty expiry notice: "Hạn bảo hành: 21-01-2027"

Take screenshot for reference: `screenshots/sis-login-reference.png`

- [ ] **Step 2: Create auth form**

`apps/ui_modern/forms/auth_forms.py`:
```python
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tên đăng nhập',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mật khẩu',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        return cleaned
```

`apps/ui_modern/forms/__init__.py`:
```python
from .auth_forms import LoginForm

__all__ = ['LoginForm']
```

- [ ] **Step 3: Create auth views**

`apps/ui_modern/views/auth_views.py`:
```python
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from ..forms import LoginForm


class PMKetoanLoginView(LoginView):
    template_name = 'modern/auth/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('ui_modern:dashboard')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Đăng nhập'
        return ctx


class PMKetoanLogoutView(LogoutView):
    next_page = '/auth/login/'
```

- [ ] **Step 4: Update apps/ui_modern/views/__init__.py**

```python
from .dashboard_views import DashboardView
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView

__all__ = ['DashboardView', 'PMKetoanLoginView', 'PMKetoanLogoutView']
```

- [ ] **Step 5: Create login template**

`templates/modern/auth/login.html`:
```html
{% load static %}
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập — {{ brand.name }}</title>
    <link rel="icon" href="{{ brand.favicon }}">
    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap.min.css' %}">
    <link rel="stylesheet" href="{% static 'vendor/css/bootstrap-icons.min.css' %}">
    <link rel="stylesheet" href="{% static 'shared/css/variables.css' %}">
    <link rel="stylesheet" href="{% static 'modern/css/auth.css' %}">
</head>
<body class="auth-page">
    <div class="auth-container">
        <div class="auth-card">
            <div class="auth-logo">
                {% if brand.logo %}
                <img src="{{ brand.logo }}" alt="{{ brand.name }}" height="48">
                {% else %}
                <h2>{{ brand.name }}</h2>
                {% endif %}
            </div>

            <form method="post">
                {% csrf_token %}

                {% if form.errors %}
                <div class="alert alert-danger">
                    Tên đăng nhập hoặc mật khẩu không đúng.
                </div>
                {% endif %}

                <div class="mb-3">
                    <div class="input-group">
                        <span class="input-group-text"><i class="bi bi-person"></i></span>
                        <input type="text" name="username" class="form-control"
                               placeholder="Tên đăng nhập"
                               value="{{ form.username.value|default:'' }}"
                               autofocus required>
                    </div>
                </div>

                <div class="mb-3">
                    <div class="input-group">
                        <span class="input-group-text"><i class="bi bi-lock"></i></span>
                        <input type="password" name="password" class="form-control"
                               placeholder="Mật khẩu" required>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary w-100">
                    Đăng nhập
                </button>

                <input type="hidden" name="next" value="{{ next }}">
            </form>

            <div class="auth-footer">
                <small class="text-muted">© 2026 {{ brand.name }}</small>
            </div>
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 6: Create auth.css**

`static/modern/css/auth.css`:
```css
body.auth-page {
    margin: 0;
    background: linear-gradient(135deg, var(--color-primary) 0%, #1e40af 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Be Vietnam Pro', sans-serif;
}

.auth-container {
    width: 100%;
    max-width: 400px;
    padding: 16px;
}

.auth-card {
    background: white;
    border-radius: 12px;
    padding: 40px 32px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.auth-logo {
    text-align: center;
    margin-bottom: 32px;
}

.auth-logo h2 {
    color: var(--color-primary);
    margin: 0;
}

.btn-primary {
    background: var(--color-primary);
    border-color: var(--color-primary);
}

.auth-footer {
    text-align: center;
    margin-top: 24px;
}
```

- [ ] **Step 7: Update urls.py**

`apps/ui_modern/urls.py`:
```python
from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import DashboardView, PMKetoanLoginView, PMKetoanLogoutView

app_name = 'ui_modern'

urlpatterns = [
    path('', login_required(DashboardView.as_view()), name='dashboard'),
]
```

`config/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from apps.ui_modern.views import PMKetoanLoginView, PMKetoanLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/login/', PMKetoanLoginView.as_view(), name='login'),
    path('auth/logout/', PMKetoanLogoutView.as_view(), name='logout'),
    path('', RedirectView.as_view(url='/modern/', permanent=False)),
    path('modern/', include('apps.ui_modern.urls')),
]
```

- [ ] **Step 8: Run dev server and verify login**

```bash
python manage.py migrate
python manage.py createsuperuser  # username=admin, password=...
python manage.py runserver
```

Open http://localhost:8000/auth/login/ → should show login form.
Login with admin → redirected to /modern/ dashboard.

- [ ] **Step 9: COMPARE with SIS login**

Visual comparison:
- SIS: 2 inputs + 1 button + logo ✓
- PMKetoan: 2 inputs + 1 button + brand name/logo ✓

Functionality:
- Login with valid creds → redirect to dashboard ✓
- Login with wrong password → show error ✓

- [ ] **Step 10: Commit**

```bash
git add apps/ui_modern/ templates/ static/ config/urls.py
git commit -m "feat(ui_modern): login page matching SIS layout"
```

---

## Task 12: Health check + middleware tests

**Files:**
- Create: `apps/ui_modern/views/health_views.py`, `templates/modern/health.html` (optional)
- Modify: `apps/ui_modern/urls.py`, `apps/ui_modern/views/__init__.py`
- Test: `tests/test_health.py`

- [ ] **Step 1: Write failing test**

`tests/test_health.py`:
```python
import pytest
from django.test import Client


def test_health_ok(client):
    response = client.get('/health/')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'


def test_health_detailed_includes_db(client):
    response = client.get('/health/detailed/')
    assert response.status_code == 200
    data = response.json()
    assert 'database' in data['checks']
    assert data['checks']['database']['status'] == 'ok'


def test_health_detailed_includes_cache(client):
    response = client.get('/health/detailed/')
    data = response.json()
    assert 'cache' in data['checks']
    assert data['checks']['cache']['status'] == 'ok'
```

- [ ] **Step 2: Run tests (fail)**

```bash
pytest tests/test_health.py -v
```

- [ ] **Step 3: Create health views**

`apps/ui_modern/views/health_views.py`:
```python
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache


def health_simple(request):
    """Lightweight health check for load balancer."""
    return JsonResponse({'status': 'ok'})


def health_detailed(request):
    """Detailed health check with component status."""
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
    }
    all_ok = all(c.get('status') == 'ok' for c in checks.values())
    return JsonResponse({
        'status': 'ok' if all_ok else 'degraded',
        'checks': checks,
    }, status=200 if all_ok else 503)


def _check_database():
    try:
        connections['default'].cursor().execute('SELECT 1')
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _check_cache():
    try:
        cache.set('_health_check', '1', 10)
        val = cache.get('_health_check')
        if val in (b'1', '1'):
            return {'status': 'ok'}
        return {'status': 'error', 'error': 'Cache set/get mismatch'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
```

- [ ] **Step 4: Update apps/ui_modern/views/__init__.py**

```python
from .dashboard_views import DashboardView
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .health_views import health_simple, health_detailed

__all__ = [
    'DashboardView', 'PMKetoanLoginView', 'PMKetoanLogoutView',
    'health_simple', 'health_detailed',
]
```

- [ ] **Step 5: Add URLs to config/urls.py**

```python
from apps.ui_modern.views import health_simple, health_detailed

urlpatterns = [
    # ... existing ...
    path('health/', health_simple, name='health_simple'),
    path('health/detailed/', health_detailed, name='health_detailed'),
]
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_health.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/ui_modern/views/ config/urls.py tests/test_health.py
git commit -m "feat(core): health check endpoints"
```

---

## Task 13: Initial data fixtures

**Files:**
- Create: `apps/core/management/commands/create_demo_company.py`, `apps/core/management/commands/seed_demo.py`, `apps/core/management/__init__.py`, `apps/core/management/commands/__init__.py`

- [ ] **Step 1: Create management command structure**

```bash
mkdir -p apps/core/management/commands
touch apps/core/management/__init__.py apps/core/management/commands/__init__.py
```

- [ ] **Step 2: Create create_demo_company command**

`apps/core/management/commands/create_demo_company.py`:
```python
"""Create demo company matching SIS PKM."""
from django.core.management.base import BaseCommand
from apps.core.models import Company


class Command(BaseCommand):
    help = 'Create demo company (PKM) matching SIS for verification'

    def handle(self, *args, **options):
        company, created = Company.objects.update_or_create(
            code='PKM',
            defaults={
                'name': 'CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM',
                'tax_code': '0101218690',
                'address': 'Tầng 06, Toà Nhà Icon4, Số 243A Đê La Thành, Hà Nội',
                'accounting_regime': 'tt133',
                'default_currency': 'VND',
                'brand_name': 'PKM Accounting',
                'brand_primary_color': '#2563eb',
                'is_active': True,
            },
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} demo company: {company.code} - {company.name}'
        ))
```

- [ ] **Step 3: Create seed_demo command**

`apps/core/management/commands/seed_demo.py`:
```python
"""Seed demo data for development."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import Company
from apps.identity.models import Role, Permission, UserCompanyRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed demo data: company + admin user + sample permissions'

    def handle(self, *args, **options):
        # 1. Create demo company
        company, _ = Company.objects.update_or_create(
            code='PKM',
            defaults={
                'name': 'CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM',
                'tax_code': '0101218690',
                'accounting_regime': 'tt133',
            },
        )

        # 2. Create admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@local.test',
                'full_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(f'Created admin user (password: admin123)')

        # 3. Create core permissions
        core_perms = [
            ('gl.voucher.view', 'ledger', 'View vouchers'),
            ('gl.voucher.create', 'ledger', 'Create voucher'),
            ('gl.voucher.edit', 'ledger', 'Edit voucher'),
            ('gl.voucher.delete', 'ledger', 'Delete voucher'),
            ('gl.voucher.post', 'ledger', 'Post voucher to ledger'),
            ('gl.voucher.lock', 'ledger', 'Lock voucher'),
            ('sales.invoice.view', 'sales', 'View sales invoices'),
            ('sales.invoice.create', 'sales', 'Create sales invoice'),
            ('purchase.invoice.view', 'purchasing', 'View purchase invoices'),
            ('purchase.invoice.create', 'purchasing', 'Create purchase invoice'),
            ('system.user.manage', 'system', 'Manage users'),
        ]
        for code, module, name in core_perms:
            Permission.objects.update_or_create(
                code=code,
                defaults={'module': module, 'name': name},
            )

        # 4. Create accountant role
        role, _ = Role.objects.update_or_create(
            company=company,
            code='accountant',
            defaults={'name': 'Kế toán viên'},
        )
        gl_perms = Permission.objects.filter(module='ledger')
        role.permissions.set(gl_perms)

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete. Company: {company.code}, User: admin, Perms: {core_perms.__len__()}'
        ))
```

- [ ] **Step 4: Run seed**

```bash
python manage.py seed_demo
```

Expected: "Seed complete. Company: PKM, User: admin, Perms: 12"

- [ ] **Step 5: Verify**

```bash
python manage.py shell -c "from apps.core.models import Company; print(Company.objects.count(), 'companies')"
python manage.py shell -c "from apps.identity.models import User; print(User.objects.count(), 'users')"
```

Expected: 1 companies, 1 users.

- [ ] **Step 6: Commit**

```bash
git add apps/core/management/
git commit -m "feat(core): demo data seed command"
```

---

## Task 14: systemd unit templates

**Files:**
- Create: `deploy/systemd/pmketoan-web.service`, `deploy/systemd/pmketoan-qcluster.service`

- [ ] **Step 1: Create web service unit**

`deploy/systemd/pmketoan-web.service`:
```ini
[Unit]
Description=PMKetoan Gunicorn Web Server
After=network.target mariadb.service

[Service]
Type=notify
User=pmketoan
Group=www-data
WorkingDirectory=/home/pmketoan/app
Environment="PATH=/home/pmketoan/app/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
EnvironmentFile=/home/pmketoan/app/.env
ExecStart=/home/pmketoan/app/.venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/pmketoan/gunicorn-access.log \
    --error-logfile /var/log/pmketoan/gunicorn-error.log \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5s

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/log/pmketoan /home/pmketoan/app/staticfiles /home/pmketoan/app/media
RestrictSUIDSGID=true
RemoveIPC=true

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Create django-q2 cluster unit**

`deploy/systemd/pmketoan-qcluster.service`:
```ini
[Unit]
Description=PMKetoan django-q2 Cluster (background workers)
After=network.target mariadb.service pmketoan-web.service

[Service]
Type=simple
User=pmketoan
Group=www-data
WorkingDirectory=/home/pmketoan/app
Environment="PATH=/home/pmketoan/app/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.prod"
EnvironmentFile=/home/pmketoan/app/.env
ExecStart=/home/pmketoan/app/.venv/bin/python manage.py qcluster
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure
RestartSec=10s

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/log/pmketoan /home/pmketoan/app/media

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Commit**

```bash
git add deploy/systemd/
git commit -m "feat(deploy): systemd units for gunicorn + django-q2"
```

---

## Task 15: Nginx config + .env.example + README

**Files:**
- Create: `deploy/nginx/pmketoan.conf`, `.env.example`, `README.md`, `Makefile`, `scripts/install_vendor_assets.sh`

- [ ] **Step 1: Create Nginx config**

`deploy/nginx/pmketoan.conf`:
```nginx
server {
    listen 80;
    server_name pmketoan.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pmketoan.example.com;

    ssl_certificate /etc/letsencrypt/live/pmketoan.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pmketoan.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    client_max_body_size 50M;

    location /static/ {
        alias /home/pmketoan/app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /media/ {
        alias /home/pmketoan/app/media/;
        expires 30d;
        access_log off;
    }

    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    location /auth/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/proxy_params.conf;
        proxy_read_timeout 120s;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 1000;
}
```

- [ ] **Step 2: Create .env.example**

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-insecure-key-change-in-prod
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=pmketoan
DB_USER=pmketoan
DB_PASSWORD=devpass
DB_HOST=127.0.0.1
DB_PORT=3306
DB_CONN_MAX_AGE=60

# Test DB
TEST_DB_NAME=test_pmketoan
TEST_DB_USER=root
TEST_DB_PASSWORD=

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Sentry (optional)
SENTRY_DSN=
```

- [ ] **Step 3: Create Makefile**

```makefile
.PHONY: help install dev test lint format migrate qcluster

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv venv --python 3.12
	uv pip install -r requirements/dev.txt
	bash scripts/install_vendor_assets.sh

dev: ## Run dev server
	uv run python manage.py migrate
	uv run python manage.py seed_demo
	uv run python manage.py runserver

qcluster: ## Start django-q2 cluster
	uv run python manage.py qcluster

test: ## Run tests
	uv run pytest

test-fast: ## Run tests parallel
	uv run pytest -n auto

lint: ## Run linters
	uv run ruff check apps/
	uv run ruff format --check apps/

format: ## Format code
	uv run ruff format apps/

migrate: ## Run migrations
	uv run python manage.py migrate

makemigrations: ## Create migrations
	uv run python manage.py makemigrations

shell: ## Django shell
	uv run python manage.py shell_plus

superuser: ## Create superuser
	uv run python manage.py createsuperuser

clean: ## Clean caches
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
```

- [ ] **Step 4: Create install_vendor_assets.sh**

`scripts/install_vendor_assets.sh`:
```bash
#!/bin/bash
set -euo pipefail

mkdir -p static/vendor/css static/vendor/js static/vendor/fonts

# Install npm packages (no save)
npm install --no-save --prefix /tmp/pmketoan-vendor \
    bootstrap@5.3.3 \
    bootstrap-icons@1.11.3 \
    htmx.org@2.0.0 \
    alpinejs@3.14.1

# Copy
VENDOR=/tmp/pmketoan-vendor/node_modules
cp $VENDOR/bootstrap/dist/css/bootstrap.min.css static/vendor/css/
cp $VENDOR/bootstrap/dist/js/bootstrap.bundle.min.js static/vendor/js/
cp $VENDOR/bootstrap-icons/font/bootstrap-icons.min.css static/vendor/css/
cp -r $VENDOR/bootstrap-icons/font/fonts/* static/vendor/fonts/
cp $VENDOR/htmx.org/dist/htmx.min.js static/vendor/js/
cp $VENDOR/alpinejs/dist/cdn.min.js static/vendor/js/alpine.min.js

echo "✓ Vendor assets installed to static/vendor/"
```

```bash
chmod +x scripts/install_vendor_assets.sh
```

- [ ] **Step 5: Create README.md**

```markdown
# PMKetoan

Vietnamese accounting software. Built with Django 5.2 + django-ninja + HTMX + Alpine.js + MariaDB.

## Quick Start

```bash
# Install dependencies
make install

# Setup database (requires MariaDB running)
mysql -u root -e "CREATE DATABASE pmketoan CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'pmketoan'@'localhost' IDENTIFIED BY 'devpass'; GRANT ALL ON pmketoan.* TO 'pmketoan'@'localhost';"

# Configure environment
cp .env.example .env

# Run migrations + seed demo data
make migrate
uv run python manage.py seed_demo

# Start dev server
make dev
# Open http://localhost:8000/auth/login/ → admin / admin123
```

## Documentation

See `docs/` for full design documentation:
- `docs/README.md` — Master index
- `docs/01-tong-quan/` — System overview
- `docs/09-ke-hoach-trien-khai/` — Roadmap

## Testing

```bash
make test
make test-fast  # parallel
```

## Deployment

See `docs/05-kien-truc-ky-thuat/06-deployment.md`.
```

- [ ] **Step 6: Commit**

```bash
git add deploy/ .env.example Makefile scripts/ README.md
git commit -m "feat: deployment configs + dev tooling"
```

---

## Task 16: Final verification against SIS

- [ ] **Step 1: Run all tests**

```bash
make test
```

Expected: All tests PASS, coverage > 80% for `apps/core/`, `apps/identity/`, `apps/ui_modern/`.

- [ ] **Step 2: Run lint + type check**

```bash
make lint
uv run mypy apps/
```

Expected: Clean.

- [ ] **Step 3: Verify login flow vs SIS**

```bash
make dev
```

Open http://localhost:8000/auth/login/ → Compare with https://pkm.erpsme.vn/:

| Element | SIS | PMKetoan | Match? |
|---------|-----|----------|--------|
| Logo / brand | Yes | Yes (brand.name) | ✓ |
| Username field | "Tên đăng nhập" | "Tên đăng nhập" | ✓ |
| Password field | "Mật khẩu ..." | "Mật khẩu" | ✓ |
| Submit button | "Đăng nhập" | "Đăng nhập" | ✓ |
| Warranty notice | "Hạn bảo hành" | (skip for now) | ✗ Phase 1 |

- [ ] **Step 4: Verify dashboard layout vs SIS**

Login to SIS, see /about page. Compare:
- Sidebar menu items (Cập nhật số liệu, Sổ sách, Báo cáo, Danh mục)
- Top bar (logo, search, user menu)

| Element | SIS | PMKetoan | Match? |
|---------|-----|----------|--------|
| Sidebar groups | 5 groups | 4 groups (placeholder) | ~ Phase 1 adds all |
| Top search | Yes | Yes | ✓ |
| User dropdown | Yes | Yes | ✓ |
| Layout switcher | No (SIS has 1 UI) | Yes (4 layouts) | + PMKetoan adds |

- [ ] **Step 5: Verify accounting data**

```bash
uv run python manage.py shell
```

```python
from apps.core.models import Company
c = Company.objects.get(code='PKM')
print(f'Company: {c.name}')
print(f'Regime: {c.accounting_regime}')
print(f'Tax: {c.tax_code}')
```

Expected output:
```
Company: CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM
Regime: tt133
Tax: 0101218690
```

Compare with SIS:
- SIS company: CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM ✓
- SIS MST: 0101218690 ✓
- SIS regime: TT133 ✓

- [ ] **Step 6: Final commit**

```bash
git add docs/superpowers/plans/2026-06-17-phase-0-foundation.md
git commit -m "docs: Phase 0 implementation plan"
git tag v0.1.0-phase0
```

---

## Phase 0 Acceptance Criteria

Phase 0 is **complete** when:

- [ ] All tests pass: `make test`
- [ ] Coverage ≥ 80% for `apps/core/`, `apps/identity/`, `apps/ui_modern/`
- [ ] Lint clean: `make lint`
- [ ] Login page renders and matches SIS structure
- [ ] Dashboard renders with sidebar + topbar
- [ ] Health check returns 200 OK
- [ ] Demo company PKM seeded correctly
- [ ] Admin user can login (admin / admin123)
- [ ] systemd + Nginx templates in `deploy/`
- [ ] Documentation in `docs/superpowers/plans/`
- [ ] Verified against SIS at https://pkm.erpsme.vn/

## Next: Phase 1 (General Ledger + Master Data)

After Phase 0 is approved, Phase 1 will cover:
- Chart of Accounts (TT133, ~120 TK)
- AccountingVoucher + VoucherLine models
- VoucherPostingService (post/unpost)
- Voucher list + form (Modern UI, Standard style)
- Sổ cái (General Ledger)
- Bảng cân đối tài khoản (Trial balance)
- Audit log

Estimated effort: ~8 weeks.

---

## Self-Review Checklist

After writing the plan, run through:

1. **Spec coverage**:
   - FR-CORE-01 (multi-tenant via company_id) ✓ Task 3
   - FR-CORE-02 (switch company via session) — deferred to Phase 1
   - FR-CORE-03 (fiscal year) — deferred to Phase 1
   - FR-CORE-04 (audit log) — deferred to Phase 1
   - FR-IDX-01 (login username/password) ✓ Task 11
   - FR-IDX-04 (lock after 5 failed) ✓ via django-axes
   - FR-IDX-05 (RBAC) ✓ Tasks 5-7
   - FR-UI-01 (multi-URL layout packs) ✓ Task 10 (Modern only, others in Phase 7)
   - FR-UI-17 (3 UX dimensions) ✓ Task 8-9
   - FR-UI-20 (plugin registry) ✓ Task 8

2. **Placeholder scan**: ✓ No TBD/TODO in tasks. All code is concrete.

3. **Type consistency**:
   - `Company.code` used consistently ✓
   - `User.username` matches auth backend ✓
   - `InteractionStyle.code` is str, `Role.code` is str ✓
   - `UXContext` fields match defaults.py ✓

---

**Plan complete.** 16 tasks, ~1-2 days of focused work for Phase 0 Foundation.
