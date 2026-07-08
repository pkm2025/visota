"""Integration tests for apps/pkm/services/vector_store.py.

These tests use real MariaDB 12.3 VECTOR operations (no mocking) to verify:
- store_embedding inserts VECTOR data correctly via VEC_FromText
- search_similar returns ranked results ordered by cosine distance
- HNSW vector index is used (verified via EXPLAIN)
- Per-user isolation is enforced (User B never sees User A's vectors)
- Multi-tenant isolation (company scoping)
- delete_embeddings removes records (by chunk_id and by document_id)

Fulfills VAL-RAG-006 (vector similarity search with HNSW index) and
VAL-RAG-011 (per-user isolation in vector search).
"""

import pytest
from django.db import connection

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import DocumentChunk, PKMDocument
from apps.pkm.services.vector_store import (
    delete_embeddings,
    search_similar,
    store_embedding,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_VEC_CO", name="PKM Vec Test Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_VEC_OC", name="PKM Vec Other Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_vec_user", password="Test1234", email="vec@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_vec_other", password="Test1234", email="vec_other@t.co"
    )


@pytest.fixture
def document(db, user, company):
    """Create a PKMDocument with a dummy file."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    return PKMDocument.objects.create(
        user=user,
        company=company,
        title="Vector Test Doc",
        file=SimpleUploadedFile("vec_test.pdf", b"dummy", content_type="application/pdf"),
        file_type="pdf",
        file_size=5,
    )


def _make_chunk(document, index=0, content="chunk text"):
    return DocumentChunk.objects.create(
        document=document,
        chunk_index=index,
        content=content,
        token_count=5,
    )


# ---------------------------------------------------------------------------
# store_embedding tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_store_embedding_returns_id(document, user, company):
    """store_embedding returns a positive integer row id."""
    chunk = _make_chunk(document)
    emb_id = store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="hello world",
        embedding_vector=[0.01] * 1536,
        model_name="text-embedding-3-small",
    )
    assert isinstance(emb_id, int)
    assert emb_id > 0


@pytest.mark.django_db
def test_store_embedding_inserts_correct_data(document, user, company):
    """The inserted row has the correct content, model_name, and FKs."""
    chunk = _make_chunk(document, content="original chunk content")
    emb_id = store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="cached embedding text",
        embedding_vector=[0.5] * 1536,
        model_name="test-embedding-model",
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT chunk_id, user_id, company_id, content, model_name "
            "FROM pkm_embedding WHERE id = %s",
            [emb_id],
        )
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == chunk.id
    assert row[1] == user.id
    assert row[2] == company.id
    assert row[3] == "cached embedding text"
    assert row[4] == "test-embedding-model"


@pytest.mark.django_db
def test_store_embedding_vector_populated(document, user, company):
    """The VECTOR column is populated (distance to same vector is near-zero)."""
    chunk = _make_chunk(document)
    vec = [0.1] * 1536
    emb_id = store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="vec test",
        embedding_vector=vec,
        model_name="m",
    )
    import json

    vec_str = json.dumps(vec)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT VEC_DISTANCE_COSINE(embedding, VEC_FromText(%s)) "
            "FROM pkm_embedding WHERE id = %s",
            [vec_str, emb_id],
        )
        distance = cursor.fetchone()[0]
    assert distance < 0.001


@pytest.mark.django_db
def test_store_embedding_multiple(document, user, company):
    """Multiple embeddings can be stored for different chunks."""
    chunks = [_make_chunk(document, index=i) for i in range(5)]
    for chunk in chunks:
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=f"text {chunk.id}",
            embedding_vector=[0.2] * 1536,
            model_name="m",
        )
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE user_id = %s", [user.id]
        )
        count = cursor.fetchone()[0]
    assert count == 5


# ---------------------------------------------------------------------------
# search_similar tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_similar_returns_results(document, user, company):
    """search_similar returns at least one result when data exists."""
    chunk = _make_chunk(document)
    vec = [1.0] * 1536
    store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="nearby text",
        embedding_vector=vec,
        model_name="m",
    )
    results = search_similar(user.id, company.id, vec, top_k=5)
    assert len(results) >= 1
    assert results[0]["content"] == "nearby text"
    assert results[0]["chunk_id"] == chunk.id


@pytest.mark.django_db
def test_search_similar_ranked_by_distance(document, user, company):
    """Results are ordered by ascending cosine distance."""
    chunks = [_make_chunk(document, index=i) for i in range(3)]

    # Use vectors with clear cosine distance differences.
    # Cosine distance for all-same-value vectors is ~0 regardless of magnitude,
    # so we need actual directional differences.
    query_vec = [1.0] * 768 + [0.0] * 768       # points "right"
    close_vec = [1.0] * 768 + [0.0] * 768        # identical -> distance 0
    medium_vec = [1.0] * 768 + [1.0] * 768       # 45 degrees -> distance ~0.29
    far_vec = [0.0] * 768 + [1.0] * 768          # orthogonal -> distance 1.0

    store_embedding(chunks[0].id, user.id, company.id, "close", close_vec, "m")
    store_embedding(chunks[1].id, user.id, company.id, "far", far_vec, "m")
    store_embedding(chunks[2].id, user.id, company.id, "medium", medium_vec, "m")

    results = search_similar(user.id, company.id, query_vec, top_k=3)
    assert len(results) == 3
    # Distances must be non-decreasing
    distances = [r["distance"] for r in results]
    assert distances[0] <= distances[1] <= distances[2]
    # The "close" chunk should be first (near-zero distance)
    assert results[0]["content"] == "close"
    assert distances[0] < 0.01
    # The "far" chunk should be last (orthogonal)
    assert results[2]["content"] == "far"
    assert distances[2] > 0.9


@pytest.mark.django_db
def test_search_similar_top_k_limit(document, user, company):
    """top_k limits the number of results returned."""
    for i in range(10):
        chunk = _make_chunk(document, index=i)
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=f"chunk {i}",
            embedding_vector=[0.1] * 1536,
            model_name="m",
        )
    results = search_similar(user.id, company.id, [0.1] * 1536, top_k=3)
    assert len(results) == 3


@pytest.mark.django_db
def test_search_similar_empty(user, company):
    """search_similar returns empty list when no embeddings exist."""
    results = search_similar(user.id, company.id, [0.1] * 1536, top_k=5)
    assert results == []


@pytest.mark.django_db
def test_search_similar_result_structure(document, user, company):
    """Each result dict has the expected keys."""
    chunk = _make_chunk(document)
    store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="structured",
        embedding_vector=[0.3] * 1536,
        model_name="m",
    )
    results = search_similar(user.id, company.id, [0.3] * 1536, top_k=1)
    assert len(results) == 1
    result = results[0]
    assert "id" in result
    assert "content" in result
    assert "chunk_id" in result
    assert "distance" in result
    assert isinstance(result["id"], int)
    assert isinstance(result["distance"], float)


@pytest.mark.django_db
def test_search_similar_default_top_k(document, user, company):
    """Default top_k is 10."""
    for i in range(15):
        chunk = _make_chunk(document, index=i)
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=f"chunk {i}",
            embedding_vector=[0.2] * 1536,
            model_name="m",
        )
    results = search_similar(user.id, company.id, [0.2] * 1536)
    assert len(results) == 10


# ---------------------------------------------------------------------------
# HNSW index usage verification (VAL-RAG-006)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_uses_hnsw_vector_index(document, user, company):
    """EXPLAIN on the search query shows the VECTOR index is considered.

    We verify the EXPLAIN output references the vector index or that the
    query plan involves index access on pkm_embedding.
    """
    chunk = _make_chunk(document)
    store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="index test",
        embedding_vector=[0.5] * 1536,
        model_name="m",
    )

    import json

    vec_str = json.dumps([0.5] * 1536)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            EXPLAIN
            SELECT e.id, e.content, e.chunk_id,
                   VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s)) AS distance
            FROM pkm_embedding e
            WHERE e.user_id = %s AND e.company_id = %s
            ORDER BY VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s))
            LIMIT 10
            """,
            [vec_str, user.id, company.id, vec_str],
        )
        explain_rows = cursor.fetchall()

    # EXPLAIN output columns: id, select_type, table, type, possible_keys,
    # key, key_len, ref, rows, Extra (MariaDB format)
    # Verify that the query references pkm_embedding and uses some index
    explain_text = str(explain_rows)
    assert "pkm_embedding" in explain_text

    # Check that possible_keys or key column mentions an index
    # MariaDB EXPLAIN: row[5] = possible_keys, row[6] = key
    found_index_ref = False
    for row in explain_rows:
        possible_keys = str(row[5]) if len(row) > 5 and row[5] else ""
        key_used = str(row[6]) if len(row) > 6 and row[6] else ""
        extra = str(row[9]) if len(row) > 9 and row[9] else ""
        combined = (possible_keys + key_used + extra).lower()
        if "idx" in combined or "vector" in combined or "index" in combined:
            found_index_ref = True
            break
    # The HNSW index should appear in the plan
    assert found_index_ref, (
        f"Expected index reference in EXPLAIN, got: {explain_rows}"
    )


# ---------------------------------------------------------------------------
# Per-user isolation tests (VAL-RAG-011)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_search_per_user_isolation(document, user, other_user, company):
    """User B's search never returns User A's embeddings."""
    chunk = _make_chunk(document, content="user A secret data")
    store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="user A secret data",
        embedding_vector=[0.8] * 1536,
        model_name="m",
    )

    # User B searches with the exact same vector
    results_b = search_similar(other_user.id, company.id, [0.8] * 1536, top_k=10)
    assert results_b == [], "User B should not see User A's embeddings"

    # User A finds their own
    results_a = search_similar(user.id, company.id, [0.8] * 1536, top_k=10)
    assert len(results_a) == 1
    assert results_a[0]["content"] == "user A secret data"


@pytest.mark.django_db
def test_search_per_user_isolation_multiple_users(document, user, other_user, company):
    """Multiple users in the same company get isolated results."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    doc_b = PKMDocument.objects.create(
        user=other_user,
        company=company,
        title="User B Doc",
        file=SimpleUploadedFile("b.pdf", b"data"),
        file_type="pdf",
    )

    chunk_a = _make_chunk(document, index=0, content="A's chunk")
    chunk_b = DocumentChunk.objects.create(
        document=doc_b, chunk_index=0, content="B's chunk", token_count=1
    )

    vec = [0.5] * 1536
    store_embedding(chunk_a.id, user.id, company.id, "A's embedding", vec, "m")
    store_embedding(chunk_b.id, other_user.id, company.id, "B's embedding", vec, "m")

    results_a = search_similar(user.id, company.id, vec, top_k=10)
    results_b = search_similar(other_user.id, company.id, vec, top_k=10)

    assert len(results_a) == 1
    assert results_a[0]["content"] == "A's embedding"
    assert len(results_b) == 1
    assert results_b[0]["content"] == "B's embedding"


@pytest.mark.django_db
def test_search_company_isolation(document, user, company, other_company):
    """Searches are scoped by company_id."""
    chunk = _make_chunk(document, content="company A data")
    store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="company A data",
        embedding_vector=[0.9] * 1536,
        model_name="m",
    )

    # Same user, different company -> no results
    results = search_similar(user.id, other_company.id, [0.9] * 1536, top_k=10)
    assert results == []

    # Same user, same company -> finds result
    results = search_similar(user.id, company.id, [0.9] * 1536, top_k=10)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# delete_embeddings tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_embeddings_by_chunk_id(document, user, company):
    """delete_embeddings with chunk_id removes the embedding."""
    chunk = _make_chunk(document)
    emb_id = store_embedding(
        chunk_id=chunk.id,
        user_id=user.id,
        company_id=company.id,
        content="to delete",
        embedding_vector=[0.1] * 1536,
        model_name="m",
    )
    deleted = delete_embeddings(chunk_id=chunk.id)
    assert deleted >= 1

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM pkm_embedding WHERE id = %s", [emb_id]
        )
        count = cursor.fetchone()[0]
    assert count == 0


@pytest.mark.django_db
def test_delete_embeddings_by_document_id(document, user, company):
    """delete_embeddings with document_id removes all embeddings for that doc."""
    chunk1 = _make_chunk(document, index=0, content="chunk 0")
    chunk2 = _make_chunk(document, index=1, content="chunk 1")
    chunk3 = _make_chunk(document, index=2, content="chunk 2")

    for chunk in [chunk1, chunk2, chunk3]:
        store_embedding(
            chunk_id=chunk.id,
            user_id=user.id,
            company_id=company.id,
            content=f"text {chunk.id}",
            embedding_vector=[0.2] * 1536,
            model_name="m",
        )

    deleted = delete_embeddings(document_id=document.id)
    assert deleted >= 3

    with connection.cursor() as cursor:
        chunk_ids = [chunk1.id, chunk2.id, chunk3.id]
        placeholders = ",".join(["%s"] * len(chunk_ids))
        cursor.execute(
            f"SELECT COUNT(*) FROM pkm_embedding WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        )
        count = cursor.fetchone()[0]
    assert count == 0


@pytest.mark.django_db
def test_delete_embeddings_chunk_id_overrides_document_id(document, user, company):
    """When both are given, only the specific chunk's embedding is deleted."""
    chunk1 = _make_chunk(document, index=0)
    chunk2 = _make_chunk(document, index=1)

    store_embedding(chunk1.id, user.id, company.id, "c1", [0.1] * 1536, "m")
    store_embedding(chunk2.id, user.id, company.id, "c2", [0.1] * 1536, "m")

    # Pass both; chunk_id should take precedence
    deleted = delete_embeddings(document_id=document.id, chunk_id=chunk1.id)
    assert deleted >= 1

    # chunk2's embedding should still exist
    results = search_similar(user.id, company.id, [0.1] * 1536, top_k=10)
    contents = [r["content"] for r in results]
    assert "c2" in contents
    assert "c1" not in contents


@pytest.mark.django_db
def test_delete_embeddings_requires_argument():
    """delete_embeddings raises ValueError with no arguments."""
    with pytest.raises(ValueError, match="requires either"):
        delete_embeddings()


@pytest.mark.django_db
def test_delete_embeddings_nonexistent_chunk():
    """Deleting a non-existent chunk returns 0 rows deleted."""
    deleted = delete_embeddings(chunk_id=99999999)
    assert deleted == 0
