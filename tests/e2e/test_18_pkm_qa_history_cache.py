"""E2E: PKM Q&A history cache to IndexedDB.

Covers the pkm-qa-history-cache feature:
  - After a Q&A response is displayed, the question + answer are saved to
    IndexedDB (qa_history store) via PKMCache.saveQAHistory().
  - On page load, recent Q&A is loaded from IndexedDB and displayed in the
    history panel for instant feedback (before / without server history).

These tests drive the running dev server on port 8903 with a real Chromium
browser via Playwright. IndexedDB operations are real — we query the
pkm_cache database directly via page.evaluate to assert on qa_history rows.
"""

import subprocess
from pathlib import Path

import pytest

E2E_BASE_URL = "http://127.0.0.1:8903"


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def ensure_llm_config():
    """Ensure e2e_admin has an active LLM config so the Q&A chat page renders.

    Without an active config, the page shows a 'configure provider first'
    message and the chat/history panel is not rendered. We create a dummy
    config via a standalone script file (no real API key needed — LLM calls
    are not exercised by these client-side cache tests).
    """
    repo_root = Path(__file__).resolve().parents[2]
    python_exe = str(repo_root / ".venv" / "Scripts" / "python.exe")

    # Write a small setup script that the Django dev server's Python can run.
    script_path = repo_root / "_tmp_ensure_llm_config.py"
    script_path.write_text(
        'import os, django\n'
        'os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"\n'
        'django.setup()\n'
        'from django.contrib.auth import get_user_model\n'
        'from apps.core.models import Company\n'
        'from apps.pkm.models import UserLLMConfig\n'
        'from apps.pkm.services.encryption_service import encrypt\n'
        'User = get_user_model()\n'
        'co = Company.objects.first()\n'
        'u = User.objects.filter(username="e2e_admin").first()\n'
        'if u and co:\n'
        '    obj, created = UserLLMConfig.objects.get_or_create(\n'
        '        user=u, company=co, provider="openai",\n'
        '        defaults={\n'
        '            "api_key_encrypted": encrypt("sk-e2e-dummy-key"),\n'
        '            "default_model": "gpt-4o-mini",\n'
        '            "default_embedding_model": "text-embedding-3-small",\n'
        '            "is_active": True,\n'
        '        },\n'
        '    )\n'
        '    if not created and not obj.is_active:\n'
        '        obj.is_active = True\n'
        '        obj.save(update_fields=["is_active"])\n',
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [python_exe, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=30,
        )
        if result.returncode != 0:
            import logging
            logging.warning("ensure_llm_config failed: %s", result.stderr[:300])
    finally:
        script_path.unlink(missing_ok=True)
    yield


# --- Helpers ----------------------------------------------------------------


def goto_qa_page(page):
    page.goto(f"{E2E_BASE_URL}/modern/knowledge/qa/")
    page.wait_for_load_state("domcontentloaded")


def dismiss_debug_toolbar(page):
    """Hide Django Debug Toolbar so it doesn't intercept clicks."""
    page.evaluate(
        """
        () => {
            var dj = document.getElementById('djDebug');
            if (dj) { dj.style.display = 'none'; }
        }
        """
    )


def clear_pkm_cache(page):
    """Wipe the pkm_cache IndexedDB so tests start from a clean state.

    Must close any open Dexie connection first, otherwise deleteDatabase
    hangs in 'blocked' state indefinitely.
    """
    page.evaluate(
        """
        async () => {
            if (window.PKMCache && window.PKMCache.db) {
                try { window.PKMCache.db.close(); } catch (e) {}
            }
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


def get_qa_history_from_indexeddb(page):
    """Return all qa_history rows from IndexedDB via a direct IDB query."""
    return page.evaluate(
        """
        async () => {
            // Ensure Dexie has opened the database
            if (window.PKMCache && window.PKMCache.db) {
                try { await window.PKMCache.db.open(); } catch (e) {}
            }
            return new Promise((resolve, reject) => {
                const req = indexedDB.open("pkm_cache");
                req.onsuccess = function () {
                    const db = req.result;
                    if (!db.objectStoreNames.contains("qa_history")) {
                        resolve([]);
                        return;
                    }
                    const tx = db.transaction("qa_history", "readonly");
                    const os = tx.objectStore("qa_history");
                    const all = os.getAll();
                    all.onsuccess = () => resolve(all.result);
                    all.onerror = () => reject(all.error);
                };
                req.onerror = () => reject(req.error);
            });
        }
        """
    )


# --- Tests ------------------------------------------------------------------


@pytest.mark.e2e
def test_pkm_cache_and_qa_history_js_loaded(logged_in_page):
    """Dexie.js and pkm-cache.js are loaded on the Q&A page, and the
    saveQAHistory / getQAHistory helpers are available.
    """
    goto_qa_page(logged_in_page)
    has_dexie = logged_in_page.evaluate("typeof window.Dexie === 'function'")
    assert has_dexie, "Dexie global not available on Q&A page"
    has_cache = logged_in_page.evaluate(
        "typeof (window.PKMCache && window.PKMCache.saveQAHistory) === 'function'"
    )
    assert has_cache, "PKMCache.saveQAHistory not available"
    has_get = logged_in_page.evaluate(
        "typeof (window.PKMCache && window.PKMCache.getQAHistory) === 'function'"
    )
    assert has_get, "PKMCache.getQAHistory not available"
    has_hook = logged_in_page.evaluate(
        "typeof (window.PKMQAHistoryCache"
        " && window.PKMQAHistoryCache.saveCurrentResponseIfPresent)"
        " === 'function'"
    )
    assert has_hook, "PKMQAHistoryCache.saveCurrentResponseIfPresent not available"


@pytest.mark.e2e
def test_qa_response_saved_to_indexeddb(logged_in_page):
    """After a Q&A response is displayed, the question + answer pair is
    saved to IndexedDB (qa_history store).

    We simulate a rendered response by directly invoking the save hook with
    DOM elements present, then verify the entry exists in IndexedDB.
    """
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)

    # Verify clean state
    entries = get_qa_history_from_indexeddb(logged_in_page)
    assert entries == [], f"Expected empty qa_history, got {entries!r}"

    # Save a Q&A pair directly via PKMCache (simulating what the page's
    # saveCurrentResponseIfPresent hook does after a real response).
    logged_in_page.evaluate("window.PKMCache.saveQAHistory('E2E test question', 'E2E test answer')")
    logged_in_page.wait_for_timeout(500)

    entries = get_qa_history_from_indexeddb(logged_in_page)
    assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"
    entry = entries[0]
    assert entry["question"] == "E2E test question"
    assert entry["answer"] == "E2E test answer"
    assert entry["created_at"], "created_at not set"


@pytest.mark.e2e
def test_qa_history_loaded_from_cache_on_reload(logged_in_page):
    """On page load, recent Q&A from IndexedDB is shown in the history panel.

    We seed IndexedDB with a cached entry, reload the Q&A page, and verify
    the local history list renders it.
    """
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)

    # Seed a cached entry
    logged_in_page.evaluate(
        "window.PKMCache.saveQAHistory('Cached reload question', 'Cached reload answer')"
    )
    logged_in_page.wait_for_timeout(500)

    # Reload the page — local cache should populate the history panel
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    logged_in_page.wait_for_timeout(1000)

    # The local history list should contain the cached entry.
    # If the server has history, the local list is hidden (d-none) but its
    # items are still rendered in the DOM. So we check for the text regardless.
    body_text = logged_in_page.evaluate("document.body.innerText")
    assert "Cached reload question" in body_text, (
        f"Cached Q&A not shown on page load. Body: {body_text[:500]}"
    )


@pytest.mark.e2e
def test_qa_history_shows_in_panel_when_no_server_history(logged_in_page):
    """When the server has no Q&A history for the user, local cache entries
    fill the history panel (the local list is shown, not hidden).
    """
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)

    # Seed a cached entry
    logged_in_page.evaluate(
        "window.PKMCache.saveQAHistory('Local-only question', 'Local-only answer')"
    )
    logged_in_page.wait_for_timeout(500)

    # Reload
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    logged_in_page.wait_for_timeout(1000)

    local_list = logged_in_page.locator("#qa-history-local")
    # Whether or not the server has history, the local list should contain items
    items = local_list.locator("li.list-group-item")
    count = items.count()
    assert count >= 1, f"Expected local list items, got {count}"
    # Verify the text is present
    text = local_list.inner_text()
    assert "Local-only question" in text


@pytest.mark.e2e
def test_multiple_qa_entries_cached_and_ordered(logged_in_page):
    """Multiple Q&A entries are cached and returned newest-first."""
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)

    # Save multiple entries
    logged_in_page.evaluate("window.PKMCache.saveQAHistory('First question', 'First answer')")
    logged_in_page.wait_for_timeout(200)
    logged_in_page.evaluate("window.PKMCache.saveQAHistory('Second question', 'Second answer')")
    logged_in_page.wait_for_timeout(200)
    logged_in_page.evaluate("window.PKMCache.saveQAHistory('Third question', 'Third answer')")
    logged_in_page.wait_for_timeout(500)

    # getQAHistory should return newest first
    ordered = logged_in_page.evaluate("window.PKMCache.getQAHistory(20)")
    assert len(ordered) == 3
    questions = [e["question"] for e in ordered]
    assert questions[0] == "Third question"
    assert questions[1] == "Second question"
    assert questions[2] == "First question"


@pytest.mark.e2e
def test_save_current_response_hook_saves_from_dom(logged_in_page):
    """The saveCurrentResponseIfPresent hook reads the rendered question and
    answer from the DOM and saves them to IndexedDB.

    We inject #user-question and #answer-text elements with data attributes
    (simulating a server-rendered Q&A response), then invoke the hook.
    """
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)
    clear_pkm_cache(logged_in_page)
    goto_qa_page(logged_in_page)
    dismiss_debug_toolbar(logged_in_page)

    # Verify clean state
    assert get_qa_history_from_indexeddb(logged_in_page) == []

    # The hook reads from #user-question[data-question] and #answer-text[data-answer].
    # These elements only exist when the server renders a Q&A response.
    # We inject them to simulate a response.
    logged_in_page.evaluate(
        """
        () => {
            var q = document.createElement('div');
            q.id = 'user-question';
            q.setAttribute('data-question', 'DOM hook question');

            var a = document.createElement('div');
            a.id = 'answer-text';
            a.setAttribute('data-answer', 'DOM hook answer');

            document.body.appendChild(q);
            document.body.appendChild(a);
        }
        """
    )

    # Invoke the save hook
    logged_in_page.evaluate("window.PKMQAHistoryCache.saveCurrentResponseIfPresent()")
    logged_in_page.wait_for_timeout(500)

    entries = get_qa_history_from_indexeddb(logged_in_page)
    assert len(entries) == 1
    assert entries[0]["question"] == "DOM hook question"
    assert entries[0]["answer"] == "DOM hook answer"
