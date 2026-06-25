"""E2E: Mobile viewport tests — verify responsive layout on phone-sized screens.

Uses iPhone 12 (390x844) as canonical mobile viewport.
"""

import pytest
from playwright.sync_api import expect


@pytest.fixture
def mobile_page(page):
    """Page with iPhone 12 viewport."""
    page.set_viewport_size({"width": 390, "height": 844})
    yield page


@pytest.fixture
def mobile_logged_in(mobile_page):
    """Login as admin on mobile viewport."""
    mobile_page.goto("http://127.0.0.1:8903/auth/login/")
    mobile_page.fill('input[name="username"]', "e2e_admin")
    mobile_page.fill('input[name="password"]', "E2EPass123!")
    mobile_page.click('button[type="submit"]')
    mobile_page.wait_for_load_state("networkidle")
    yield mobile_page


def _check_no_h_scroll(page, tolerance=20):
    """Check no VISIBLE horizontal overflow (excludes dropdowns and scrollable containers)."""
    overflow = page.evaluate("""(tolerance) => {
        const vp = window.innerWidth;
        const els = document.querySelectorAll('*');
        for (const el of els) {
            const r = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            if (style.position === 'absolute' || style.position === 'fixed') continue;
            if (r.width === 0 || r.height === 0) continue;
            // Skip elements inside scrollable container
            let p = el.parentElement;
            let inScrollable = false;
            while (p && p !== document.body) {
                if (p.classList.contains('table-responsive') ||
                    getComputedStyle(p).overflowX === 'auto' ||
                    getComputedStyle(p).overflowX === 'scroll') {
                    inScrollable = true;
                    break;
                }
                p = p.parentElement;
            }
            if (inScrollable) continue;
            if (r.right > vp + tolerance) {
                return {tag: el.tagName, cls: (el.className?.toString() || '').slice(0, 80), right: r.right, vp};
            }
        }
        return null;
    }""", tolerance)
    if overflow:
        pytest.fail(f"Horizontal overflow on mobile: {overflow}")


@pytest.mark.e2e
def test_login_mobile_responsive(mobile_page):
    mobile_page.goto("http://127.0.0.1:8903/auth/login/")
    expect(mobile_page.locator('input[name="username"]')).to_be_visible()
    expect(mobile_page.locator('input[name="password"]')).to_be_visible()
    expect(mobile_page.locator('button[type="submit"]')).to_be_visible()
    _check_no_h_scroll(mobile_page)


@pytest.mark.e2e
def test_dashboard_mobile_no_h_scroll(mobile_logged_in):
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_dashboard_topbar_center_hidden(mobile_logged_in):
    is_hidden = mobile_logged_in.evaluate("""() => {
        const el = document.querySelector('.topbar-center');
        if (!el) return true;
        return getComputedStyle(el).display === 'none';
    }""")
    assert is_hidden


@pytest.mark.e2e
def test_dashboard_right_sidebar_hidden(mobile_logged_in):
    is_hidden = mobile_logged_in.evaluate("""() => {
        const el = document.querySelector('.right-sidebar');
        if (!el) return true;
        const style = getComputedStyle(el);
        return style.display === 'none' || style.visibility === 'hidden';
    }""")
    assert is_hidden


@pytest.mark.e2e
def test_body_font_size_mobile(mobile_logged_in):
    size = mobile_logged_in.evaluate("() => parseFloat(getComputedStyle(document.body).fontSize)")
    assert size >= 13, f"Body font {size}px too small"


@pytest.mark.e2e
def test_voucher_list_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/vouchers/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_voucher_create_form_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/vouchers/new/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_einvoice_list_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/einvoices/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_approval_queue_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/approvals/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_banking_reconcile_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/banking/reconcile/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_payroll_run_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/payroll/run/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_sales_invoice_list_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/sales-invoices/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_customers_list_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/customers/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_projects_list_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/modern/projects/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)


@pytest.mark.e2e
def test_notifications_inbox_mobile(mobile_logged_in):
    mobile_logged_in.goto("http://127.0.0.1:8903/notifications/")
    mobile_logged_in.wait_for_load_state("networkidle")
    _check_no_h_scroll(mobile_logged_in)
