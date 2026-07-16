"""Tests for the PKM export functionality (VAL-EXPORT-001).

Covers:

  * The ``GET /api/v1/pkm/export/`` REST endpoint returning JSON with notes
    (title, content, tags) and wiki pages, scoped by ``(user, company)``.
  * The ``apps.pkm.services.export_service`` module (reusable exporter used
    by both the API and the management command).
  * The ``export_pkm_data`` management command (--user, --format, --output,
    --company).

Fulfils:
  - **VAL-EXPORT-001**: Given user has notes and wiki pages, when export API
    is called, then JSON response contains all notes (title, content, tags)
    and wiki pages.
"""

from __future__ import annotations

import io
import json

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import KnowledgeNote, Tag, WikiPage
from apps.pkm.services.export_service import (
    export_user_pkm_data,
    render_export_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="EXP_CO", name="Export Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="EXP_CO2", name="Export Co 2")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="exp_user", password="Test1234!", email="exp@t.co")


@pytest.fixture
def client(user):
    """Authenticated test client for ``user``."""
    c = Client()
    c.force_login(user)
    return c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(user, company, title, content="body", *, tags=None, role_context=""):
    note = KnowledgeNote.objects.create(
        user=user, company=company, title=title, content=content, role_context=role_context
    )
    if tags:
        for tname in tags:
            tag, _ = Tag.objects.get_or_create(user=user, company=company, name=tname)
            note.tags.add(tag)
    return note


def _make_wiki(user, company, title, content="wiki body", page_type="summary"):
    return WikiPage.objects.create(
        user=user,
        company=company,
        title=title,
        content=content,
        page_type=page_type,
    )


# ===========================================================================
# Export service (reusable, tested in isolation)
# ===========================================================================


@pytest.mark.django_db
def test_export_service_returns_notes_with_title_content_tags(user, company):
    """VAL-EXPORT-001: export payload contains notes with title/content/tags."""
    _make_note(user, company, "Note A", "body A", tags=["vat", "invoice"])
    _make_note(user, company, "Note B", "body B", tags=["hr"])

    payload = export_user_pkm_data(user=user, company=company)

    assert payload["notes"]
    titles = {n["title"] for n in payload["notes"]}
    assert titles == {"Note A", "Note B"}

    note_a = next(n for n in payload["notes"] if n["title"] == "Note A")
    assert note_a["content"] == "body A"
    assert set(note_a["tags"]) == {"vat", "invoice"}


@pytest.mark.django_db
def test_export_service_returns_wiki_pages(user, company):
    """VAL-EXPORT-001: export payload contains wiki pages."""
    _make_wiki(user, company, "Summary: Doc 1", "summary content", page_type="summary")
    _make_wiki(user, company, "Concept: VAT", "concept content", page_type="concept")

    payload = export_user_pkm_data(user=user, company=company)

    assert len(payload["wiki_pages"]) == 2
    titles = {w["title"] for w in payload["wiki_pages"]}
    assert "Summary: Doc 1" in titles
    assert "Concept: VAT" in titles

    summary = next(w for w in payload["wiki_pages"] if "Summary" in w["title"])
    assert summary["content"] == "summary content"
    assert summary["page_type"] == "summary"


@pytest.mark.django_db
def test_export_service_payload_shape(user, company):
    """The payload has the expected top-level shape."""
    payload = export_user_pkm_data(user=user, company=company)

    assert set(payload.keys()) >= {"user", "company", "exported_at", "notes", "wiki_pages"}
    assert payload["user"]["username"] == user.username
    assert payload["company"]["code"] == company.code
    assert payload["exported_at"]  # non-empty ISO timestamp


@pytest.mark.django_db
def test_export_service_scoped_per_user(user, company):
    """Notes owned by a different user are excluded (user isolation)."""
    other = User.objects.create_user(username="other", password="Test1234!", email="other@t.co")
    _make_note(user, company, "My Note", "mine")
    _make_note(other, company, "Their Note", "theirs")

    payload = export_user_pkm_data(user=user, company=company)

    titles = {n["title"] for n in payload["notes"]}
    assert titles == {"My Note"}
    assert "Their Note" not in titles


@pytest.mark.django_db
def test_export_service_scoped_per_company(user, company, other_company):
    """Notes in a different company are excluded (multi-tenant isolation)."""
    _make_note(user, company, "Co1 Note", "in co1")
    _make_note(user, other_company, "Co2 Note", "in co2")

    payload = export_user_pkm_data(user=user, company=company)

    titles = {n["title"] for n in payload["notes"]}
    assert titles == {"Co1 Note"}
    assert "Co2 Note" not in titles


@pytest.mark.django_db
def test_export_service_include_flags(user, company):
    """include_notes / include_wiki flags control payload sections."""
    _make_note(user, company, "Note X", "x")
    _make_wiki(user, company, "Wiki X", "x")

    notes_only = export_user_pkm_data(
        user=user, company=company, include_notes=True, include_wiki=False
    )
    assert "notes" in notes_only
    assert "wiki_pages" not in notes_only

    wiki_only = export_user_pkm_data(
        user=user, company=company, include_notes=False, include_wiki=True
    )
    assert "notes" not in wiki_only
    assert "wiki_pages" in wiki_only


# ===========================================================================
# VAL-EXPORT-001: GET /api/v1/pkm/export/
# ===========================================================================


@pytest.mark.django_db
def test_export_api_returns_json_with_notes_and_wiki(client, user, company):
    """VAL-EXPORT-001: GET /api/v1/pkm/export/ returns notes + wiki as JSON."""
    _make_note(user, company, "API Note", "api body", tags=["tag1"])
    _make_wiki(user, company, "API Wiki", "api wiki content", page_type="concept")

    response = client.get("/api/v1/pkm/export/")

    assert response.status_code == 200, response.content
    data = response.json()

    assert data["user"]["username"] == user.username
    assert data["company"]["code"] == company.code
    assert "exported_at" in data

    # Notes section contains the note with title, content, tags.
    assert len(data["notes"]) == 1
    note = data["notes"][0]
    assert note["title"] == "API Note"
    assert note["content"] == "api body"
    assert "tag1" in note["tags"]

    # Wiki section contains the wiki page.
    assert len(data["wiki_pages"]) == 1
    wiki = data["wiki_pages"][0]
    assert wiki["title"] == "API Wiki"
    assert wiki["content"] == "api wiki content"
    assert wiki["page_type"] == "concept"


@pytest.mark.django_db
def test_export_api_empty_when_no_data(client, user, company):
    """Export returns valid JSON with empty lists when user has no data."""
    response = client.get("/api/v1/pkm/export/")
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == []
    assert data["wiki_pages"] == []


@pytest.mark.django_db
def test_export_api_requires_authentication():
    """Unauthenticated requests are rejected (401)."""
    c = Client()
    response = c.get("/api/v1/pkm/export/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_export_api_user_isolation(client, user, company):
    """Notes owned by another user (same company) are not exported."""
    _make_note(user, company, "My Export Note", "mine")
    other = User.objects.create_user(username="other_exp", password="Test1234!", email="o@t.co")
    _make_note(other, company, "Other Note", "not mine")

    response = client.get("/api/v1/pkm/export/")
    data = response.json()
    titles = {n["title"] for n in data["notes"]}
    assert titles == {"My Export Note"}
    assert "Other Note" not in titles


@pytest.mark.django_db
def test_export_api_query_params_include_notes_false(client, user, company):
    """?include_notes=False omits notes from the payload."""
    _make_note(user, company, "X", "y")
    _make_wiki(user, company, "W", "z")

    response = client.get("/api/v1/pkm/export/?include_notes=False")
    assert response.status_code == 200
    data = response.json()
    # Notes section is present but empty.
    assert data["notes"] == []
    assert len(data["wiki_pages"]) == 1


@pytest.mark.django_db
def test_export_api_query_params_include_wiki_false(client, user, company):
    """?include_wiki=False omits wiki from the payload."""
    _make_note(user, company, "X", "y")
    _make_wiki(user, company, "W", "z")

    response = client.get("/api/v1/pkm/export/?include_wiki=False")
    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 1
    assert data["wiki_pages"] == []


@pytest.mark.django_db
def test_export_api_notes_include_role_context_and_pinned(client, user, company):
    """Exported notes include role_context and is_pinned fields."""
    _make_note(user, company, "Pinned", "x", role_context="accountant")
    note = KnowledgeNote.objects.get(title="Pinned")
    note.is_pinned = True
    note.save(update_fields=["is_pinned"])

    response = client.get("/api/v1/pkm/export/")
    data = response.json()
    assert data["notes"][0]["role_context"] == "accountant"
    assert data["notes"][0]["is_pinned"] is True


# ===========================================================================
# Management command: export_pkm_data
# ===========================================================================


@pytest.mark.django_db
def test_export_command_json_to_stdout(user, company):
    """export_pkm_data --user X --format json writes JSON to stdout."""
    _make_note(user, company, "Cmd Note", "cmd body", tags=["c1"])
    _make_wiki(user, company, "Cmd Wiki", "cmd wiki")

    out = io.StringIO()
    call_command("export_pkm_data", "--user", str(user.id), "--format", "json", stdout=out)
    raw = out.getvalue()
    data = json.loads(raw)

    assert data["user"]["username"] == user.username
    titles = {n["title"] for n in data["notes"]}
    assert "Cmd Note" in titles
    wiki_titles = {w["title"] for w in data["wiki_pages"]}
    assert "Cmd Wiki" in wiki_titles


@pytest.mark.django_db
def test_export_command_md_to_stdout(user, company):
    """export_pkm_data --format md writes Markdown to stdout."""
    _make_note(user, company, "MD Note", "md body")
    _make_wiki(user, company, "MD Wiki", "md wiki")

    out = io.StringIO()
    call_command("export_pkm_data", "--user", str(user.id), "--format", "md", stdout=out)
    raw = out.getvalue()

    assert "# PKM Export" in raw
    assert "MD Note" in raw
    assert "MD Wiki" in raw


@pytest.mark.django_db
def test_export_command_writes_to_file(tmp_path, user, company):
    """export_pkm_data --output writes to a file on disk."""
    _make_note(user, company, "File Note", "in file")

    out_file = tmp_path / "export.json"
    out = io.StringIO()
    call_command(
        "export_pkm_data",
        "--user",
        str(user.id),
        "--format",
        "json",
        "--output",
        str(out_file),
        stdout=out,
    )

    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    titles = {n["title"] for n in data["notes"]}
    assert "File Note" in titles
    assert "exported" in out.getvalue().lower() or str(out_file) in out.getvalue()


@pytest.mark.django_db
def test_export_command_company_scope(user, company, other_company):
    """--company CODE scopes the export to that company's data."""
    _make_note(user, company, "Note co1", "in co1")
    _make_note(user, other_company, "Note co2", "in co2")

    out = io.StringIO()
    call_command(
        "export_pkm_data",
        "--user",
        str(user.id),
        "--company",
        other_company.code,
        "--format",
        "json",
        stdout=out,
    )
    data = json.loads(out.getvalue())
    titles = {n["title"] for n in data["notes"]}
    assert titles == {"Note co2"}
    assert data["company"]["code"] == other_company.code


@pytest.mark.django_db
def test_export_command_no_notes_flag(user, company):
    """--no-notes excludes notes from the export."""
    _make_note(user, company, "X", "y")
    _make_wiki(user, company, "W", "z")

    out = io.StringIO()
    call_command(
        "export_pkm_data",
        "--user",
        str(user.id),
        "--no-notes",
        "--format",
        "json",
        stdout=out,
    )
    data = json.loads(out.getvalue())
    # Notes section is omitted entirely when include_notes=False.
    assert data.get("notes", []) == []
    assert len(data["wiki_pages"]) == 1


@pytest.mark.django_db
def test_export_command_invalid_user_raises(db):
    """Invalid --user raises a helpful error."""
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        call_command("export_pkm_data", "--user", "999999")
    assert "999999" in str(exc_info.value) or "does not exist" in str(exc_info.value).lower()


@pytest.mark.django_db
def test_export_command_invalid_company_raises(user, company):
    """Invalid --company CODE raises a helpful error."""
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        call_command(
            "export_pkm_data",
            "--user",
            str(user.id),
            "--company",
            "NOPE",
        )
    assert "NOPE" in str(exc_info.value) or "does not exist" in str(exc_info.value).lower()


# ===========================================================================
# Markdown rendering
# ===========================================================================


@pytest.mark.django_db
def test_render_export_markdown_contains_all_sections(user, company):
    """The Markdown renderer includes notes and wiki sections."""
    _make_note(user, company, "MD Note", "md note body", tags=["t1"])
    _make_wiki(user, company, "MD Wiki", "md wiki body", page_type="concept")

    payload = export_user_pkm_data(user=user, company=company)
    md = render_export_markdown(payload)

    assert "# PKM Export" in md
    assert "## Notes" in md
    assert "## Wiki Pages" in md
    assert "MD Note" in md
    assert "MD Wiki" in md
    assert "t1" in md
