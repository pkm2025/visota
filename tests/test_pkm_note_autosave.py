"""Integration tests for PKM note draft autosave UI markup.

These tests verify the server-rendered HTML for the note form and the
note list contains the hooks the autosave JavaScript relies on (form
fields, recovery banner, autosave status, list-page indicator, and
script references). The full IndexedDB flow is covered by E2E tests
in tests/e2e/test_17_pkm_note_autosave.py.

Covers (markup-level subset of):
    VAL-CACHE-001 - note form has autosave hooks + status element
    VAL-CACHE-002 - note form has the draft recovery banner
    VAL-CACHE-003 - note form has a submit hook (form#note-form)
    VAL-CACHE-005 - Dexie.js vendor script is referenced
"""

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def company():
    return Company.objects.create(code="PKM_AUTO", name="Autosave Co")


@pytest.fixture
def admin_user(company):
    return User.objects.create_superuser(
        username="autosave_admin", password="Test1234", email="auto@pkm.test"
    )


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = None  # superuser bypass
    session.save()
    return c


# --- Note create form: autosave markup -------------------------------------


def test_note_create_form_has_title_and_content_ids(admin_client):
    """The autosave JS targets #id_title and #id_content — both must render."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'id="id_title"' in html
    assert 'id="id_content"' in html


def test_note_create_form_has_recovery_banner(admin_client):
    """VAL-CACHE-002: form page renders the draft recovery banner container."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    html = response.content.decode("utf-8")
    assert 'id="pkm-draft-banner"' in html
    assert 'id="pkm-draft-recover"' in html
    assert 'id="pkm-draft-dismiss"' in html


def test_note_create_form_has_autosave_status(admin_client):
    """The autosave status indicator element is present on the form page."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    html = response.content.decode("utf-8")
    assert 'id="pkm-autosave-status"' in html


def test_note_create_form_has_note_form_id(admin_client):
    """The form uses id='note-form' so the submit hook can attach."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    html = response.content.decode("utf-8")
    assert 'id="note-form"' in html


def test_note_create_form_includes_pkm_cache_script(admin_client):
    """VAL-CACHE-005: Dexie vendor file and pkm-cache.js are referenced."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    html = response.content.decode("utf-8")
    assert "vendor/js/dexie.min.js" in html
    assert "modern/js/pkm-cache.js" in html


def test_note_create_form_includes_autosave_inline_script(admin_client):
    """The inline autosave script exposing PKMDraftAutosave is on the page."""
    response = admin_client.get("/modern/knowledge/notes/new/")
    html = response.content.decode("utf-8")
    assert "PKMDraftAutosave" in html
    assert "saveNow" in html
    assert "DEBOUNCE_MS" in html


# --- Note edit form: same autosave markup ----------------------------------


def test_note_edit_form_has_recovery_banner(admin_client, admin_user, company):
    """Edit form also renders the autosave UI (recovery banner + status)."""
    from apps.pkm.models import KnowledgeNote

    note = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Edit Me", content="body"
    )
    response = admin_client.get(f"/modern/knowledge/notes/{note.pk}/edit/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'id="pkm-draft-banner"' in html
    assert 'id="pkm-autosave-status"' in html
    assert 'id="note-form"' in html


# --- Note list: recover-drafts indicator -----------------------------------


def test_note_list_has_recover_drafts_indicator(admin_client):
    """The notes list page renders the draft recovery indicator container."""
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'id="pkm-drafts-indicator"' in html
    assert 'id="pkm-drafts-count"' in html


def test_note_list_includes_pkm_cache_script(admin_client):
    """The notes list also loads pkm-cache.js (so it can count drafts)."""
    response = admin_client.get("/modern/knowledge/notes/")
    html = response.content.decode("utf-8")
    assert "modern/js/pkm-cache.js" in html


def test_note_list_indicator_links_to_create_page(admin_client):
    """The indicator links to the note create form where drafts can be recovered."""
    response = admin_client.get("/modern/knowledge/notes/")
    html = response.content.decode("utf-8")
    assert 'href="/modern/knowledge/notes/new/"' in html
