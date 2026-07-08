"""MariaDB VECTOR operations for the PKM module.

All operations use raw SQL via ``django.db.connection`` because Django's ORM
cannot express MariaDB's native ``VECTOR(1536)`` type. Vectors are serialized
with ``json.dumps`` and inserted/searched using ``VEC_FromText()``.

Functions
---------
- ``store_embedding``      -- INSERT a single embedding row
- ``search_similar``       -- cosine similarity search (HNSW-indexed)
- ``delete_embeddings``    -- DELETE by document or chunk
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import connection

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 1536


def store_embedding(
    chunk_id: int,
    user_id: int,
    company_id: int,
    content: str,
    embedding_vector: list[float],
    model_name: str,
) -> int:
    """Insert a single embedding row into ``pkm_embedding``.

    Parameters
    ----------
    chunk_id:
        FK to ``pkm_documentchunk.id``.
    user_id:
        Owning user (per-user isolation).
    company_id:
        Owning company (multi-tenant isolation).
    content:
        Cached text that was embedded.
    embedding_vector:
        List of floats (length must match ``EMBEDDING_DIMENSIONS``).
    model_name:
        Name of the embedding model used (e.g. ``text-embedding-3-small``).

    Returns
    -------
    int
        The ``lastrowid`` (primary key) of the newly inserted row.
    """
    vec_str = json.dumps(embedding_vector)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pkm_embedding
                (chunk_id, user_id, company_id, content, embedding, model_name, created_at)
            VALUES (%s, %s, %s, %s, VEC_FromText(%s), %s, NOW())
            """,
            [chunk_id, user_id, company_id, content, vec_str, model_name],
        )
        return int(cursor.lastrowid)


def search_similar(
    user_id: int,
    company_id: int,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Return the top-k most similar embeddings for a user/company.

    Uses ``VEC_DISTANCE_COSINE`` with a bare ``ORDER BY`` so the HNSW
    vector index is used. Results are filtered by ``user_id`` and
    ``company_id`` to enforce per-user and multi-tenant isolation.

    Parameters
    ----------
    user_id:
        The user to scope the search to.
    company_id:
        The company to scope the search to.
    query_embedding:
        List of floats representing the query vector.
    top_k:
        Maximum number of results to return (default 10).

    Returns
    -------
    list[dict]
        Each dict has keys ``id``, ``content``, ``chunk_id``, ``distance``.
        Results are ordered by ascending cosine distance (most similar first).
    """
    vec_str = json.dumps(query_embedding)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT e.id, e.content, e.chunk_id,
                   VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s)) AS distance
            FROM pkm_embedding e
            WHERE e.user_id = %s AND e.company_id = %s
            ORDER BY VEC_DISTANCE_COSINE(e.embedding, VEC_FromText(%s))
            LIMIT %s
            """,
            [vec_str, user_id, company_id, vec_str, top_k],
        )
        rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "content": row[1],
            "chunk_id": row[2],
            "distance": float(row[3]) if row[3] is not None else None,
        }
        for row in rows
    ]


def delete_embeddings(
    document_id: int | None = None,
    chunk_id: int | None = None,
) -> int:
    """Delete embedding rows by ``chunk_id`` or ``document_id``.

    If both ``chunk_id`` and ``document_id`` are provided, ``chunk_id`` takes
    precedence (more specific). At least one must be provided.

    Parameters
    ----------
    document_id:
        Delete all embeddings belonging to chunks of this document.
    chunk_id:
        Delete all embeddings for this specific chunk.

    Returns
    -------
    int
        Number of rows deleted.
    """
    if chunk_id is not None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM pkm_embedding WHERE chunk_id = %s",
                [chunk_id],
            )
            return int(cursor.rowcount)

    if document_id is not None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM pkm_embedding
                WHERE chunk_id IN (
                    SELECT id FROM pkm_documentchunk WHERE document_id = %s
                )
                """,
                [document_id],
            )
            return int(cursor.rowcount)

    raise ValueError("delete_embeddings requires either document_id or chunk_id")
