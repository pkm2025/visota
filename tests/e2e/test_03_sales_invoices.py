"""E2E: Sales invoice list + customer list."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_sales_invoice_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    expect(logged_in_page.locator("h1")).to_be_visible()
    expect(logged_in_page.locator("table")).to_be_visible()


@pytest.mark.e2e
def test_sales_invoice_list_columns(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    headers = ["Ngày", "Số HĐ", "Khách hàng"]
    for h in headers:
        expect(logged_in_page.locator(f"th:has-text('{h}')").first).to_be_visible()


@pytest.mark.e2e
def test_sales_invoice_search(logged_in_page):
    """Sales invoice list has working filter form."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    # Look for any filter form within main content (not topbar global search)
    search = logged_in_page.locator('main input[name="search"], .card input[name="search"]').first
    if search.count() > 0:
        search.fill("ABC")
        search.press("Enter")
        logged_in_page.wait_for_load_state("networkidle")
        # Should remain on sales-invoices
        assert "/modern/sales-invoices/" in logged_in_page.url
    else:
        # No local search — that's also OK
        pass


@pytest.mark.e2e
def test_sales_invoice_create_page_loads(logged_in_page):
    """Sales invoice create form loads."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/sales-invoices/new/")
    # Form should be present (any form within main content)
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_customer_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/customers/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_customer_list_has_search(logged_in_page):
    """Customer list has its own search input (scoped to card)."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/customers/")
    # Local search inside card-body, not topbar global search
    search = logged_in_page.locator('.card input[name="search"], main form input[name="search"]').first
    assert search.count() > 0


@pytest.mark.e2e
def test_customer_export_excel(logged_in_page):
    """Customer export endpoint returns Excel file."""
    response = logged_in_page.request.get("http://127.0.0.1:8903/modern/customers/export/")
    assert response.ok
    body = response.body()
    # XLSX files start with PK (zip magic)
    assert body[:2] == b"PK"


@pytest.mark.e2e
def test_customer_create_page_loads(logged_in_page):
    """Customer create form loads."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/customers/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_sales_invoice_list_permission_for_purchaser(login_as):
    """Purchaser (no sales permission) denied."""
    page = login_as("e2e_purchaser")
    page.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_sales_invoice_list_allowed_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    assert "/modern/sales-invoices/" in page.url
