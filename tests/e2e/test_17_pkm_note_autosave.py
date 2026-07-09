"""E2E: PKM note draft autosave to IndexedDB.

Covers VAL-CACHE-001 (drafts autosaved to IndexedDB),
VAL-CACHE-002 (drafts persist across reloads), VAL-CACHE-003 (drafts
recoverable after close/crash).

These tests drive the running dev server on port 8903 with a real
Chromium browser via Playwright. IndexedDB operations are real — we
query the pkm_cache database via page.evaluate to assert on draft rows.
"""

import pytest
from playwright.sync_api import expect

E2E_BASE_URL = "http://127.0.0.1:8903"


# --- Helpers ----------------------------------------------------------------


def open_indexeddb(page, db_name="pkm_cache", store="drafts"):
    """Ensure the Dexie database has been opened by the page (Dexie opens
    on first query, which PKMCache.getDrafts() triggers). Returns the
    list of draft rows currently in IndexedDB via a direct IDB query.
    """
    return page.evaluate(
        """
        async ({dbName, store}) => {
            // Ask Dexie to surface the db if the page hasn't opened it yet.
            if (window.PKMCache && window.PKMCache.db) {
                try { await window.PKMCache.db.open(); } catch (e) {}
            }
            return new Promise((resolve, reject) => {
                const req = indexedDB.open(dbName);
                req.onsuccess = function () {
                    const db = req.result;
                    if (!db.objectStoreNames.contains(store)) {
                        resolve([]);
                        return;
                    }
                    const tx = db.transaction(store, "readonly");
                    const os = tx.objectStore(store);
                    const all = os.getAll();
                    all.onsuccess = () => resolve(all.result);
                    all.onerror = () => reject(all.error);
                };
                req.onerror = () => reject(req.error);
            });
        }
        """,
        {"dbName": db_name, "store": store},
    )


def clear_pkm_cache(page):
    """Wipe the pkm_cache IndexedDB so tests start from a clean state."""
    page.evaluate(
        """
        async () => {
            return new Promise((resolve) => {
                const req = indexedDB.deleteDatabase("pkm_cache");
                req.onsuccess = () => resolve(true);
                req.onerror = () => resolve(false);
                req.onblocked = () => resolve(false);
                req.onupgradeneeded = () => resolve(true);
            });
        }
        """
    )


def login(page, username="e2e_admin", password="E2EPass123!"):
    page.goto(f"{E2E_BASE_URL}/auth/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def goto_note_create(page):
    page.goto(f"{E2E_BASE_URL}/modern/knowledge/notes/new/")
    page.wait_for_load_state("networkidle")


# --- Tests ------------------------------------------------------------------


@pytest.mark.e2e
def test_dexie_vendor_file_loaded(logged_in_page):
    """VAL-CACHE-005: Dexie.js is served from /static/vendor/js/dexie.min.js.

    The base_pkm.html template loads it; verify it's present on the
    note create page (a PKM page) and Dexie global is available.
    """
    goto_note_create(logged_in_page)
    # The global Dexie constructor should be defined.
    has_dexie = logged_in_page.evaluate("typeof window.Dexie === 'function'")
    assert has_dexie, "Dexie global not available on note create page"
    # And PKMCache should be exposed.
    has_cache = logged_in_page.evaluate("typeof window.PKMCache === 'object'")
    assert has_cache, "PKMCache global not available"


@pytest.mark.e2e
def test_pkm_cache_js_loaded(logged_in_page):
    """PKMCache helper object is exposed on window."""
    goto_note_create(logged_in_page)
    has_save = logged_in_page.evaluate(
        "typeof (window.PKMCache && window.PKMCache.saveDraft) === 'function'"
    )
    assert has_save, "PKMCache.saveDraft not available"
    has_autosave = logged_in_page.evaluate(
        "typeof (window.PKMDraftAutosave && window.PKMDraftAutosave.saveNow) === 'function'"
    )
    assert has_autosave, "PKMDraftAutosave.saveNow not available"


@pytest.mark.e2e
def test_typing_saves_draft_to_indexeddb(logged_in_page):
    """VAL-CACHE-001: Typing in the note editor saves a draft to IndexedDB."""
    login(logged_in_page)
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    # Reload after clearing so the page's Dexie handle reopens cleanly.
    goto_note_create(logged_in_page)

    # Type into the title and content fields.
    logged_in_page.fill("#id_title", "Draft Note E2E Title")
    logged_in_page.fill("#id_content", "Some body content for the draft.")

    # Drive the debounced save to completion immediately rather than
    # waiting the full 1s, then verify IndexedDB has a draft.
    logged_in_page.evaluate("window.PKMDraftAutosave.saveNow()")
    # Give the async IndexedDB write a moment to flush.
    logged_in_page.wait_for_timeout(500)

    drafts = open_indexeddb(logged_in_page)
    assert drafts, "No drafts saved to IndexedDB after typing"
    matching = [d for d in drafts
                if d.get("title") == "Draft Note E2E Title"]
    assert matching, f"Draft title not found in {drafts!r}"
    saved = matching[0]
    assert saved.get("content") == "Some body content for the draft."
    assert saved.get("updated_at"), "updated_at not set on saved draft"


@pytest.mark.e2e
def test_debounced_autosave_writes_after_one_second(logged_in_page):
    """VAL-CACHE-001: The 1s debounce window triggers an autosave automatically."""
    login(logged_in_page)
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_note_create(logged_in_page)

    # Trigger input events (not just .fill, which may not fire 'input'
    # on every keystroke — we type into the field).
    logged_in_page.locator("#id_title").click()
    logged_in_page.type("#id_title", "Debounced Title")
    logged_in_page.locator("#id_content").click()
    logged_in_page.type("#id_content", "Debounced body text")

    # Before debounce fires there should be no draft.
    pre = open_indexeddb(logged_in_page)
    # Allow a tiny window — debounce hasn't fired yet.
    assert pre == [] or all(
        d.get("title") != "Debounced Title" for d in pre
    ), f"Draft saved too early: {pre!r}"

    # Wait past the 1s debounce.
    logged_in_page.wait_for_timeout(1500)

    drafts = open_indexeddb(logged_in_page)
    assert any(d.get("title") == "Debounced Title" for d in drafts), \
        f"Debounced autosave did not write a draft: {drafts!r}"


@pytest.mark.e2e
def test_reload_recovers_draft(logged_in_page):
    """VAL-CACHE-002: After reload, the draft recovery banner is shown."""
    login(logged_in_page)
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_note_create(logged_in_page)

    logged_in_page.fill("#id_title", "Persistent Draft Title")
    logged_in_page.fill("#id_content", "Persistent draft body content.")
    logged_in_page.evaluate("window.PKMDraftAutosave.saveNow()")
    logged_in_page.wait_for_timeout(500)

    # Reset the form fields to empty (simulate the user not having typed
    # yet on a fresh page load). Then reload — the recovery banner should
    # appear because the draft differs from the (empty) form.
    goto_note_create(logged_in_page)

    banner = logged_in_page.locator("#pkm-draft-banner")
    # Banner should be visible after the page's checkForDraft() runs.
    expect(banner).to_be_visible(timeout=5000)
    banner_text = banner.inner_text()
    assert "Bản nháp chưa lưu" in banner_text

    # Click "Khôi phục nháp" and verify the form is populated.
    logged_in_page.locator("#pkm-draft-recover").click()
    expect(logged_in_page.locator("#id_title")).to_have_value(
        "Persistent Draft Title"
    )
    expect(logged_in_page.locator("#id_content")).to_have_value(
        "Persistent draft body content."
    )


@pytest.mark.e2e
def test_save_note_deletes_draft_from_indexeddb(logged_in_page):
    """VAL-CACHE-003 + VAL-CACHE-007: Successful server save clears the draft."""
    login(logged_in_page)
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_note_create(logged_in_page)

    logged_in_page.fill("#id_title", "Server-Saved Note")
    logged_in_page.fill("#id_content", "This will be saved to the server.")
    # Make sure a draft exists.
    logged_in_page.evaluate("window.PKMDraftAutosave.saveNow()")
    logged_in_page.wait_for_timeout(500)
    assert open_indexeddb(logged_in_page), "Precondition: draft should exist"

    # Submit the form to the server.
    logged_in_page.click('button[type="submit"]')
    logged_in_page.wait_for_load_state("networkidle")

    # After successful save, the draft(s) should be deleted from IndexedDB.
    # (clearDraftsOnSave runs on submit; allow a moment for IDB delete.)
    logged_in_page.wait_for_timeout(500)
    drafts = open_indexeddb(logged_in_page)
    # Either no drafts remain, or none with our title.
    leftover = [d for d in drafts if d.get("title") == "Server-Saved Note"]
    assert not leftover, f"Draft not cleared after save: {drafts!r}"


@pytest.mark.e2e
def test_note_list_shows_recover_drafts_indicator(logged_in_page):
    """The note list page shows a 'recover drafts' indicator when drafts exist."""
    login(logged_in_page)
    # Seed a draft directly via PKMCache on the create page, then navigate
    # to the list page.
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_note_create(logged_in_page)
    logged_in_page.evaluate(
        "window.PKMCache.saveDraft('Indicator Draft', 'indicator body')"
    )
    logged_in_page.wait_for_timeout(300)

    # Navigate to the notes list.
    logged_in_page.goto(f"{E2E_BASE_URL}/modern/knowledge/notes/")
    logged_in_page.wait_for_load_state("networkidle")

    indicator = logged_in_page.locator("#pkm-drafts-indicator")
    expect(indicator).to_be_visible(timeout=5000)
    # The count element should reflect at least one draft.
    count_text = logged_in_page.locator("#pkm-drafts-count").inner_text()
    assert int(count_text) >= 1


@pytest.mark.e2e
def test_dismiss_hides_draft_banner(logged_in_page):
    """Dismiss button hides the recovery banner without applying the draft."""
    login(logged_in_page)
    goto_note_create(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_note_create(logged_in_page)
    logged_in_page.fill("#id_title", "Dismissable Draft")
    logged_in_page.evaluate("window.PKMDraftAutosave.saveNow()")
    logged_in_page.wait_for_timeout(300)

    # Reload with empty form to trigger banner.
    goto_note_create(logged_in_page)
    banner = logged_in_page.locator("#pkm-draft-banner")
    expect(banner).to_be_visible(timeout=5000)

    logged_in_page.locator("#pkm-draft-dismiss").click()
    expect(banner).to_be_hidden(timeout=2000)

    # Form should still be empty (dismiss does not apply the draft).
    expect(logged_in_page.locator("#id_title")).to_have_value("")
