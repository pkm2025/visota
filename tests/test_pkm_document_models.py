"""Tests for PKM document models: PKMDocument, DocumentChunk, Embedding.

Covers model creation, field constraints, cascade deletes, status defaults,
multi-tenant isolation, and VECTOR column existence (via raw SQL insertion
and similarity search on real MariaDB).

Fulfills VAL-RAG-004 (chunks stored in DocumentChunk table) and
VAL-RAG-005 (embeddings stored in VECTOR column).
"""

import json

import pytest
from django.db import connection

from apps.core.managers import CompanyOwnedModel
from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, Embedding, PKMDocument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_DOC_TEST", name="PKM Doc Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_doc_user", password="Test1234", email="doc@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_doc_other", password="Test1234", email="doc_other@t.co"
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_DOC_OTHER", name="PKM Doc Other Co")


@pytest.fixture
def document(db, user, company, tmp_path):
    """Create a PKMDocument with a dummy file path."""
    # Create a real temp file so FileField doesn't complain
    from django.core.files.uploadedfile import SimpleUploadedFile

    dummy_file = SimpleUploadedFile(
        "test_doc.pdf", b"dummy content for test", content_type="application/pdf"
    )
    return PKMDocument.objects.create(
        user=user,
        company=company,
        title="Test Document",
        file=dummy_file,
        file_type="pdf",
        file_size=22,
    )


# ---------------------------------------------------------------------------
# Model inheritance and structural checks
# ---------------------------------------------------------------------------


def test_pkm_document_extends_company_owned_model():
    """PKMDocument must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(PKMDocument, CompanyOwnedModel)


def test_embedding_extends_company_owned_model():
    """Embedding must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(Embedding, CompanyOwnedModel)


def test_document_chunk_has_document_fk():
    """DocumentChunk must have a document FK (not CompanyOwned, linked to doc)."""
    from django.db import models

    assert hasattr(DocumentChunk, "document")
    field = DocumentChunk._meta.get_field("document")
    assert field.remote_field.on_delete == models.CASCADE


# ---------------------------------------------------------------------------
# PKMDocument model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_document_creation(document):
    """PKMDocument can be created with all required fields."""
    assert document.pk is not None
    assert document.title == "Test Document"
    assert document.file_type == "pdf"
    assert document.file_size == 22
    assert document.status == "pending"
    assert document.checksum == ""
    assert document.error_message == ""
    assert document.created_at is not None
    assert document.updated_at is not None


@pytest.mark.django_db
def test_document_status_default_pending(document):
    """Status defaults to 'pending'."""
    assert document.status == "pending"


@pytest.mark.django_db
def test_document_status_choices(user, company):
    """All status choices can be set."""
    statuses = ["pending", "processing", "processed", "failed"]
    for status in statuses:
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc = PKMDocument.objects.create(
            user=user,
            company=company,
            title=f"Doc {status}",
            file=SimpleUploadedFile(f"f_{status}.pdf", b"data"),
            file_type="pdf",
            status=status,
        )
        assert doc.status == status


@pytest.mark.django_db
def test_document_checksum_for_dedup(user, company):
    """Checksum field stores hash for duplicate detection."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Checksummed Doc",
        file=SimpleUploadedFile("c.pdf", b"data"),
        file_type="pdf",
        checksum="abc123def456",
    )
    assert doc.checksum == "abc123def456"


@pytest.mark.django_db
def test_document_error_message_blank(user, company):
    """Error message defaults to blank."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="No Error Doc",
        file=SimpleUploadedFile("n.pdf", b"data"),
        file_type="pdf",
    )
    assert doc.error_message == ""


@pytest.mark.django_db
def test_document_error_message_set(user, company):
    """Error message can be set for failed documents."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc = PKMDocument.objects.create(
        user=user,
        company=company,
        title="Failed Doc",
        file=SimpleUploadedFile("f.pdf", b"data"),
        file_type="pdf",
        status="failed",
        error_message="PDF parsing failed: corrupt file",
    )
    assert doc.error_message == "PDF parsing failed: corrupt file"


@pytest.mark.django_db
def test_document_user_isolation(company, user, other_user):
    """Documents are private per user."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    PKMDocument.objects.create(
        user=user,
        company=company,
        title="User A Doc",
        file=SimpleUploadedFile("a.pdf", b"data"),
        file_type="pdf",
    )
    other_docs = PKMDocument.objects.filter(user=other_user, company=company)
    assert other_docs.count() == 0


@pytest.mark.django_db
def test_document_company_isolation(user, company, other_company):
    """Documents are isolated by company."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    PKMDocument.objects.create(
        user=user,
        company=company,
        title="Company A Doc",
        file=SimpleUploadedFile("a.pdf", b"data"),
        file_type="pdf",
    )
    other_docs = PKMDocument.objects.filter(user=user, company=other_company)
    assert other_docs.count() == 0


@pytest.mark.django_db
def test_document_str_representation(document):
    """PKMDocument __str__ returns the title."""
    assert str(document) == "Test Document"


@pytest.mark.django_db
def test_document_cascade_delete_user(document):
    """Deleting a user cascades to their documents."""
    user_id = document.user.id
    assert PKMDocument.objects.filter(user_id=user_id).count() == 1
    document.user.delete()
    assert PKMDocument.objects.filter(user_id=user_id).count() == 0


# ---------------------------------------------------------------------------
# DocumentChunk model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_chunk_creation(document):
    """DocumentChunk can be created with all required fields."""
    chunk = DocumentChunk.objects.create(
        document=document,
        chunk_index=0,
        content="This is the first chunk of text.",
        token_count=10,
    )
    assert chunk.pk is not None
    assert chunk.document == document
    assert chunk.chunk_index == 0
    assert chunk.content == "This is the first chunk of text."
    assert chunk.token_count == 10
    assert chunk.created_at is not None


@pytest.mark.django_db
def test_chunk_multiple_for_document(document):
    """Multiple chunks can be created for a single document."""
    for i in range(5):
        DocumentChunk.objects.create(
            document=document,
            chunk_index=i,
            content=f"Chunk {i} content",
            token_count=5,
        )
    assert document.chunks.count() == 5


@pytest.mark.django_db
def test_chunk_cascade_delete_document(document):
    """Deleting a document cascades to its chunks."""
    DocumentChunk.objects.create(
        document=document, chunk_index=0, content="content", token_count=5
    )
    doc_id = document.id
    assert DocumentChunk.objects.filter(document_id=doc_id).count() == 1
    document.delete()
    assert DocumentChunk.objects.filter(document_id=doc_id).count() == 0


@pytest.mark.django_db
def test_chunk_str_representation(document):
    """DocumentChunk __str__ includes chunk index."""
    chunk = DocumentChunk.objects.create(
        document=document, chunk_index=3, content="text", token_count=1
    )
    s = str(chunk)
    assert "3" in s


# ---------------------------------------------------------------------------
# Embedding model + VECTOR column tests (VAL-RAG-004, VAL-RAG-005)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_embedding_vector_column_exists():
    """The pkm_embedding table has a VECTOR(1536) column (schema inspection)."""
    with connection.cursor() as cursor:
        cursor.execute("DESCRIBE pkm_embedding")
        columns = {row[0]: row[1] for row in cursor.fetchall()}
    assert "embedding" in columns
    assert "vector(1536)" in columns["embedding"].lower()


@pytest.mark.django_db
def test_embedding_vector_index_exists():
    """The HNSW vector index exists on the embedding column."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW INDEX FROM pkm_embedding")
        indexes = cursor.fetchall()
    vec_indexes = [idx for idx in indexes if "VECTOR" in str(idx[10]).upper()]
    assert len(vec_indexes) >= 1, "Expected at least one VECTOR index"


@pytest.mark.django_db
def test_store_and_retrieve_embedding_via_raw_sql(document, user, company):
    """Embeddings can be stored via VEC_FromText and retrieved (VAL-RAG-005)."""
    chunk = DocumentChunk.objects.create(
        document=document, chunk_index=0, content="chunk text", token_count=5
    )
    vec = [0.01] * 1536
    vec_str = json.dumps(vec)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pkm_embedding
                (chunk_id, user_id, company_id, content, embedding, model_name, created_at)
            VALUES (%s, %s, %s, %s, VEC_FromText(%s), %s, NOW())
            """,
            [chunk.id, user.id, company.id, "cached text", vec_str, "test-model"],
        )
        cursor.execute(
            """
            SELECT id, content, model_name,
                   VEC_DISTANCE_COSINE(embedding, VEC_FromText(%s)) AS distance
            FROM pkm_embedding
            WHERE chunk_id = %s
            """,
            [vec_str, chunk.id],
        )
        row = cursor.fetchone()
    assert row is not None
    assert row[0] > 0  # embedding id
    assert row[1] == "cached text"
    assert row[2] == "test-model"
    assert row[3] < 0.001  # same vector -> near-zero distance


@pytest.mark.django_db
def test_embedding_similarity_search(document, user, company):
    """Vector similarity search returns ranked results (VAL-RAG-006 basics)."""
    # Create 3 chunks with embeddings
    chunks = []
    for i in range(3):
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=i,
            content=f"Chunk {i}",
            token_count=5,
        )
        chunks.append(chunk)

    # Insert embeddings: chunk0 close to query, chunk1 far, chunk2 close
    query_vec = [1.0] * 1536
    close_vec = [0.99] * 1536
    far_vec = [-1.0] * 1536
    close_vec2 = [0.95] * 1536

    vectors = {chunks[0].id: close_vec, chunks[1].id: far_vec, chunks[2].id: close_vec2}

    with connection.cursor() as cursor:
        for chunk_id, vec in vectors.items():
            cursor.execute(
                """
                INSERT INTO pkm_embedding
                    (chunk_id, user_id, company_id, content, embedding, model_name, created_at)
                VALUES (%s, %s, %s, %s, VEC_FromText(%s), %s, NOW())
                """,
                [chunk_id, user.id, company.id, f"text {chunk_id}",
                 json.dumps(vec), "test-model"],
            )

        # Search for vectors close to query_vec
        cursor.execute(
            """
            SELECT e.chunk_id,
                   VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s)) AS distance
            FROM pkm_embedding e
            WHERE e.user_id = %s AND e.company_id = %s
            ORDER BY VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s))
            LIMIT 3
            """,
            [json.dumps(query_vec), user.id, company.id, json.dumps(query_vec)],
        )
        rows = cursor.fetchall()

    # Results should be ordered by distance ascending
    assert len(rows) == 3
    assert rows[0][1] <= rows[1][1] <= rows[2][1]
    # chunk1 (far_vec = [-1.0]*1536) should be the farthest
    assert rows[2][0] == chunks[1].id


@pytest.mark.django_db
def test_embedding_cascade_delete_chunk(document, user, company):
    """Deleting a chunk cascades to its embeddings."""
    chunk = DocumentChunk.objects.create(
        document=document, chunk_index=0, content="text", token_count=1
    )
    vec_str = json.dumps([0.0] * 1536)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pkm_embedding
                (chunk_id, user_id, company_id, content, embedding, model_name, created_at)
            VALUES (%s, %s, %s, %s, VEC_FromText(%s), %s, NOW())
            """,
            [chunk.id, user.id, company.id, "text", vec_str, "m"],
        )
        assert (
            cursor.execute(
                "SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id = %s", [chunk.id]
            )
            is not None
        )
    chunk.delete()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id = %s", [chunk.id]
        )
        count = cursor.fetchone()[0]
    assert count == 0


@pytest.mark.django_db
def test_embedding_per_user_isolation(document, user, other_user, company):
    """Vector search for user A returns only user A's embeddings (VAL-RAG-011)."""
    chunk = DocumentChunk.objects.create(
        document=document, chunk_index=0, content="user A chunk", token_count=1
    )
    vec_str = json.dumps([0.5] * 1536)
    with connection.cursor() as cursor:
        # Insert embedding for user A
        cursor.execute(
            """
            INSERT INTO pkm_embedding
                (chunk_id, user_id, company_id, content, embedding, model_name, created_at)
            VALUES (%s, %s, %s, %s, VEC_FromText(%s), %s, NOW())
            """,
            [chunk.id, user.id, company.id, "user A text", vec_str, "m"],
        )

        # Search as user B
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pkm_embedding
            WHERE user_id = %s AND company_id = %s
            """,
            [other_user.id, company.id],
        )
        count_b = cursor.fetchone()[0]

        # Search as user A
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pkm_embedding
            WHERE user_id = %s AND company_id = %s
            """,
            [user.id, company.id],
        )
        count_a = cursor.fetchone()[0]

    assert count_b == 0
    assert count_a == 1


@pytest.mark.django_db
def test_chunks_stored_in_documentchunk_table(document):
    """Multiple chunks from a document are persisted (VAL-RAG-004)."""
    for i in range(10):
        DocumentChunk.objects.create(
            document=document,
            chunk_index=i,
            content=f"Chunk number {i} with some text content.",
            token_count=8,
        )
    assert DocumentChunk.objects.filter(document=document).count() == 10
    # Verify correct FK
    for chunk in document.chunks.all():
        assert chunk.document_id == document.id
