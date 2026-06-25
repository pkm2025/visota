"""E2E: CRM — leads, opportunities, tickets, campaigns."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_crm_lead_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/leads/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_crm_lead_create_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/leads/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_crm_opportunity_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/opportunities/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_crm_opportunity_create_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/opportunities/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_crm_ticket_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/tickets/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_crm_campaign_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/crm/campaigns/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_crm_permission_for_accountant(login_as):
    page = login_as("e2e_accountant")
    page.goto("http://127.0.0.1:8903/modern/crm/leads/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url


@pytest.mark.e2e
def test_crm_allowed_for_sales(login_as):
    page = login_as("e2e_sales")
    page.goto("http://127.0.0.1:8903/modern/crm/leads/")
    assert "/modern/crm/leads/" in page.url
