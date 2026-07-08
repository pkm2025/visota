"""Integration tests for PKM Documents API (/api/v1/pkm/documents/).

Covers multipart upload for all supported file types, listing with status,
detail retrieval, delete cascade (file + chunks + embeddings), reprocess,
status endpoint, duplicate detection via SHA-256 checksum, invalid file
type rejection, size limit enforcement, and per-user / per-company isolation.

All LLM/embedding calls are **mocked** (no real API key required).

Fulfills:
    VAL-DOC-001 - Upload a PDF document
    VAL-DOC-002 - Upload a DOCX document
    VAL-DOC-003 - Upload a TXT or Markdown file
    VAL-DOC-004 - Document list shows processing status
    VAL-DOC-005 - Delete a document (cascades to chunks + embeddings)
    VAL-DOC-006 - Document status transitions to processed
    VAL-DOC-007 - Invalid file type rejected
    VAL-DOC-008 - Oversized file rejected
    VAL-DOC-009 - Documents are private per user
    VAL-DOC-010 - Documents multi-tenant isolated
    VAL-DOC-011 - Reprocess a failed document
    VAL-DOC-012 - Duplicate file detection via checksum
    VAL-DOC-013 - Document upload API endpoint (multipart)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument, UserLLMConfig
from apps.pkm.services.encryption_service import encrypt

# ---------------------------------------------------------------------------
# Test data generators
# ---------------------------------------------------------------------------

# Minimal valid PDF header + body
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

    docx_content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats'
        '-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument'
        '.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    docx_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org"
        '/officeDocument/2006/relationships/officeDocument"'
        ' Target="word/document.xml"/>'
        "</Relationships>"
    )
    docx_document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Hello DOCX test</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", docx_content_types)
        zf.writestr("_rels/.rels", docx_rels)
        zf.writestr("word/document.xml", docx_document)
    return buf.getvalue()


def _make_xlsx() -> bytes:
    """Generate a minimal valid .xlsx file (ZIP archive)."""
    import io
    import zipfile

    xlsx_content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats'
        '-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd'
        ".openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "</Types>"
    )
    xlsx_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org"
        '/officeDocument/2006/relationships/officeDocument"'
        ' Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    xlsx_workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>'
        "</workbook>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", xlsx_content_types)
        zf.writestr("_rels/.rels", xlsx_rels)
        zf.writestr("xl/workbook.xml", xlsx_workbook)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_DOC_CO", name="PKM Doc Test Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_DOC_CO2", name="PKM Doc Test Co 2")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_doc_user", password="Test1234", email="docuser@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_doc_other", password="Test1234", email="docother@t.co"
    )


@pytest.fixture
def llm_config(db, user, company):
    """Create an active LLM config with an encrypted dummy API key."""
    return UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encrypt("sk-test-dummy-key"),
        default_model="gpt-4o-mini",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )


@pytest.fixture
def client(user):
    """Authenticated test client for ``user``."""
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def other_client(other_user):
    """Authenticated test client for ``other_user`` (same company)."""
    c = Client()
    c.force_login(other_user)
    return c


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
# Upload: Supported file types (VAL-DOC-001, 002, 003, 013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_txt_document(client, user, company, llm_config):
    """POST /api/v1/pkm/documents/ uploads a TXT file and returns 201."""
    upload = SimpleUploadedFile("test.txt", b"Hello text world", content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post(
            "/api/v1/pkm/documents/",
            data={"file": upload, "title": "My Text Doc"},
        )
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["title"] == "My Text Doc"
    assert data["file_type"] == "txt"
    assert data["status"] == "pending"
    assert data["checksum"] != ""
    # Verify DB record
    doc = PKMDocument.objects.get(id=data["id"])
    assert doc.user == user
    assert doc.company == company
    assert doc.file_type == "txt"


@pytest.mark.django_db
def test_upload_md_document(client, user, company, llm_config):
    """Upload a Markdown file."""
    upload = SimpleUploadedFile(
        "readme.md", b"# Heading\n\nSome **markdown** text.", content_type="text/markdown"
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["file_type"] == "md"
    assert data["title"] == "readme"


@pytest.mark.django_db
def test_upload_pdf_document(client, user, company, llm_config):
    """Upload a PDF file."""
    upload = SimpleUploadedFile(
        "report.pdf", MINIMAL_PDF, content_type="application/pdf"
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["file_type"] == "pdf"
    assert data["title"] == "report"


@pytest.mark.django_db
def test_upload_docx_document(client, user, company, llm_config):
    """Upload a DOCX file."""
    docx_bytes = _make_docx()
    upload = SimpleUploadedFile("document.docx", docx_bytes)
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["file_type"] == "docx"


@pytest.mark.django_db
def test_upload_xlsx_document(client, user, company, llm_config):
    """Upload an XLSX file."""
    xlsx_bytes = _make_xlsx()
    upload = SimpleUploadedFile("spreadsheet.xlsx", xlsx_bytes)
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["file_type"] == "xlsx"


@pytest.mark.django_db
def test_upload_without_title_uses_filename(client, user, company, llm_config):
    """When no title is provided, the filename (without extension) is used."""
    upload = SimpleUploadedFile("auto_title.txt", b"content", content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201
    assert response.json()["title"] == "auto_title"


@pytest.mark.django_db
def test_upload_enqueues_async_task(client, user, company, llm_config):
    """Upload enqueues ``schedule_document_processing`` for the document."""
    upload = SimpleUploadedFile("task_test.txt", b"content", content_type="text/plain")
    with patch(
        "apps.pkm.services.rag_pipeline.schedule_document_processing"
    ) as mock_schedule:
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201
    assert mock_schedule.called
    # Verify the document_id was passed
    call_args = mock_schedule.call_args
    doc_id = call_args[0][0]
    assert PKMDocument.objects.filter(id=doc_id).exists()


@pytest.mark.django_db
def test_upload_unauthenticated(db):
    """POST without authentication returns 401."""
    c = Client()
    upload = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
    response = c.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Upload: Invalid file type (VAL-DOC-007)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_exe_rejected(client, user, company, llm_config):
    """An .exe file is rejected with 400."""
    upload = SimpleUploadedFile("malware.exe", b"MZ\x90\x00")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 400
    body = str(response.json()).lower()
    assert "not allowed" in body


@pytest.mark.django_db
def test_upload_zip_rejected(client, user, company, llm_config):
    """A .zip file is rejected with 400."""
    upload = SimpleUploadedFile("archive.zip", b"PK\x03\x04", content_type="application/zip")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 400


@pytest.mark.django_db
def test_upload_invalid_type_no_document_created(client, user, company, llm_config):
    """Rejected uploads do not create a PKMDocument record."""
    upload = SimpleUploadedFile("bad.exe", b"binary data", content_type="application/x-msdownload")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert PKMDocument.objects.count() == 0


@pytest.mark.django_db
def test_upload_jpg_rejected(client, user, company, llm_config):
    """A .jpg file is rejected with 400."""
    upload = SimpleUploadedFile(
        "photo.jpg", b"\xff\xd8\xff\xe0", content_type="image/jpeg"
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Upload: Size limit (VAL-DOC-008)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_oversized_rejected(client, user, company, llm_config):
    """A file exceeding 20MB is rejected with 400."""
    # Create a file just over 20MB
    large_content = b"x" * (20 * 1024 * 1024 + 1)
    upload = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 400
    body = str(response.json()).lower()
    assert "exceeds" in body or "size" in body


@pytest.mark.django_db
def test_upload_within_size_limit_accepted(client, user, company, llm_config):
    """A file just under 20MB is accepted."""
    # Create a file just under 20MB (but not too large for test memory)
    content = b"y" * (1024 * 1024)  # 1MB
    upload = SimpleUploadedFile("ok.txt", content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201
    assert response.json()["file_size"] == 1024 * 1024


@pytest.mark.django_db
def test_upload_oversized_no_document_created(client, user, company, llm_config):
    """Oversized uploads do not create a record."""
    large_content = b"z" * (20 * 1024 * 1024 + 100)
    upload = SimpleUploadedFile("big.txt", large_content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert PKMDocument.objects.count() == 0


# ---------------------------------------------------------------------------
# Duplicate detection (VAL-DOC-012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upload_duplicate_warns(client, user, company, llm_config):
    """Uploading the same content twice triggers a duplicate warning."""
    content = b"Identical content for dedup test"
    upload1 = SimpleUploadedFile("first.txt", content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        resp1 = client.post("/api/v1/pkm/documents/", data={"file": upload1, "title": "First"})
    assert resp1.status_code == 201
    assert resp1.json()["is_duplicate"] is False

    upload2 = SimpleUploadedFile("second.txt", content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        resp2 = client.post(
            "/api/v1/pkm/documents/", data={"file": upload2, "title": "Second"}
        )
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    msg = data2["duplicate_message"].lower()
    assert "checksum" in msg or "exists" in msg


@pytest.mark.django_db
def test_upload_different_content_not_duplicate(client, user, company, llm_config):
    """Different content does not trigger duplicate warning."""
    upload1 = SimpleUploadedFile("a.txt", b"Content A", content_type="text/plain")
    upload2 = SimpleUploadedFile("b.txt", b"Content B", content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        resp1 = client.post("/api/v1/pkm/documents/", data={"file": upload1})
        resp2 = client.post("/api/v1/pkm/documents/", data={"file": upload2})
    assert resp1.json()["is_duplicate"] is False
    assert resp2.json()["is_duplicate"] is False


@pytest.mark.django_db
def test_checksum_computed_correctly(client, user, company, llm_config):
    """The SHA-256 checksum is computed and stored correctly."""
    import hashlib

    content = b"Checksum test content"
    upload = SimpleUploadedFile("hash.txt", content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    expected = hashlib.sha256(content).hexdigest()
    assert response.json()["checksum"] == expected


@pytest.mark.django_db
def test_duplicate_scoped_per_user(client, other_client, user, other_user, company, llm_config):
    """Same checksum from different users is NOT flagged as duplicate."""
    content = b"Shared content across users"
    upload1 = SimpleUploadedFile("u1.txt", content, content_type="text/plain")
    upload2 = SimpleUploadedFile("u2.txt", content, content_type="text/plain")
    with patch("apps.pkm.services.rag_pipeline.schedule_document_processing"):
        resp1 = client.post("/api/v1/pkm/documents/", data={"file": upload1})
        resp2 = other_client.post("/api/v1/pkm/documents/", data={"file": upload2})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["is_duplicate"] is False
    assert resp2.json()["is_duplicate"] is False


# ---------------------------------------------------------------------------
# List documents (VAL-DOC-004)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_documents(client, user, company):
    """GET /api/v1/pkm/documents/ returns user's documents with status."""
    _create_document(user, company, title="Doc 1", status=PKMDocument.Status.PENDING)
    _create_document(user, company, title="Doc 2", status=PKMDocument.Status.PROCESSED)
    response = client.get("/api/v1/pkm/documents/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2


@pytest.mark.django_db
def test_list_documents_shows_status(client, user, company):
    """Each document in the list includes its processing status."""
    _create_document(user, company, title="Pending", status=PKMDocument.Status.PENDING)
    _create_document(
        user, company, title="Processed", status=PKMDocument.Status.PROCESSED
    )
    _create_document(user, company, title="Failed", status=PKMDocument.Status.FAILED)
    response = client.get("/api/v1/pkm/documents/")
    items = response.json()["items"]
    statuses = {item["status"] for item in items}
    assert "pending" in statuses
    assert "processed" in statuses
    assert "failed" in statuses


@pytest.mark.django_db
def test_list_documents_filter_by_status(client, user, company):
    """Filtering by status returns only matching documents."""
    _create_document(user, company, title="Pending", status=PKMDocument.Status.PENDING)
    _create_document(
        user, company, title="Processed", status=PKMDocument.Status.PROCESSED
    )
    response = client.get("/api/v1/pkm/documents/?status=processed")
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "processed"


@pytest.mark.django_db
def test_list_documents_empty(client, user, company):
    """GET returns empty list when user has no documents."""
    response = client.get("/api/v1/pkm/documents/")
    assert response.json()["items"] == []


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_document_detail(client, user, company):
    """GET /api/v1/pkm/documents/{id}/ returns document detail."""
    doc = _create_document(user, company, title="Detail Doc", file_type="pdf")
    response = client.get(f"/api/v1/pkm/documents/{doc.id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["title"] == "Detail Doc"
    assert data["file_type"] == "pdf"
    assert "file_url" in data


@pytest.mark.django_db
def test_get_nonexistent_document_404(client):
    """GET a document that does not exist returns 404."""
    response = client.get("/api/v1/pkm/documents/99999/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete document (VAL-DOC-005)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_document(client, user, company, llm_config):
    """DELETE removes the document record and file."""
    doc = _create_document(user, company, title="To Delete")
    doc_id = doc.id
    response = client.delete(f"/api/v1/pkm/documents/{doc_id}/")
    assert response.status_code == 200
    assert response.json()["message"] == "Document deleted"
    assert not PKMDocument.objects.filter(id=doc_id).exists()


@pytest.mark.django_db
def test_delete_cascades_to_chunks(client, user, company, llm_config):
    """DELETE removes all associated DocumentChunk records."""
    doc = _create_document(user, company, title="With Chunks")
    # Create some chunks
    DocumentChunk.objects.create(document=doc, chunk_index=0, content="chunk 0", token_count=10)
    DocumentChunk.objects.create(document=doc, chunk_index=1, content="chunk 1", token_count=10)
    assert DocumentChunk.objects.filter(document=doc).count() == 2

    response = client.delete(f"/api/v1/pkm/documents/{doc.id}/")
    assert response.status_code == 200
    assert DocumentChunk.objects.filter(document_id=doc.id).count() == 0


@pytest.mark.django_db
def test_delete_cascades_to_embeddings(client, user, company, llm_config):
    """DELETE removes all associated Embedding records from the DB."""
    doc = _create_document(user, company, title="With Embeddings")
    chunk = DocumentChunk.objects.create(
        document=doc, chunk_index=0, content="text", token_count=4
    )

    # Insert an embedding row via raw SQL (VECTOR column)
    import json

    vec = json.dumps([0.1] * 1536)
    insert_sql = (
        "INSERT INTO pkm_embedding"
        " (chunk_id, user_id, company_id, content, model_name, embedding, created_at)"
        " VALUES (%s, %s, %s, %s, %s, VEC_FromText(%s), NOW())"
    )
    with connection.cursor() as cursor:
        cursor.execute(
            insert_sql,
            [chunk.id, user.id, company.id, "text", "test-model", vec],
        )

    # Verify embedding exists
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id = %s", [chunk.id]
        )
        assert cursor.fetchone()[0] == 1

    # Delete the document
    response = client.delete(f"/api/v1/pkm/documents/{doc.id}/")
    assert response.status_code == 200

    # Verify embedding is gone
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE user_id = %s AND company_id = %s",
            [user.id, company.id],
        )
        assert cursor.fetchone()[0] == 0


@pytest.mark.django_db
def test_delete_nonexistent_document_404(client):
    """DELETE on nonexistent document returns 404."""
    response = client.delete("/api/v1/pkm/documents/99999/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Status endpoint (VAL-DOC-006)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_document_status(client, user, company):
    """GET /api/v1/pkm/documents/{id}/status/ returns current status."""
    doc = _create_document(
        user, company, title="Status Doc", status=PKMDocument.Status.PROCESSING
    )
    response = client.get(f"/api/v1/pkm/documents/{doc.id}/status/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["status"] == "processing"


@pytest.mark.django_db
def test_get_document_status_with_error(client, user, company):
    """Status endpoint includes error_message for failed documents."""
    doc = _create_document(
        user,
        company,
        title="Failed Doc",
        status=PKMDocument.Status.FAILED,
        error_message="Processing failed due to corrupt file",
    )
    response = client.get(f"/api/v1/pkm/documents/{doc.id}/status/")
    data = response.json()
    assert data["status"] == "failed"
    assert "corrupt file" in data["error_message"]


@pytest.mark.django_db
def test_get_status_nonexistent_404(client):
    """GET status for nonexistent document returns 404."""
    response = client.get("/api/v1/pkm/documents/99999/status/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_status_transitions_after_processing(client, user, company, llm_config):
    """Document status transitions from pending to processed after pipeline."""
    # Upload document
    upload = SimpleUploadedFile(
        "transition.txt", b"Transition test content", content_type="text/plain"
    )

    from types import SimpleNamespace

    mock_emb_response = SimpleNamespace(data=[SimpleNamespace(embedding=[0.01] * 1536)])

    # Upload with sync processing (no mock on schedule -> runs pipeline in test sync mode)
    with patch(
        "apps.pkm.services.rag_pipeline.get_embedding", return_value=mock_emb_response
    ):
        response = client.post("/api/v1/pkm/documents/", data={"file": upload})
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # After sync processing, status should be "processed"
    status_resp = client.get(f"/api/v1/pkm/documents/{doc_id}/status/")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "processed"


# ---------------------------------------------------------------------------
# Reprocess (VAL-DOC-011)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reprocess_document(client, user, company, llm_config):
    """POST /api/v1/pkm/documents/{id}/reprocess/ re-queues the pipeline."""
    doc = _create_document(
        user,
        company,
        title="Reprocess Me",
        status=PKMDocument.Status.FAILED,
        error_message="Previous failure",
    )

    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing") as mock_sched:
        response = client.post(f"/api/v1/pkm/documents/{doc.id}/reprocess/")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert "re-queued" in data["message"].lower() or "reprocess" in data["message"].lower()
    assert mock_sched.called
    assert mock_sched.call_args[0][0] == doc.id

    # Status should be reset to pending
    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PENDING
    assert doc.error_message == ""


@pytest.mark.django_db
def test_reprocess_nonexistent_404(client):
    """Reprocess on nonexistent document returns 404."""
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        response = client.post("/api/v1/pkm/documents/99999/reprocess/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_reprocess_clears_failed_status(client, user, company, llm_config):
    """Reprocessing clears the error_message from a previous failure."""
    doc = _create_document(
        user,
        company,
        title="Failed",
        status=PKMDocument.Status.FAILED,
        error_message="Old error",
    )
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        client.post(f"/api/v1/pkm/documents/{doc.id}/reprocess/")
    doc.refresh_from_db()
    assert doc.status == PKMDocument.Status.PENDING
    assert doc.error_message == ""


# ---------------------------------------------------------------------------
# Per-user isolation (VAL-DOC-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_documents_private_per_user_list(user, other_user, company):
    """User B cannot see User A's documents in the list."""
    _create_document(user, company, title="User A Doc")
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.get("/api/v1/pkm/documents/")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.django_db
def test_documents_private_per_user_detail(user, other_user, company):
    """User B gets 404 when accessing User A's document detail."""
    doc_a = _create_document(user, company, title="Private Doc")
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.get(f"/api/v1/pkm/documents/{doc_a.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_documents_private_per_user_delete(user, other_user, company):
    """User B cannot delete User A's document."""
    doc_a = _create_document(user, company, title="User A Doc")
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.delete(f"/api/v1/pkm/documents/{doc_a.id}/")
    assert response.status_code == 404
    assert PKMDocument.objects.filter(id=doc_a.id).exists()


@pytest.mark.django_db
def test_documents_private_per_user_status(user, other_user, company):
    """User B cannot access User A's document status."""
    doc_a = _create_document(user, company, title="Private")
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.get(f"/api/v1/pkm/documents/{doc_a.id}/status/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_documents_private_per_user_reprocess(user, other_user, company):
    """User B cannot reprocess User A's document."""
    doc_a = _create_document(user, company, title="Private")
    c_b = Client()
    c_b.force_login(other_user)
    with patch("apps.pkm.services.rag_pipeline.schedule_reprocessing"):
        response = c_b.post(f"/api/v1/pkm/documents/{doc_a.id}/reprocess/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Multi-tenant isolation (VAL-DOC-010)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_documents_isolated_by_company_orm(user, company, other_company):
    """Documents are scoped by company at the ORM level."""
    doc_x = _create_document(user, company, title="Company X Doc")
    doc_y = _create_document(user, other_company, title="Company Y Doc")

    qs_x = PKMDocument.objects.filter(user=user, company=company)
    assert doc_x in qs_x
    assert doc_y not in qs_x

    qs_y = PKMDocument.objects.filter(user=user, company=other_company)
    assert doc_y in qs_y
    assert doc_x not in qs_y


@pytest.mark.django_db
def test_documents_isolated_by_company_list(user, company, other_company):
    """List endpoint only returns documents for the resolved company."""
    doc_x = _create_document(user, company, title="Company X Doc")
    _create_document(user, other_company, title="Company Y Doc")

    c = Client()
    c.force_login(user)

    from django.test import RequestFactory

    from apps.core.api import get_current_company

    factory = RequestFactory()
    req = factory.get("/api/v1/pkm/documents/")
    req.user = user
    resolved_company = get_current_company(req)

    response = c.get("/api/v1/pkm/documents/")
    items = response.json()["items"]
    if resolved_company == company:
        assert any(item["id"] == doc_x.id for item in items)
        assert all(item["title"] != "Company Y Doc" for item in items)
    else:
        assert all(item["title"] != "Company X Doc" for item in items)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_list_pagination(client, user, company):
    """Document list supports pagination."""
    for i in range(15):
        _create_document(user, company, title=f"Doc {i}")
    response = client.get("/api/v1/pkm/documents/?limit=5")
    data = response.json()
    assert data["count"] == 15
    assert len(data["items"]) == 5


@pytest.mark.django_db
def test_document_list_pagination_offset(client, user, company):
    """Document list supports offset pagination."""
    for i in range(10):
        _create_document(user, company, title=f"Doc {i}")
    response = client.get("/api/v1/pkm/documents/?limit=5&offset=5")
    data = response.json()
    assert data["count"] == 10
    assert len(data["items"]) == 5
