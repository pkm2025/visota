"""Page Object base class — common patterns across all pages."""

import os
from pathlib import Path

from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8903")


class BasePage:
    BASE_URL = BASE_URL

    def __init__(self, page: Page):
        self.page = page

    def goto(self, path):
        self.page.goto(f"{self.BASE_URL}{path}")
        self.page.wait_for_load_state("networkidle")
        return self

    def click_nav_item(self, text):
        """Click a nav item by text."""
        self.page.click(f'.nav-item:has-text("{text}")')
        self.page.wait_for_load_state("networkidle")

    def expect_title(self, text):
        expect(self.page.locator("h1, h3").first).to_contain_text(text)

    def expect_toast(self, text=None, kind=None):
        """Wait for a toast notification."""
        selector = ".toast"
        if kind:
            selector += f".toast-{kind}"
        toast = self.page.locator(selector).first
        if text:
            expect(toast).to_contain_text(text)
        else:
            expect(toast).to_be_visible()
        return toast

    def expect_in_url(self, fragment):
        assert fragment in self.page.url, f"URL {self.page.url} doesn't contain {fragment}"

    def expect_status(self, code=None):
        """For HTTP status checks — Playwright doesn't expose response directly
        without route interception. Use page.error or response listener."""
        return self

    def screenshot(self, name):
        """Save screenshot for visual regression."""
        Path("tests/e2e/screenshots").mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=f"tests/e2e/screenshots/{name}.png", full_page=True)

    def click_button(self, text):
        self.page.click(f'button:has-text("{text}")')
        self.page.wait_for_load_state("networkidle")

    def fill_field(self, name, value):
        self.page.fill(f'[name="{name}"]', str(value))

    def select_option(self, name, value):
        self.page.select_option(f'[name="{name}"]', str(value))

    def submit_form(self, form_selector="form"):
        self.page.click(f'{form_selector} button[type="submit"]')
        self.page.wait_for_load_state("networkidle")


class LoginPage(BasePage):
    def login(self, username, password):
        self.goto("/auth/login/")
        self.fill_field("username", username)
        self.fill_field("password", password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state("networkidle")

    def expect_login_success(self):
        assert "/modern/" in self.page.url, f"Expected /modern/, got {self.page.url}"

    def expect_login_error(self, message=None):
        if message:
            expect(self.page.locator(".alert-danger")).to_contain_text(message)
        else:
            # Wait for either alert-danger or login page to persist
            assert "/auth/login/" in self.page.url or self.page.locator(".alert-danger").count() > 0


class DashboardPage(BasePage):
    def goto_dashboard(self):
        return self.goto("/modern/")

    def expect_kpi_cards(self):
        expect(self.page.locator(".stat-card").first).to_be_visible()

    def expect_recent_vouchers_table(self):
        expect(self.page.locator("table")).to_be_visible()

    def click_create_voucher(self):
        self.page.click('a:has-text("Tạo phiếu mới")')
        self.page.wait_for_load_state("networkidle")


# Module list page patterns
class ListPage(BasePage):
    TABLE_SELECTOR = "table"
    SEARCH_INPUT = 'input[name="search"]'

    def search(self, query):
        if self.page.locator(self.SEARCH_INPUT).count() > 0:
            self.fill_field("search", query)
            self.page.keyboard.press("Enter")
            self.page.wait_for_load_state("networkidle")

    def expect_rows(self, min_count=1):
        rows = self.page.locator(f"{self.TABLE_SELECTOR} tbody tr")
        expect(rows.nth(min_count - 1) if min_count > 0 else rows.first).to_be_visible()

    def expect_empty_state(self):
        expect(self.page.locator("text=Chưa có")).to_be_visible()

    def click_row_by_text(self, text):
        self.page.click(f'{self.TABLE_SELECTOR} tbody tr:has-text("{text}")')
        self.page.wait_for_load_state("networkidle")

    def get_row_count(self):
        return self.page.locator(f"{self.TABLE_SELECTOR} tbody tr").count()


class FormPage(BasePage):
    def fill_text_field(self, name, value):
        self.page.fill(f'[name="{name}"]', str(value))

    def fill_date_field(self, name, date_value):
        # date_value: "2026-06-24" YYYY-MM-DD
        self.page.fill(f'[name="{name}"]', str(date_value))

    def select_dropdown(self, name, value):
        self.page.select_option(f'[name="{name}"]', str(value))

    def click_checkbox(self, name, checked=True):
        cb = self.page.locator(f'[name="{name}"]')
        if checked:
            cb.check()
        else:
            cb.uncheck()

    def submit(self, button_text="Lưu"):
        self.click_button(button_text)

    def expect_validation_error(self, field_name=None, message=None):
        if field_name:
            expect(self.page.locator(f'[name="{field_name}"] + .invalid-feedback, [name="{field_name}"] ~ .text-danger')).to_be_visible()
        if message:
            expect(self.page.locator(f".invalid-feedback, .alert-danger").first).to_contain_text(message)

    def expect_success_redirect(self, url_fragment):
        expect(self.page).to_have_url(lambda u: url_fragment in u)


# Detail page patterns
class DetailPage(BasePage):
    def expect_field_value(self, label, value):
        # Look for dt containing label, then dd after
        loc = self.page.locator(f'dt:has-text("{label}") + dd')
        expect(loc).to_contain_text(str(value))

    def click_action_button(self, text):
        self.page.click(f'button:has-text("{text}"), a:has-text("{text}")')
        self.page.wait_for_load_state("networkidle")

    def expect_status_badge(self, text):
        expect(self.page.locator(f'.badge:has-text("{text}")')).to_be_visible()
