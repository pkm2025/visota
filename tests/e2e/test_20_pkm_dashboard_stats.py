"""E2E: PKM dashboard shows correct stats for a seeded user.

Covers feature pkm-dashboard-stats:
  VAL-CROSS-007 - Dashboard shows stats (total notes, total documents, total Q&A)
  VAL-CROSS-008 - Role-based context filtering on the dashboard

These tests drive the running dev server on port 8903 with a real
Chromium browser via Playwright. Seed data is created via a standalone
Django shell script (subprocess) so it persists in the running server's
database.
"""

import subprocess
from pathlib import Path

import pytest
from playwright.sync_api import expect

E2E_BASE_URL = "http://127.0.0.1:8903"


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def seed_dashboard_data():
    """Seed e2e_admin with a known set of PKM data for dashboard assertions.

    Creates:
      - 2 notes (1 pinned, 1 with role_context matching a role)
      - 1 document (processed)
      - 3 Q&A history entries
      - A role assigned to e2e_admin so role-based suggestions are testable

    Idempotent: clears existing e2e_admin PKM data first so the dashboard
    shows deterministic counts.
    """
    repo_root = Path(__file__).resolve().parents[2]
    python_exe = str(repo_root / ".venv" / "Scripts" / "python.exe")

    script_path = repo_root / "_tmp_seed_dashboard.py"
    script_path.write_text(
        'import os, django\n'
        'os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"\n'
        'django.setup()\n'
        'from django.contrib.auth import get_user_model\n'
        'from django.core.files.uploadedfile import SimpleUploadedFile\n'
        'from apps.core.models import Company\n'
        'from apps.identity.models import Role, UserCompanyRole\n'
        'from apps.pkm.models import (\n'
        '    KnowledgeNote, PKMDocument, QAHistory, UserInteractionLog,\n'
        ')\n'
        'User = get_user_model()\n'
        'co = Company.objects.first()\n'
        'u = User.objects.filter(username="e2e_admin").first()\n'
        'if u and co:\n'
        '    # Wipe existing e2e_admin PKM data for deterministic counts\n'
        '    KnowledgeNote.objects.filter(user=u, company=co).delete()\n'
        '    PKMDocument.objects.filter(user=u, company=co).delete()\n'
        '    QAHistory.objects.filter(user=u, company=co).delete()\n'
        '    # Create a role for e2e_admin so role suggestions work\n'
        '    UserCompanyRole.objects.filter(user=u, company=co).delete()\n'
        '    role, _ = Role.objects.get_or_create(\n'
        '        company=co, code="e2e_dash_role",\n'
        '        defaults={"name": "E2E Dash Role"},\n'
        '    )\n'
        '    UserCompanyRole.objects.update_or_create(\n'
        '        user=u, company=co, role=role, defaults={"is_default": True}\n'
        '    )\n'
        '    # 2 notes (1 pinned, 1 with matching role_context)\n'
        '    KnowledgeNote.objects.create(\n'
        '        user=u, company=co, title="E2E Pinned Note",\n'
        '        content="pinned", is_pinned=True,\n'
        '    )\n'
        '    KnowledgeNote.objects.create(\n'
        '        user=u, company=co, title="E2E Role Note",\n'
        '        content="role-based", role_context="e2e_dash_role",\n'
        '    )\n'
        '    # 1 document (processed)\n'
        '    PKMDocument.objects.create(\n'
        '        user=u, company=co, title="E2E Doc",\n'
        '        file=SimpleUploadedFile("e2e_dash.txt", b"hi",\n'
        '                                content_type="text/plain"),\n'
        '        file_type="txt", file_size=2,\n'
        '        status="processed",\n'
        '    )\n'
        '    # 3 Q&A history entries\n'
        '    for i in range(3):\n'
        '        QAHistory.objects.create(\n'
        '            user=u, company=co,\n'
        '            question=f"E2E Q{i}?", answer=f"E2E A{i}.",\n'
        '        )\n'
        '    # 2 interaction logs (recent activity)\n'
        '    for i in range(2):\n'
        '        UserInteractionLog.objects.create(\n'
        '            user=u, company=co, interaction_type="page_view",\n'
        '            module="pkm",\n'
        '        )\n'
        'print("E2E dashboard seed complete")\n',
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
            logging.warning("seed_dashboard_data failed: %s", result.stderr[:300])
    finally:
        script_path.unlink(missing_ok=True)
    yield


# --- Helpers ----------------------------------------------------------------


def login(page, username="e2e_admin", password="E2EPass123!"):
    page.goto(f"{E2E_BASE_URL}/auth/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
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


def goto_dashboard(page):
    page.goto(f"{E2E_BASE_URL}/modern/knowledge/")
    page.wait_for_load_state("domcontentloaded")
    dismiss_debug_toolbar(page)


# --- Tests: VAL-CROSS-007 Dashboard shows stats ------------------------------


def test_dashboard_shows_note_count(page):
    """Dashboard stat card shows the total notes count (2)."""
    login(page)
    goto_dashboard(page)
    stat = page.locator("#stat-notes")
    expect(stat).to_have_text("2")


def test_dashboard_shows_doc_count(page):
    """Dashboard stat card shows the total documents count (1)."""
    login(page)
    goto_dashboard(page)
    stat = page.locator("#stat-docs")
    expect(stat).to_have_text("1")


def test_dashboard_shows_qa_count(page):
    """Dashboard stat card shows the total Q&A interactions count (3)."""
    login(page)
    goto_dashboard(page)
    stat = page.locator("#stat-qa")
    expect(stat).to_have_text("3")


def test_dashboard_shows_doc_status_breakdown(page):
    """Dashboard shows document status breakdown text."""
    login(page)
    goto_dashboard(page)
    status = page.locator("#stat-doc-status")
    expect(status).to_contain_text("1")  # 1 processed doc


# --- Tests: dashboard activity feed and pinned notes -------------------------


def test_dashboard_shows_recent_activity(page):
    """Dashboard shows the recent activity feed panel."""
    login(page)
    goto_dashboard(page)
    activity_list = page.locator("#recent-activity-list")
    expect(activity_list).to_be_visible()
    # Should have at least 2 activity items (from seeded interaction logs)
    items = activity_list.locator("li")
    expect(items).to_have_count(2)


def test_dashboard_shows_pinned_notes(page):
    """Dashboard shows pinned notes quick access."""
    login(page)
    goto_dashboard(page)
    pinned_list = page.locator("#pinned-notes-list")
    expect(pinned_list).to_be_visible()
    expect(pinned_list).to_contain_text("E2E Pinned Note")


# --- Tests: VAL-CROSS-008 Role-based context filtering ----------------------


def test_dashboard_shows_role_suggestions(page):
    """Dashboard shows role-based suggestion panel for the user's role."""
    login(page)
    goto_dashboard(page)
    suggestions = page.locator("#role-suggestions-list")
    expect(suggestions).to_be_visible()
    expect(suggestions).to_contain_text("E2E Role Note")


# --- Tests: stats API endpoint ---------------------------------------------


def test_stats_api_returns_counts(page, request):
    """GET /api/v1/pkm/stats/ returns correct counts for the seeded user.

    Uses the authenticated session established by the browser login (the
    django-ninja API accepts session auth).
    """
    login(page)
    # Use the browser context's cookies to make a fetch from within the page
    data = page.evaluate(
        """async () => {
            const resp = await fetch('/api/v1/pkm/stats/', {credentials: 'include'});
            return await resp.json();
        }"""
    )
    assert data["note_count"] == 2
    assert data["doc_count"] == 1
    assert data["qa_count"] == 3
    assert data["pinned_note_count"] == 1
    assert data["doc_status_counts"]["processed"] == 1
    assert "e2e_dash_role" in data["user_role_codes"]
    assert data["role_suggestions_count"] == 1
