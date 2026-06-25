"""E2E: HR + Payroll."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_employee_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/employees/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_employee_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/employees/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_labor_contract_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/labor-contracts/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_dependent_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/dependents/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_insurance_dashboard_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/insurance/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_payroll_run_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/payroll/run/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_leave_request_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/leave/request/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_hr_permission_for_purchaser(login_as):
    page = login_as("e2e_purchaser")
    page.goto("http://127.0.0.1:8903/modern/employees/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_payroll_permission_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/payroll/run/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url
