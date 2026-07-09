"""Pytest fixtures for E2E tests — hits running server, no DB fixtures needed.

E2E tests do NOT use test database. They hit the running dev/prod server.
Test users are pre-created via management command before tests run.
"""

import os
import subprocess

import pytest
from playwright.sync_api import sync_playwright

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8903")


def pytest_configure(config):
    """Ensure test users exist before any test runs."""
    # Run management command to ensure users + roles seeded
    script = """
from django.contrib.auth import get_user_model
from django.core.management import call_command
from apps.core.models import Company
from apps.identity.models import Role, UserCompanyRole
User = get_user_model()

call_command('seed_permissions', verbosity=0)

company = Company.objects.first()
if not company:
    company = Company.objects.create(code='E2E', name='E2E Test Co', tax_code='0101234567')

ROLES = [
    ('e2e_admin', 'Admin', True, None),
    ('e2e_accountant', 'KT', False, 'accountant'),
    ('e2e_sales', 'Sales', False, 'sales'),
    ('e2e_purchaser', 'Mua hang', False, 'purchaser'),
    ('e2e_hr', 'HR', False, 'hr_officer'),
    ('e2e_pm', 'PM', False, 'project_manager'),
    ('e2e_chief', 'KTT', False, 'chief_accountant'),
    ('e2e_viewer', 'Viewer', False, 'viewer'),
]
for username, full_name, is_super, role_code in ROLES:
    u, _ = User.objects.get_or_create(username=username, defaults={
        'full_name': full_name, 'email': f'{username}@e2e.test',
        'is_active': True, 'is_superuser': is_super, 'is_staff': is_super,
    })
    u.set_password('E2EPass123!')
    u.save()
    if not is_super and role_code:
        role = Role.objects.filter(code=role_code, company=company).first()
        if role:
            UserCompanyRole.objects.update_or_create(
                user=u, company=company, role=role, defaults={'is_default': True}
            )
print(f'E2E users ready: {User.objects.filter(username__startswith="e2e_").count()}')
"""
    result = subprocess.run(
        [".venv/Scripts/python.exe", "manage.py", "shell", "-c", script],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    if result.returncode != 0:
        print(f"Setup warning: {result.stderr[:200]}")


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright):
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()


def _login(page, username, password="E2EPass123!"):
    """Helper: login via the running server."""
    page.goto(f"{E2E_BASE_URL}/auth/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@pytest.fixture
def logged_in_page(page):
    """Login as admin and return page."""
    _login(page, "e2e_admin")
    yield page


@pytest.fixture
def login_as(page):
    """Factory: login_as('e2e_sales') logs in and returns page."""
    def _factory(username):
        _login(page, username)
        return page
    return _factory
