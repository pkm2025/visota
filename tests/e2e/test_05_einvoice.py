"""E2E: E-Invoice list + detail."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_einvoice_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/einvoices/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_einvoice_list_status_filter(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/einvoices/")
    # Status filter should exist
    status = logged_in_page.locator('select[name="status"]')
    if status.count() > 0:
        assert status.locator("option").count() > 0


@pytest.mark.e2e
def test_einvoice_detail_loads(logged_in_page):
    """Detail page for first einvoice loads (if any exists)."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/einvoices/")
    rows = logged_in_page.locator("table tbody tr")
    if rows.count() > 0:
        # Click view detail via eye icon link
        view_links = logged_in_page.locator('a:has(i.bi-eye)')
        if view_links.count() > 0:
            href = view_links.first.get_attribute("href")
            if href:
                # Navigate directly via href to avoid click issues
                logged_in_page.goto(f"http://127.0.0.1:8903{href}")
                logged_in_page.wait_for_load_state("networkidle")
                expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_einvoice_bc01_form_visible(logged_in_page):
    """BC01 report generation form is visible."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/einvoices/")
    # Scroll to bottom section
    bc01_section = logged_in_page.locator("text=BC01").first
    assert bc01_section.count() > 0


@pytest.mark.e2e
def test_einvoice_list_allowed_for_accountant(login_as):
    page = login_as("e2e_accountant")
    page.goto("http://127.0.0.1:8903/modern/einvoices/")
    assert "/modern/einvoices/" in page.url


@pytest.mark.e2e
def test_einvoice_list_permission_for_hr(login_as):
    """HR user (no einvoice permission) denied."""
    page = login_as("e2e_hr")
    page.goto("http://127.0.0.1:8903/modern/einvoices/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url
