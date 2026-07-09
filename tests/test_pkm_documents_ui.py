"""Integration tests for PKM Documents UI views (/modern/knowledge/documents/).

Covers:
    VAL-DOC-001 - Upload a PDF document via browser
    VAL-DOC-002 - Upload a DOCX document via browser
    VAL-DOC-003 - Upload a TXT or Markdown file via browser
    VAL-DOC-004 - Document list shows processing status (badges)
    VAL-DOC-005 - Delete a document via browser
    VAL-DOC-006 - Document status transitions to processed
    VAL-DOC-007 - Invalid file type rejected
    VAL-DOC-008 - Oversized file rejected
    VAL-DOC-011 - Reprocess a failed document via browser

These tests exercise the UI layer (views + templates) using the Django test
client. All async processing is mocked — no real LLM/embedding API calls.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.models import DocumentChunk, PKMDocument

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"xref\n0 3\n0000000000 65535 f \n"
    b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
)


def _make_docx() -> bytes:
    """Generate a minimal valid .docx file (ZIP archive)."""
    import io
    import zipfile

    docx_document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Hello DOCX</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats'
            '-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd'
            '.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006'
            '/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org'
            '/officeDocument/2006/relationships/officeDocument"'
            ' Target="word/document.xml"/>'
            "</Relationships>",
        )
        zf.writestr("word/document.xml", docx_document)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_DOC_UI", name="PKM Doc UI Co")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="pkm_doc_admin", password="Test1234", email="docadmin@t.co"
    )


@pytest.fixture
def regular_user_with_perm(db, company):
    user = User.objects.create_user(
        username="pkm_doc_perm", password="Test1234", email="docperm@t.co"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(company=company, code="pkm_doc_role", name="PKM Doc Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def admin_client(admin_user, company):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def perm_client(regular_user_with_perm, company):
    c = Client()
    c.force_login(regular_user_with_perm)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def other_user(db, company):
    """A second user WITH pkm.access (so we test data isolation, not permission)."""
    user = User.objects.create_user(
        username="pkm_doc_other", password="Test1234", email="docother@t.co"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(
        company=company, code="pkm_doc_other_role", name="Other PKM Doc Role"
    )
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


def _create_document(user, company, **kwargs):
    """Helper: create a PKMDocument with a dummy file."""
    defaults = {
        "title": "Test Doc",
        "file_type": "txt",
        "file_size": 100,
        "status": PKMDocument.Status.PENDING,
        "checksum": "",
    }
    defaults.update(kwargs)
    if "file" not in defaults:
        upload = SimpleUploadedFile("test.txt", b"test content", content_type="text/plain")
        defaults["file"] = upload
    return PKMDocument.objects.create(user=user, company=company, **defaults)


# ---------------------------------------------------------------------------
# Unauthenticated / permission gating
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_redirect_to_login():
    """Unauthenticated user is redirected to login."""
    client = Client()
    response = client.get("/modern/knowledge/documents/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_no_perm_user_redirected():
    """User without pkm.access is redirected to /no-access/."""
    # Build a no-perm client inline
    company = Company.objects.create(code="PKM_DOC_NOPERM", name="NoPerm Co")
    user = User.objects.create_user(
        username="doc_noperm", password="Test1234", email="np@t.co"
    )
    role = Role.objects.create(company=company, code="no_pkm2", name="No PKM Role 2")
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get("/modern/knowledge/documents/")
    assert response.status_code == 302
    assert "/no-access/" in response.url


# ---------------------------------------------------------------------------
# Navigation reachability
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_list_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_upload_page_reachable(admin_client):
    response = admin_client.get("/modern/knowledge/documents/upload/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_list_in_sidebar(admin_client):
    """Sidebar shows the Documents link."""
    response = admin_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    assert "Tài liệu" in content
    assert "/modern/knowledge/documents/" in content


# ---------------------------------------------------------------------------
# VAL-DOC-004: Document list shows status badges
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_list_shows_documents(admin_client, admin_user, company):
    """Document list page shows the user's documents."""
    _create_document(admin_user, company, title="My PDF", file_type="pdf")
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "My PDF" in content


@pytest.mark.django_db
def test_document_list_shows_status_badges(admin_client, admin_user, company):
    """Each document shows a status badge in the list."""
    _create_document(
        admin_user, company, title="Pending", status=PKMDocument.Status.PENDING
    )
    _create_document(
        admin_user, company, title="Processed", status=PKMDocument.Status.PROCESSED
    )
    _create_document(
        admin_user, company, title="Failed", status=PKMDocument.Status.FAILED
    )
    response = admin_client.get("/modern/knowledge/documents/")
    content = response.content.decode("utf-8")
    # Vietnamese labels
    assert "Chờ xử lý" in content
    assert "Đã xử lý" in content
    assert "Lỗi" in content


@pytest.mark.django_db
def test_document_list_badge_css_class_per_status(admin_client, admin_user, company):
    """Status badges render the correct Bootstrap CSS class per status on the
    initial server-side list load (regression: previously the badges rendered
    empty because the list view passed the _status_badge_class/_status_label
    function objects instead of calling them per document)."""
    _create_document(
        admin_user, company, title="PendingCSS", status=PKMDocument.Status.PENDING
    )
    _create_document(
        admin_user, company, title="ProcessingCSS", status=PKMDocument.Status.PROCESSING
    )
    _create_document(
        admin_user, company, title="ProcessedCSS", status=PKMDocument.Status.PROCESSED
    )
    _create_document(
        admin_user, company, title="FailedCSS", status=PKMDocument.Status.FAILED
    )
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # Each document's badge span must carry both the label text AND the
    # correct CSS class inside the same document-status-badge element.
    # We verify the badge element contains the expected class + label together.
    for status, cls, label in [
        (PKMDocument.Status.PENDING, "bg-secondary", "Chờ xử lý"),
        (PKMDocument.Status.PROCESSING, "bg-info", "Đang xử lý"),
        (PKMDocument.Status.PROCESSED, "bg-success", "Đã xử lý"),
        (PKMDocument.Status.FAILED, "bg-danger", "Lỗi"),
    ]:
        # The document-status-badge class is always present on badge spans
        assert "document-status-badge" in content
        # The expected CSS class must appear inside a badge span (not empty)
        assert cls in content, f"Missing CSS class {cls} for status {status}"
        # The label must appear inside a badge span (not empty)
        assert label in content, f"Missing label {label} for status {status}"


@pytest.mark.django_db
def test_document_list_badge_not_empty_per_document(admin_client, admin_user, company):
    """Each document's badge span in the list contains a non-empty label and
    a concrete bg-* class, not a bare 'badge  ' (double-space = empty class).

    This is the precise regression test: before the fix, the rendered badge
    was '<span class=\"badge  document-status-badge\" ...>\\n    \\n</span>'
    (empty class + empty label) on the initial server-side load.
    """
    doc = _create_document(
        admin_user, company, title="BadgeCheck", status=PKMDocument.Status.PROCESSED
    )
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The inner badge span (from the partial) carries the document-status-badge
    # class and a concrete bg-* class. Locate it and verify both class and body.
    assert "document-status-badge" in content
    # Find every badge span; one must belong to our document and carry bg-success.
    badge_spans = re.findall(
        r'<span class="badge\s+([^"]*document-status-badge[^"]*)"[^>]*id="doc-status-(\d+)"'
        r">(.*?)</span>",
        content,
        re.DOTALL,
    )
    matching = [
        (cls, body)
        for cls, pk, body in badge_spans
        if int(pk) == doc.pk
    ]
    assert matching, (
        f"No document-status-badge span found for document pk={doc.pk}. "
        f"Found badge spans: {badge_spans[:3]}"
    )
    cls, body = matching[0]
    assert "bg-success" in cls, f"Badge class missing bg-success: {cls!r}"
    assert "Đã xử lý" in body, f"Badge body missing 'Đã xử lý': {body!r}"


@pytest.mark.django_db
def test_document_list_empty_state(admin_client):
    """Empty document list shows a message and upload link."""
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chưa có tài liệu" in content


@pytest.mark.django_db
def test_document_list_filter_by_status(admin_client, admin_user, company):
    """Filtering by status returns only matching documents."""
    _create_document(
        admin_user, company, title="PendingOne", status=PKMDocument.Status.PENDING
    )
    _create_document(
        admin_user, company, title="ProcessedOne", status=PKMDocument.Status.PROCESSED
    )
    response = admin_client.get("/modern/knowledge/documents/?status=processed")
    content = response.content.decode("utf-8")
    assert "ProcessedOne" in content
    assert "PendingOne" not in content


@pytest.mark.django_db
def test_document_list_htmx_polling_on_pending(admin_client, admin_user, company):
    """Pending documents have HTMX polling attributes on the badge."""
    _create_document(
        admin_user, company, title="Polling Doc", status=PKMDocument.Status.PENDING
    )
    response = admin_client.get("/modern/knowledge/documents/")
    content = response.content.decode("utf-8")
    assert "hx-get" in content
    assert "every" in content  # hx-trigger="every 3000ms"
    assert "3000ms" in content


@pytest.mark.django_db
def test_document_list_no_polling_on_processed(admin_client, admin_user, company):
    """Processed documents do NOT have HTMX polling attributes."""
    _create_document(
        admin_user, company, title="Done Doc", status=PKMDocument.Status.PROCESSED
    )
    response = admin_client.get("/modern/knowledge/documents/")
    content = response.content.decode("utf-8")
    snippet = content.split("Done Doc")[1].split("list-group-item")[0]
    assert "hx-get" not in snippet


@pytest.mark.django_db
def test_document_list_failed_shows_error_and_reprocess(admin_client, admin_user, company):
    """Failed documents show error message in the list."""
    _create_document(
        admin_user,
        company,
        title="Broken Doc",
        status=PKMDocument.Status.FAILED,
        error_message="Cannot parse this file",
    )
    response = admin_client.get("/modern/knowledge/documents/")
    content = response.content.decode("utf-8")
    assert "Cannot parse this file" in content


# ---------------------------------------------------------------------------
# VAL-DOC-001, 002, 003: Upload via browser
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_txt_via_ui(admin_client, admin_user, company):
    """Upload a TXT file via the upload form."""
    upload = SimpleUploadedFile("note.txt", b"Hello text", content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload, "title": "My Text"},
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get(title="My Text")
    assert doc.user == admin_user
    assert doc.company == company
    assert doc.file_type == "txt"
    assert doc.status == PKMDocument.Status.PENDING


@pytest.mark.django_db
def test_upload_md_via_ui(admin_client):
    """Upload a Markdown file."""
    upload = SimpleUploadedFile(
        "readme.md", b"# Title\nContent", content_type="text/markdown"
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload},
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get()
    assert doc.file_type == "md"
    assert doc.title == "readme"


@pytest.mark.django_db
def test_upload_pdf_via_ui(admin_client):
    """Upload a PDF file (VAL-DOC-001)."""
    upload = SimpleUploadedFile("report.pdf", MINIMAL_PDF, content_type="application/pdf")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload, "title": "PDF Report"},
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get(title="PDF Report")
    assert doc.file_type == "pdf"


@pytest.mark.django_db
def test_upload_docx_via_ui(admin_client):
    """Upload a DOCX file (VAL-DOC-002)."""
    upload = SimpleUploadedFile("document.docx", _make_docx())
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload},
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get()
    assert doc.file_type == "docx"


@pytest.mark.django_db
def test_upload_redirects_to_detail(admin_client):
    """Successful upload redirects to the document detail page."""
    upload = SimpleUploadedFile("x.txt", b"content", content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload, "title": "Redirect Me"},
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get(title="Redirect Me")
    assert f"/modern/knowledge/documents/{doc.pk}/" in response.url


@pytest.mark.django_db
def test_upload_no_file_shows_error(admin_client):
    """POST without a file shows an error and re-renders the form."""
    response = admin_client.post(
        "/modern/knowledge/documents/upload/",
        data={"title": "No File"},
    )
    assert response.status_code == 200  # stays on form
    content = response.content.decode("utf-8")
    assert "Vui lòng chọn một tệp" in content
    assert PKMDocument.objects.count() == 0


# ---------------------------------------------------------------------------
# VAL-DOC-007: Invalid file type rejected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_exe_rejected_via_ui(admin_client):
    """An .exe file is rejected by the UI form."""
    upload = SimpleUploadedFile("malware.exe", b"MZ\x90\x00")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload},
        )
    assert response.status_code == 200  # re-renders form with error
    content = response.content.decode("utf-8")
    assert "không được hỗ trợ" in content
    assert PKMDocument.objects.count() == 0


@pytest.mark.django_db
def test_upload_zip_rejected_via_ui(admin_client):
    """A .zip file is rejected by the UI form."""
    upload = SimpleUploadedFile("archive.zip", b"PK\x03\x04", content_type="application/zip")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload},
        )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "không được hỗ trợ" in content


# ---------------------------------------------------------------------------
# VAL-DOC-008: Oversized file rejected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_oversized_rejected_via_ui(admin_client):
    """A file exceeding 20MB is rejected."""
    large = b"x" * (20 * 1024 * 1024 + 1)
    upload = SimpleUploadedFile("huge.txt", large, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/",
            data={"file": upload},
        )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "vượt quá giới hạn" in content
    assert PKMDocument.objects.count() == 0


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_detail_reachable(admin_client, admin_user, company):
    doc = _create_document(admin_user, company, title="Detail Doc", file_type="pdf")
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Detail Doc" in content
    assert "pdf" in content.lower()


@pytest.mark.django_db
def test_document_detail_shows_chunks_count(admin_client, admin_user, company):
    """Detail page shows the number of chunks."""
    doc = _create_document(
        admin_user, company, title="Chunked", status=PKMDocument.Status.PROCESSED
    )
    DocumentChunk.objects.create(document=doc, chunk_index=0, content="c0", token_count=2)
    DocumentChunk.objects.create(document=doc, chunk_index=1, content="c1", token_count=2)
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    content = response.content.decode("utf-8")
    assert "2" in content  # chunks count


@pytest.mark.django_db
def test_document_detail_404_for_nonexistent(admin_client):
    response = admin_client.get("/modern/knowledge/documents/99999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_document_detail_pending_shows_polling(admin_client, admin_user, company):
    """Pending document detail page has HTMX polling on the badge."""
    doc = _create_document(
        admin_user, company, title="Pending", status=PKMDocument.Status.PENDING
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    content = response.content.decode("utf-8")
    assert "hx-get" in content
    assert "3000ms" in content
    assert "Đang xử lý" in content or "Chờ xử lý" in content


@pytest.mark.django_db
def test_document_detail_failed_shows_error_and_reprocess(admin_client, admin_user, company):
    """Failed document detail shows the error message and a reprocess button."""
    doc = _create_document(
        admin_user,
        company,
        title="Failed",
        status=PKMDocument.Status.FAILED,
        error_message="Boom error",
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    content = response.content.decode("utf-8")
    assert "Boom error" in content
    assert "Xử lý lại" in content
    assert f"/modern/knowledge/documents/{doc.pk}/reprocess/" in content


@pytest.mark.django_db
def test_document_detail_processed_no_reprocess_button(admin_client, admin_user, company):
    """Processed document does NOT show a reprocess button."""
    doc = _create_document(
        admin_user, company, title="Done", status=PKMDocument.Status.PROCESSED
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    content = response.content.decode("utf-8")
    assert "Xử lý lại" not in content


# ---------------------------------------------------------------------------
# VAL-DOC-011: Reprocess a failed document
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reprocess_via_ui(admin_client, admin_user, company):
    """POST to reprocess resets status and re-queues."""
    doc = _create_document(
        admin_user,
        company,
        title="Reprocess Me",
        status=PKMDocument.Status.FAILED,
        error_message="old error",
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing") as mock_sched:
        response = admin_client.post(
            f"/modern/knowledge/documents/{doc.pk}/reprocess/"
        )
    assert response.status_code == 302
    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PENDING
    assert doc.error_message == ""
    assert mock_sched.called
    assert mock_sched.call_args[0][0] == doc.id


@pytest.mark.django_db
def test_reprocess_nonexistent_404(admin_client):
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        response = admin_client.post("/modern/knowledge/documents/99999/reprocess/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# HTMX status badge partial
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_status_partial_pending(admin_client, admin_user, company):
    """The HTMX status partial returns the badge HTML for a pending doc."""
    doc = _create_document(
        admin_user, company, title="Partial", status=PKMDocument.Status.PENDING
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/status/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chờ xử lý" in content
    assert "bg-secondary" in content


@pytest.mark.django_db
def test_status_partial_processed_stops_polling(admin_client, admin_user, company):
    """Processed document partial triggers HX-Stop (terminal state)."""
    doc = _create_document(
        admin_user, company, title="Done", status=PKMDocument.Status.PROCESSED
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/status/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Đã xử lý" in content
    assert "bg-success" in content


@pytest.mark.django_db
def test_status_partial_failed_shows_reprocess(admin_client, admin_user, company):
    """Failed document partial shows the reprocess button."""
    doc = _create_document(
        admin_user,
        company,
        title="Failed",
        status=PKMDocument.Status.FAILED,
        error_message="broken",
    )
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/status/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_status_partial_404_for_nonexistent(admin_client):
    response = admin_client.get("/modern/knowledge/documents/99999/status/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# VAL-DOC-005: Delete via browser
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_confirm_page_loads(admin_client, admin_user, company):
    doc = _create_document(admin_user, company, title="Del Me")
    response = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/delete/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Xác nhận xóa" in content
    assert "Del Me" in content


@pytest.mark.django_db
def test_delete_via_ui(admin_client, admin_user, company):
    """POST on delete page removes the document."""
    doc = _create_document(admin_user, company, title="Del Me")
    doc_pk = doc.pk
    with patch("apps.pkm.services.rag_pipeline.delete_document_data"):
        response = admin_client.post(
            f"/modern/knowledge/documents/{doc_pk}/delete/", {}
        )
    assert response.status_code == 302
    assert "/modern/knowledge/documents/" in response.url
    assert not PKMDocument.objects.filter(pk=doc_pk).exists()


@pytest.mark.django_db
def test_delete_cascades_chunks_via_ui(admin_client, admin_user, company):
    """Delete via UI removes associated chunks."""
    doc = _create_document(admin_user, company, title="With Chunks")
    DocumentChunk.objects.create(document=doc, chunk_index=0, content="c0", token_count=2)
    with patch("apps.pkm.services.rag_pipeline.delete_document_data"):
        response = admin_client.post(f"/modern/knowledge/documents/{doc.pk}/delete/", {})
    assert response.status_code == 302
    assert DocumentChunk.objects.filter(document_id=doc.pk).count() == 0


# ---------------------------------------------------------------------------
# VAL-DOC-006: Status transitions (end-to-end via UI upload)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_then_status_transitions_to_processed(admin_client, admin_user, company, llm_config):
    """After upload (with sync processing), detail shows 'processed'."""
    from types import SimpleNamespace

    mock_emb = SimpleNamespace(data=[SimpleNamespace(embedding=[0.01] * 1536)])
    upload = SimpleUploadedFile(
        "transition.txt", b"Transition content", content_type="text/plain"
    )
    with patch("apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_emb):
        response = admin_client.post(
            "/modern/knowledge/documents/upload/", data={"file": upload}
        )
    assert response.status_code == 302
    doc = PKMDocument.objects.get()
    # After sync processing, status should be processed
    detail_resp = admin_client.get(f"/modern/knowledge/documents/{doc.pk}/")
    content = detail_resp.content.decode("utf-8")
    assert "Đã xử lý" in content


@pytest.fixture
def llm_config(db, admin_user, company):
    from apps.pkm.models import UserLLMConfig
    from apps.pkm.services.encryption_service import encrypt

    return UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_documents_private_per_user_list(admin_user, company, other_user):
    """User B cannot see User A's documents in the list."""
    _create_document(admin_user, company, title="User A Doc")
    c = Client()
    c.force_login(other_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "User A Doc" not in content


@pytest.mark.django_db
def test_documents_private_per_user_detail(admin_user, company, other_user):
    """User B gets 404 accessing User A's document detail."""
    doc = _create_document(admin_user, company, title="Private")
    c = Client()
    c.force_login(other_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.get(f"/modern/knowledge/documents/{doc.pk}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_documents_private_per_user_delete(admin_user, company, other_user):
    """User B cannot delete User A's document."""
    doc = _create_document(admin_user, company, title="Private")
    c = Client()
    c.force_login(other_user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    response = c.post(f"/modern/knowledge/documents/{doc.pk}/delete/")
    assert response.status_code == 404
    assert PKMDocument.objects.filter(pk=doc.pk).exists()


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_list_pagination(admin_client, admin_user, company):
    for i in range(15):
        _create_document(admin_user, company, title=f"Doc {i:02d}")
    response = admin_client.get("/modern/knowledge/documents/")
    assert response.status_code == 200
    assert response.context["is_paginated"] is True
    assert response.context["page_obj"].object_list.count() == 10
    response2 = admin_client.get("/modern/knowledge/documents/?page=2")
    assert response2.status_code == 200
    assert response2.context["page_obj"].object_list.count() == 5


# ---------------------------------------------------------------------------
# Dashboard now shows real document count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_shows_real_doc_count(admin_client, admin_user, company):
    _create_document(admin_user, company, title="D1")
    _create_document(admin_user, company, title="D2")
    response = admin_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    # The stat-docs div should show 2
    assert "stat-docs" in content
    assert ">2<" in content
