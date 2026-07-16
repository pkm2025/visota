"""Integration tests for PKM interaction logging hooks (auto-capture).

Verifies that user interactions are logged automatically when the user
performs key actions:

  - Browsing PKM pages creates ``page_view`` interactions (VAL-CAP-001).
  - Creating a note creates a ``note_create`` interaction (VAL-CAP-002).
  - Uploading a document creates a ``document_create`` interaction (VAL-CAP-003).
  - Searching creates a ``search`` interaction with the query in metadata
    (VAL-CAP-004).
  - Logging errors do not break the main operation (VAL-CAP-009).

These tests exercise the full stack: middleware, signals, API, and UI views.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.models import KnowledgeNote, PKMDocument, UserInteractionLog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="CAP_MW", name="Capture Middleware Co", tax_code="0101234567"
    )


@pytest.fixture
def admin_user(db, company):
    """Superuser — bypasses permission checks."""
    return User.objects.create_superuser(
        username="cap_admin", password="Test1234", email="cap_admin@t.co"
    )


@pytest.fixture
def admin_client(admin_user, company):
    """Authenticated client for a superuser with session company set."""
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def perm_client(company):
    """Client for a regular user WITH pkm.access permission."""
    user = User.objects.create_user(username="cap_perm", password="Test1234", email="cap_perm@t.co")
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(company=company, code="cap_role", name="CAP Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


# ---------------------------------------------------------------------------
# Page View Logging (VAL-CAP-001)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_page_view_logged_on_pkm_dashboard(admin_client, admin_user, company):
    """Browsing the PKM dashboard creates a page_view interaction."""
    # Clear any prior logs
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.module == "pkm"
    assert log.entity_type == "page"
    assert log.metadata["url"] == "/modern/knowledge/"


@pytest.mark.django_db
def test_page_view_logged_on_notes_page(admin_client, admin_user, company):
    """Browsing the PKM notes page creates a page_view interaction."""
    response = admin_client.get("/modern/knowledge/notes/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
    )
    assert logs.filter(entity_id="/modern/knowledge/notes/").exists()


@pytest.mark.django_db
def test_page_view_logged_on_documents_page(admin_client, admin_user, company):
    """Browsing the PKM documents page creates a page_view interaction."""
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
    )
    assert logs.filter(entity_id="/modern/knowledge/documents/").exists()


@pytest.mark.django_db
def test_page_view_not_logged_for_dashboard(admin_client, admin_user, company):
    """Dashboard (/modern/) has no module mapping, so no page_view is logged."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/modern/")
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        interaction_type="page_view",
    )
    assert logs.count() == 0


@pytest.mark.django_db
def test_page_view_not_logged_for_post_requests(admin_client, admin_user, company):
    """POST requests do not create page_view interactions."""
    UserInteractionLog.objects.all().delete()
    # POST to note create (should not log page_view)
    admin_client.post("/modern/knowledge/notes/new/", data={"title": "Test", "content": "x"})
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        interaction_type="page_view",
    )
    assert logs.count() == 0


@pytest.mark.django_db
def test_page_view_with_permission_user(perm_client, company):
    """Regular user with pkm.access permission gets page_view logs."""
    UserInteractionLog.objects.all().delete()
    response = perm_client.get("/modern/knowledge/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(interaction_type="page_view", module="pkm")
    assert logs.count() == 1


# ---------------------------------------------------------------------------
# Cross-Module Page View Logging (VAL-CTX-001)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_page_view_logged_for_vouchers_with_ledger_module(admin_client, admin_user, company):
    """Visiting /modern/vouchers/ logs page_view with module='ledger'."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/modern/vouchers/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
        module="ledger",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.entity_type == "page"
    assert log.entity_id == "/modern/vouchers/"
    assert log.metadata["url"] == "/modern/vouchers/"


@pytest.mark.django_db
def test_page_view_logged_for_sales_invoices_with_sales_module(admin_client, admin_user, company):
    """Visiting /modern/sales-invoices/ logs page_view with module='sales'."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/modern/sales-invoices/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
        module="sales",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.entity_type == "page"
    assert log.entity_id == "/modern/sales-invoices/"
    assert log.metadata["url"] == "/modern/sales-invoices/"


@pytest.mark.django_db
def test_page_view_logged_for_knowledge_with_pkm_module(admin_client, admin_user, company):
    """Visiting /modern/knowledge/ logs page_view with module='pkm'."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="page_view",
        module="pkm",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.entity_id == "/modern/knowledge/"


@pytest.mark.django_db
def test_page_view_logs_correct_modules_for_multiple_urls(admin_client, admin_user, company):
    """Middleware resolves correct module for several /modern/* URLs."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/modern/vouchers/")
    admin_client.get("/modern/sales-invoices/")
    admin_client.get("/modern/knowledge/")

    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        interaction_type="page_view",
    )
    assert logs.count() == 3

    modules = set(logs.values_list("module", flat=True))
    assert modules == {"ledger", "sales", "pkm"}


@pytest.mark.django_db
def test_page_view_not_logged_for_non_modern_url(admin_client, admin_user, company):
    """Non-modern pages (e.g. /auth/) do not create page_view interactions."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/auth/login/")
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        interaction_type="page_view",
    )
    assert logs.count() == 0


# ---------------------------------------------------------------------------
# Note Create Logging (VAL-CAP-002)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_note_create_logged_via_api(admin_client, admin_user, company):
    """Creating a note via API creates a note_create interaction."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.post(
        "/api/v1/pkm/notes/",
        data={"title": "Signal Test Note", "content": "via API"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="note_create",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.module == "pkm"
    assert log.entity_type == "note"
    assert log.metadata["title"] == "Signal Test Note"


@pytest.mark.django_db
def test_note_create_logged_via_orm(admin_user, company):
    """Creating a note directly via ORM triggers the post_save signal."""
    UserInteractionLog.objects.all().delete()
    note = KnowledgeNote.objects.create(
        user=admin_user,
        company=company,
        title="ORM Note",
        content="created directly",
    )
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="note_create",
    )
    assert logs.count() == 1
    assert logs.first().entity_id == str(note.pk)


@pytest.mark.django_db
def test_note_update_does_not_log_note_create(admin_user, company):
    """Updating a note does not create a second note_create interaction."""
    note = KnowledgeNote.objects.create(
        user=admin_user, company=company, title="Original", content=""
    )
    UserInteractionLog.objects.all().delete()

    note.title = "Updated"
    note.save()

    logs = UserInteractionLog.objects.filter(interaction_type="note_create")
    assert logs.count() == 0


@pytest.mark.django_db
def test_note_create_logged_via_ui(admin_client, admin_user, company):
    """Creating a note via the UI form creates a note_create interaction."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.post(
        "/modern/knowledge/notes/new/",
        data={"title": "UI Note", "content": "via UI"},
    )
    assert response.status_code == 302  # redirect to detail
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="note_create",
    )
    assert logs.count() == 1


# ---------------------------------------------------------------------------
# Document Create Logging (VAL-CAP-003)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_create_logged_via_api(admin_client, admin_user, company):
    """Uploading a document via API creates a document_create interaction."""
    UserInteractionLog.objects.all().delete()
    from unittest.mock import patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("test.txt", b"hello world", content_type="text/plain")
    # Mock the RAG pipeline to avoid needing an LLM config for processing
    with patch("apps.pkm.api.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/api/v1/pkm/documents/",
            data={"file": upload, "title": "Test Doc"},
        )
    assert response.status_code == 201, response.content
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="document_create",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.module == "pkm"
    assert log.entity_type == "document"
    assert log.metadata["file_type"] == "txt"


@pytest.mark.django_db
def test_document_create_logged_via_orm(admin_user, company):
    """Creating a document directly via ORM triggers the post_save signal."""
    UserInteractionLog.objects.all().delete()
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("orm.txt", b"orm content", content_type="text/plain")
    doc = PKMDocument.objects.create(
        user=admin_user,
        company=company,
        title="ORM Doc",
        file=upload,
        file_type="txt",
        file_size=11,
    )
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="document_create",
    )
    assert logs.count() == 1
    assert logs.first().entity_id == str(doc.pk)


@pytest.mark.django_db
def test_document_update_does_not_log_create(admin_user, company):
    """Updating a document (status change) does not create a new interaction."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("upd.txt", b"x", content_type="text/plain")
    doc = PKMDocument.objects.create(
        user=admin_user,
        company=company,
        title="Doc",
        file=upload,
        file_type="txt",
        file_size=1,
    )
    UserInteractionLog.objects.all().delete()

    doc.status = PKMDocument.Status.PROCESSED
    doc.save()

    logs = UserInteractionLog.objects.filter(interaction_type="document_create")
    assert logs.count() == 0


# ---------------------------------------------------------------------------
# Search Logging (VAL-CAP-004)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_logged_via_api_list_endpoint(admin_client, admin_user, company):
    """Searching via GET /api/v1/pkm/notes/?search= creates a search interaction."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/api/v1/pkm/notes/?search=accounting")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="search",
    )
    assert logs.count() == 1
    log = logs.first()
    assert log.metadata["query"] == "accounting"


@pytest.mark.django_db
def test_search_logged_via_notes_search_endpoint(admin_client, admin_user, company):
    """Searching via POST /api/v1/pkm/notes/search/ creates a search interaction."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.post(
        "/api/v1/pkm/notes/search/",
        data={"query": "VAT guide"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="search",
    )
    assert logs.count() == 1
    assert logs.first().metadata["query"] == "VAT guide"


@pytest.mark.django_db
def test_search_logged_via_ui(admin_client, admin_user, company):
    """Searching via the UI (/modern/knowledge/search/?q=) creates a search interaction."""
    UserInteractionLog.objects.all().delete()
    response = admin_client.get("/modern/knowledge/search/?q=budget")
    assert response.status_code == 200
    logs = UserInteractionLog.objects.filter(
        user=admin_user,
        company=company,
        interaction_type="search",
    )
    assert logs.count() == 1
    assert logs.first().metadata["query"] == "budget"


@pytest.mark.django_db
def test_list_notes_without_search_does_not_log(admin_client, admin_user, company):
    """Listing notes without a search param does NOT create a search interaction."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/api/v1/pkm/notes/")
    logs = UserInteractionLog.objects.filter(interaction_type="search")
    assert logs.count() == 0


@pytest.mark.django_db
def test_search_page_without_query_does_not_log(admin_client, admin_user, company):
    """Visiting search page without ?q= does not create a search interaction."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/modern/knowledge/search/")
    logs = UserInteractionLog.objects.filter(interaction_type="search")
    assert logs.count() == 0


# ---------------------------------------------------------------------------
# Non-Blocking: Logging errors do not break main operations (VAL-CAP-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logging_failure_does_not_break_note_creation(admin_user, company):
    """If log_interaction raises, note creation still succeeds."""
    from unittest.mock import patch

    with patch(
        "apps.pkm.signals.log_interaction",
        side_effect=Exception("DB is down"),
    ):
        note = KnowledgeNote.objects.create(
            user=admin_user, company=company, title="Survives", content=""
        )
    # Note was created despite logging failure
    assert note.pk is not None
    assert KnowledgeNote.objects.filter(pk=note.pk).exists()
    # No interaction log was created (logging failed)
    assert not UserInteractionLog.objects.filter(interaction_type="note_create").exists()


@pytest.mark.django_db
def test_middleware_logging_failure_does_not_break_page(admin_client, admin_user, company):
    """If middleware log_interaction raises, page still loads."""
    from unittest.mock import patch

    UserInteractionLog.objects.all().delete()
    with patch(
        "apps.pkm.middleware.log_interaction",
        side_effect=Exception("Logging broken"),
    ):
        response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_search_logging_failure_does_not_break_search(admin_client, admin_user, company):
    """If search logging raises, search results still return."""
    from unittest.mock import patch

    with patch(
        "apps.pkm.api.log_interaction",
        side_effect=Exception("Search logging broken"),
    ):
        response = admin_client.get("/api/v1/pkm/notes/?search=test")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Per-user and multi-tenant isolation of interaction logs
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_page_view_log_is_per_user(admin_client, admin_user, company):
    """Page view log is attributed to the correct user."""
    other_user = User.objects.create_user(
        username="cap_other", password="Test1234", email="cap_other@t.co"
    )
    UserInteractionLog.objects.all().delete()
    admin_client.get("/modern/knowledge/")

    # Other user has no logs
    assert UserInteractionLog.objects.filter(user=other_user).count() == 0
    # Admin user has 1 page_view log
    assert (
        UserInteractionLog.objects.filter(user=admin_user, interaction_type="page_view").count()
        == 1
    )


# ---------------------------------------------------------------------------
# Metadata structure validation (VAL-CAP-006)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_page_view_log_has_module_and_entity_info(admin_client, admin_user, company):
    """Page view log records module and entity info."""
    UserInteractionLog.objects.all().delete()
    admin_client.get("/modern/knowledge/")
    log = UserInteractionLog.objects.filter(interaction_type="page_view").first()
    assert log is not None
    assert log.module == "pkm"
    assert log.entity_type == "page"
    assert log.entity_id == "/modern/knowledge/"
    assert "url" in log.metadata
    assert "created_at"  # timestamp field exists


@pytest.mark.django_db
def test_search_log_has_query_in_metadata(admin_client, admin_user, company):
    """Search log stores the query term in metadata."""
    admin_client.get("/api/v1/pkm/notes/?search=invoicing")
    log = UserInteractionLog.objects.filter(interaction_type="search").first()
    assert log is not None
    assert log.metadata["query"] == "invoicing"
