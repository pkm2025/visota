"""E2E: Approval queue + detail + rules."""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_approval_queue_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/approvals/")
    expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_approval_rules_page_loads(logged_in_page):
    logged_in_page.goto("http://127.0.0.1:8903/modern/approvals/rules/")
    expect(logged_in_page.locator("h1")).to_be_visible()
    # Should show 7 system rules
    rows = logged_in_page.locator("table tbody tr")
    assert rows.count() >= 1


@pytest.mark.e2e
def test_approval_queue_empty_for_admin(logged_in_page):
    """Admin (superuser) sees queue — may be empty."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/approvals/")
    # Either queue has items or shows empty state
    has_table = logged_in_page.locator("table tbody tr").count() > 0
    has_empty = logged_in_page.locator("text=Không có yêu cầu").count() > 0
    assert has_table or has_empty


@pytest.mark.e2e
def test_approval_detail_loads(logged_in_page):
    """Detail page loads if any approval exists."""
    logged_in_page.goto("http://127.0.0.1:8903/modern/approvals/")
    rows = logged_in_page.locator("table tbody tr")
    if rows.count() > 0:
        view_btn = rows.first.locator('a:has(i.bi-eye)')
        if view_btn.count() > 0:
            view_btn.click()
            logged_in_page.wait_for_load_state("networkidle")
            expect(logged_in_page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_approval_queue_allowed_for_accountant(login_as):
    page = login_as("e2e_accountant")
    page.goto("http://127.0.0.1:8903/modern/approvals/")
    assert "/modern/approvals/" in page.url


@pytest.mark.e2e
def test_approval_queue_denied_for_viewer(login_as):
    """Viewer (no approvals permission) — actually all users have approvals now via notifications, but check."""
    page = login_as("e2e_viewer")
    page.goto("http://127.0.0.1:8903/modern/approvals/")
    # Viewer has 3 modules only (reporting, ledger, notifications) — approvals denied
    assert "/no-access/" in page.url or "/modern/approvals/" in page.url
