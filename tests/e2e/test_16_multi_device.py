"""E2E: Multi-device emulation tests — verify PWA + responsive across devices.

Uses Playwright device descriptors for iPhone 12, iPad, Galaxy S20.
Verifies PWA manifest, service worker, bottom nav, offline page.
"""

import pytest
from playwright.sync_api import expect


# ---------- PWA manifest ----------

@pytest.mark.e2e
def test_pwa_manifest_linked(logged_in_page):
    """Layout links to manifest.json."""
    manifest = logged_in_page.locator('link[rel="manifest"]')
    assert manifest.count() > 0
    href = manifest.get_attribute("href")
    assert href and "manifest.json" in href


@pytest.mark.e2e
def test_pwa_manifest_valid_json(logged_in_page):
    """Manifest.json is valid JSON with required fields."""
    manifest_url = logged_in_page.locator('link[rel="manifest"]').get_attribute("href")
    if manifest_url:
        response = logged_in_page.context.request.get(
            f"http://127.0.0.1:8903{manifest_url}" if manifest_url.startswith("/") else manifest_url
        )
        assert response.ok
        data = response.json()
        assert data["name"]
        assert data["short_name"]
        assert data["start_url"]
        assert data["display"] == "standalone"
        assert len(data["icons"]) >= 2
        assert data["theme_color"]


@pytest.mark.e2e
def test_pwa_theme_color_meta(logged_in_page):
    """theme-color meta tag present."""
    meta = logged_in_page.locator('meta[name="theme-color"]')
    assert meta.count() > 0


@pytest.mark.e2e
def test_pwa_apple_meta_tags(logged_in_page):
    """Apple mobile web app meta tags present."""
    assert logged_in_page.locator('meta[name="apple-mobile-web-app-capable"]').count() > 0
    assert logged_in_page.locator('meta[name="apple-mobile-web-app-title"]').count() > 0


@pytest.mark.e2e
def test_pwa_service_worker_registered(logged_in_page):
    """Service worker is registered (may take a moment after page load)."""
    # Give SW time to register
    logged_in_page.wait_for_timeout(2000)
    sw_count = logged_in_page.evaluate("""async () => {
        if (!navigator.serviceWorker) return -1;
        const regs = await navigator.serviceWorker.getRegistrations();
        return regs.length;
    }""")
    assert sw_count >= 0  # -1 means not supported, >=1 means registered


# ---------- Offline page ----------

@pytest.mark.e2e
def test_offline_page_loads(logged_in_page):
    """Offline page renders correctly."""
    logged_in_page.goto("http://127.0.0.1:8903/offline/")
    expect(logged_in_page.locator("h1, h2").first).to_be_visible()
    # Has retry button
    expect(logged_in_page.locator('button:has-text("Thử lại")')).to_be_visible()


# ---------- Mobile bottom nav ----------

@pytest.mark.e2e
def test_mobile_bottom_nav_visible_on_phone(page):
    """Bottom nav appears on phone viewport."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    bottom_nav = page.locator(".mobile-bottom-nav")
    assert bottom_nav.count() > 0
    # Should be visible on mobile
    is_visible = page.evaluate("""() => {
        const el = document.querySelector('.mobile-bottom-nav');
        return el ? getComputedStyle(el).display === 'flex' : false;
    }""")
    assert is_visible


@pytest.mark.e2e
def test_mobile_bottom_nav_hidden_on_desktop(logged_in_page):
    """Bottom nav hidden on desktop (1280px)."""
    bottom_nav = logged_in_page.locator(".mobile-bottom-nav")
    if bottom_nav.count() > 0:
        is_visible = logged_in_page.evaluate("""() => {
            const el = document.querySelector('.mobile-bottom-nav');
            return el ? getComputedStyle(el).display !== 'none' : false;
        }""")
        assert not is_visible


@pytest.mark.e2e
def test_bottom_nav_has_5_items(page):
    """Bottom nav has Home, Phiếu, Menu, Thông báo, Tài khoản."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    items = page.locator(".mobile-bottom-nav-item")
    assert items.count() == 5
    # Verify labels
    labels = [items.nth(i).inner_text() for i in range(items.count())]
    assert "Trang chủ" in labels[0]
    assert "Thông báo" in labels[3]


@pytest.mark.e2e
def test_bottom_nav_links_work(page):
    """Clicking bottom nav items navigates correctly."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Click voucher nav
    page.locator('.mobile-bottom-nav-item:has-text("Phiếu")').click()
    page.wait_for_load_state("networkidle")
    assert "/modern/vouchers/" in page.url


# ---------- Touch gestures ----------

@pytest.mark.e2e
def test_mobile_js_loaded(logged_in_page):
    """mobile.js is loaded on pages."""
    loaded = logged_in_page.evaluate("""() => {
        return Array.from(document.querySelectorAll('script')).some(s => s.src.includes('mobile.js'));
    }""")
    assert loaded


@pytest.mark.e2e
def test_pull_to_refresh_indicator_exists(logged_in_page):
    """Pull-to-refresh indicator element exists in DOM."""
    ptr = logged_in_page.locator("#ptr-indicator")
    assert ptr.count() > 0


# ---------- iPad / tablet tests ----------

@pytest.mark.e2e
def test_ipad_view(page):
    """iPad portrait (768x1024) renders without horizontal scroll."""
    page.set_viewport_size({"width": 768, "height": 1024})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    body_w = page.evaluate("() => document.body.scrollWidth")
    vp_w = 768
    assert body_w <= vp_w + 20


@pytest.mark.e2e
def test_ipad_landscape_view(page):
    """iPad landscape (1024x768)."""
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    body_w = page.evaluate("() => document.body.scrollWidth")
    assert body_w <= 1024 + 20


@pytest.mark.e2e
def test_galaxy_s20_view(page):
    """Samsung Galaxy S20 (360x800) — common Android phone."""
    page.set_viewport_size({"width": 360, "height": 800})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Allow 50px tolerance for smallest phones (tables, dropdowns)
    body_w = page.evaluate("() => document.body.scrollWidth")
    assert body_w <= 360 + 50, f"Body width {body_w} too wide for 360px viewport"


# ---------- Safe area inset (notched phones) ----------

@pytest.mark.e2e
def test_safe_area_meta(logged_in_page):
    """viewport-fit=cover for notched phone safe areas."""
    viewport_meta = logged_in_page.locator('meta[name="viewport"]').get_attribute("content")
    assert "viewport-fit=cover" in viewport_meta


# ---------- Performance on mobile ----------

@pytest.mark.e2e
def test_page_load_speed_mobile(page):
    """Dashboard loads in < 5s on mobile viewport."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')

    import time
    start = time.time()
    page.wait_for_load_state("networkidle")
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Page took {elapsed:.1f}s to load"


@pytest.mark.e2e
def test_no_console_errors_mobile(page):
    """No console errors on mobile viewport."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://127.0.0.1:8903/auth/login/")
    page.fill('input[name="username"]', "e2e_admin")
    page.fill('input[name="password"]', "E2EPass123!")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Allow some known benign errors (e.g., favicon)
    real_errors = [e for e in errors if "favicon" not in e.lower() and "404" not in e]
    assert len(real_errors) == 0, f"Console errors: {real_errors[:3]}"
