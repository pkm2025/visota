"""E2E: Purchase invoice + vendor list."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_purchase_invoice_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/purchase-invoices/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_purchase_invoice_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/purchase-invoices/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_vendor_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/vendors/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_vendor_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/vendors/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_vendor_export_excel(logged_in_page):
    """Vendor export returns Excel."""
    response = logged_in_page.request.get("http://127.0.0.1:8903/modern/vendors/export/")
    assert response.ok
    assert response.body()[:2] == b"PK"


@pytest.mark.e2e
def test_purchase_invoice_permission_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/purchase-invoices/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_purchase_invoice_allowed_for_purchaser(login_as):
    page = login_as("e2e_purchaser")
    page.goto("http://127.0.0.1:8903/modern/purchase-invoices/")
    assert "/modern/purchase-invoices/" in page.url
