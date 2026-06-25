"""E2E: Inventory + Assets."""

import pytest
from playwright.sync_api import expect


# Inventory

@pytest.mark.e2e
def test_stock_dashboard_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/inventory/dashboard/")
    expect(logged_in_page.locator("h1, h2, h3").first).to_be_visible()


@pytest.mark.e2e
def test_stock_voucher_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/stock-vouchers/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_stock_adjustment_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/inventory/adjustments/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_stock_card_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/inventory/stock-card/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# Assets

@pytest.mark.e2e
def test_asset_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/assets/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_asset_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/assets/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_depreciation_run_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/assets/depreciation/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_asset_transaction_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/assets/transactions/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# Permissions

@pytest.mark.e2e
def test_inventory_permission_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/stock-vouchers/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_assets_permission_for_hr(login_as):
    page = login_as("e2e_hr")
    page.goto("http://127.0.0.1:8903/modern/assets/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url
