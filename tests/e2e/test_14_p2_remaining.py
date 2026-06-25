"""E2E: Remaining modules — bidding, budget, FX, guarantees, loans."""

import pytest
from playwright.sync_api import expect


# Bidding

@pytest.mark.e2e
def test_bidding_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/bidding/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_bidding_permission_for_hr(login_as):
    page = login_as("e2e_hr")
    page.goto("http://127.0.0.1:8903/modern/bidding/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_bidding_allowed_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/bidding/")
    assert "/modern/bidding/" in page.url


# Budget

@pytest.mark.e2e
def test_budget_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/budget/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_cash_flow_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/cash-flow/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# FX

@pytest.mark.e2e
def test_fx_rate_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/fx/rates/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_fx_revaluation_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/fx/revaluation/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# Guarantees + Loans

@pytest.mark.e2e
def test_guarantees_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/guarantees/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_loans_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/loans/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# Treasury

@pytest.mark.e2e
def test_cash_receipt_create_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/treasury/receipt/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_cash_payment_create_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/treasury/payment/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


# Input invoices

@pytest.mark.e2e
def test_input_invoice_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/input-invoices/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# Period closing

@pytest.mark.e2e
def test_period_closing_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/closing/")
    expect(logged_in_page.locator("h1")).to_be_visible()


# No-access page

@pytest.mark.e2e
def test_no_access_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/no-access/")
    expect(logged_in_page.locator("h1, h2").first).to_be_visible()
