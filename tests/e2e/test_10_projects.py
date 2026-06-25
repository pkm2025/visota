"""E2E: Projects."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_project_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/projects/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_project_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/projects/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_project_detail_loads(logged_in_page):
    """Project detail page loads if projects exist."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/projects/")
    rows = logged_in_page.locator("table tbody tr")
    if rows.count() > 0:
        link = rows.first.locator("a[href*='/projects/']").first
        if link.count() > 0:
            href = link.get_attribute("href")
            if href:
                logged_in_page.goto(f"http://127.0.0.1:8903{href}" if href.startswith("/") else href)
                expect(logged_in_page.locator("h1, h2, h3").first).to_be_visible()


@pytest.mark.e2e
def test_project_permission_for_accountant(login_as):
    """Accountant (no projects permission) denied."""
    page = login_as("e2e_accountant")
    page.goto("http://127.0.0.1:8903/modern/projects/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_project_allowed_for_pm(login_as):
    page = login_as("e2e_pm")
    page.goto("http://127.0.0.1:8903/modern/projects/")
    assert "/modern/projects/" in page.url
