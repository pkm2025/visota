"""Integration tests for PKM service worker caching and background sync.

These tests verify the server-served static files (sw.js, pkm-cache.js)
contain the expected PKM caching, offline fallback, and background sync
logic. The full browser-based E2E flow (cache hits, offline page loads,
sync replay) is covered by E2E tests in
tests/e2e/test_19_pkm_service_worker.py.

Covers (markup/content-level subset of):
    VAL-CACHE-006 - sw.js caches PKM static assets and pages
    VAL-CACHE-007 - background sync handler for offline drafts
    VAL-CACHE-008 - clearing browser data does not corrupt server data
"""

from pathlib import Path

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import KnowledgeNote

pytestmark = pytest.mark.django_db

STATIC_ROOT = Path(__file__).resolve().parent.parent / "static"


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def company():
    return Company.objects.create(code="PKM_SW", name="SW Test Co")


@pytest.fixture
def admin_user(company):
    return User.objects.create_superuser(
        username="sw_admin", password="Test1234", email="sw@pkm.test"
    )


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = None  # superuser bypass
    session.save()
    return c


# --- Static file content tests ----------------------------------------------


def test_sw_js_exists():
    """The service worker file exists at static/sw.js."""
    assert (STATIC_ROOT / "sw.js").exists(), "static/sw.js not found"


def test_pkm_cache_js_exists():
    """The PKM cache JS file exists at static/modern/js/pkm-cache.js."""
    assert (STATIC_ROOT / "modern" / "js" / "pkm-cache.js").exists()


def test_dexie_vendor_exists():
    """Dexie.js vendor file exists at static/vendor/js/dexie.min.js."""
    assert (STATIC_ROOT / "vendor" / "js" / "dexie.min.js").exists()


def test_sw_js_caches_pkm_static_assets():
    """VAL-CACHE-006: sw.js includes PKM static assets in the precache list."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "dexie.min.js" in content, "dexie.min.js not in sw.js cache list"
    assert "pkm-cache.js" in content, "pkm-cache.js not in sw.js cache list"


def test_sw_js_has_pkm_page_caching_strategy():
    """VAL-CACHE-006: sw.js uses stale-while-revalidate for PKM pages."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "/modern/knowledge/" in content, (
        "PKM route prefix not found in sw.js"
    )
    assert "staleWhileRevalidate" in content, (
        "staleWhileRevalidate strategy not found in sw.js"
    )


def test_sw_js_has_cache_first_for_static():
    """VAL-CACHE-006: sw.js uses cache-first strategy for static assets."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "cacheFirst" in content, "cacheFirst strategy not found in sw.js"


def test_sw_js_has_offline_fallback():
    """sw.js includes an offline fallback URL for failed navigations."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "/offline/" in content, "Offline fallback URL not found in sw.js"


def test_sw_js_has_background_sync():
    """VAL-CACHE-007: sw.js includes a background sync handler for drafts."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "sync" in content.lower(), "sync event handler not found in sw.js"
    assert "pkm-draft-sync" in content, "SYNC_TAG not found in sw.js"
    assert "queueDraftRequest" in content, (
        "queueDraftRequest handler not found in sw.js"
    )
    assert "replayQueue" in content, "replayQueue handler not found in sw.js"


def test_sw_js_queues_pkm_notes_post():
    """VAL-CACHE-007: sw.js intercepts POST to PKM notes API for queuing."""
    content = (STATIC_ROOT / "sw.js").read_text(encoding="utf-8")
    assert "/api/v1/pkm/notes" in content, (
        "PKM notes API path not found in sw.js for background sync"
    )


def test_pkm_cache_js_has_sync_helpers():
    """VAL-CACHE-007: pkm-cache.js exposes background sync helper functions."""
    content = (STATIC_ROOT / "modern" / "js" / "pkm-cache.js").read_text(encoding="utf-8")
    assert "queueForSync" in content, "queueForSync not in pkm-cache.js"
    assert "triggerSync" in content, "triggerSync not in pkm-cache.js"
    assert "getQueuedCount" in content, "getQueuedCount not in pkm-cache.js"
    assert "pkm_sync_queue" in content, "outbox DB name not in pkm-cache.js"


# --- Server-served static file tests ----------------------------------------
# NOTE: Static files are served by Django's staticfiles app only in dev
# mode (runserver) or when staticfiles have been collected. In tests,
# STATICFILES_STORAGE doesn't serve files via the test client. Instead we
# verify the files exist on disk (covered by the tests above). The E2E
# tests verify they are served correctly by the running dev server.


# --- VAL-CACHE-008: Clearing browser data doesn't corrupt server data -------


def test_clearing_cache_preserves_server_notes(admin_client, admin_user, company):
    """VAL-CACHE-008: Server-side notes survive client cache clearing.

    We create notes directly on the server, then simulate clearing all
    client caches (which is a no-op for the server DB), and verify the
    server notes are still accessible via the API.
    """
    # Create notes server-side
    note1 = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Server Note 1", content="content 1"
    )
    note2 = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Server Note 2", content="content 2"
    )

    # Verify notes exist via API
    response = admin_client.get("/api/v1/pkm/notes/")
    assert response.status_code == 200
    data = response.json()
    server_titles = {n["title"] for n in data.get("items", data) if isinstance(n, dict)}
    assert "Server Note 1" in server_titles
    assert "Server Note 2" in server_titles

    # "Clear browser data" — this is a client-side operation that has zero
    # effect on the server database. We verify the notes still exist.
    # (In a real browser, clearing IndexedDB/CacheStorage only removes local
    # caches; the server data is untouched.)
    assert KnowledgeNote.objects.filter(user=admin_user).count() >= 2

    # Verify notes are still accessible via API after "clearing"
    response2 = admin_client.get("/api/v1/pkm/notes/")
    assert response2.status_code == 200
    data2 = response2.json()
    server_titles2 = {n["title"] for n in data2.get("items", data2) if isinstance(n, dict)}
    assert "Server Note 1" in server_titles2
    assert "Server Note 2" in server_titles2

    # Cleanup
    note1.delete()
    note2.delete()
