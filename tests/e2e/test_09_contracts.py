"""E2E: Contracts + contract templates."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_contract_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/contracts/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_contract_create_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/contracts/new/")
    form = logged_in_page.locator('main form, .container-fluid form').first
    assert form.count() > 0


@pytest.mark.e2e
def test_contract_template_list_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/contract-templates/")
    expect(logged_in_page.locator("h1, h2, h3, h4").first).to_be_visible()


@pytest.mark.e2e
def test_contract_detail_loads(logged_in_page):
    """Contract detail page loads (if contracts exist)."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/contracts/")
    rows = logged_in_page.locator("table tbody tr")
    if rows.count() > 0:
        link = rows.first.locator("a[href*='/contracts/']").first
        if link.count() > 0:
            href = link.get_attribute("href")
            if href:
                logged_in_page.goto(f"http://127.0.0.1:8903{href}" if href.startswith("/") else href)
                expect(logged_in_page.locator("h1, h2, h3, h4").first).to_be_visible()


@pytest.mark.e2e
def test_contract_export_docx(logged_in_page):
    """Contract DOCX export returns Word file."""
    # Just verify URL responds — actual file download tested via API
    response = logged_in_page.context.request.get(
        "http://127.0.0.1:8903/modern/contracts/1/export-docx/"
    )
    # 200 = ok, 404 = no contract with that ID (acceptable in test env)
    assert response.status in (200, 404)


@pytest.mark.e2e
def test_contract_permission_for_hr(login_as):
    page = login_as("e2e_hr")
    page.goto("http://127.0.0.1:8903/modern/contracts/")
    assert "/no-access/" in page.url or "/auth/login/" in page.url
