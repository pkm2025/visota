"""Seed Vietnamese regulation documents into the PKM RAG corpus.

Creates system-level ``PKMDocument`` records (``is_system=True``) for the
core regulations used by Visota:

  * TT58/2026/TT-BTC — Chế độ kế toán DNSN
  * PIT/BHXH/CIT/VAT rates (tháng 7/2026)
  * TT133/2016 — Tổng quan hệ thống tài khoản DN nhỏ và vừa
  * NĐ 254/2026 — Hóa đơn điện tử (cơ bản)

Each document is written to a markdown file (so the existing
``doc_parser.extract_text`` path can read it) and chunked via the existing
``chunking_service.split_text`` helper. Chunks are persisted as
``DocumentChunk`` rows so downstream RAG retrieval can use them even before
an embedding model is configured.

Idempotency: documents are keyed by a stable ``slug`` stored in the title
prefix (e.g. ``"[system:tt58-2026]"``). Re-running the command updates the
body and re-chunks existing documents instead of creating duplicates.

System documents are shared across tenants. Because ``PKMDocument.company``
is NOT nullable, the command attaches system documents to the first
``Company`` (or a sentinel ``SYSTEM`` company created on the fly). The owner
``User`` is the first superuser (or the first user overall) so the documents
are always readable to administrators.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.management.commands._regulation_content import REGULATION_DOCUMENTS
from apps.pkm.models import DocumentChunk, PKMDocument
from apps.pkm.services.chunking_service import count_tokens, split_text

logger = logging.getLogger(__name__)

#: Prefix stored in the title to make system documents identifiable and idempotent.
SYSTEM_TITLE_PREFIX = "[system]"

#: Stable slug marker used to look up an existing system document by slug.
SLUG_MARKER = "reg:"


def _system_title(slug: str, title: str) -> str:
    """Build a deterministic, idempotent title for a system regulation doc."""
    return f"{SYSTEM_TITLE_PREFIX} {SLUG_MARKER}{slug} — {title}"


def _extract_slug_from_title(title: str) -> Optional[str]:
    """Return the slug embedded in a system document title, if any."""
    marker = f"{SYSTEM_TITLE_PREFIX} {SLUG_MARKER}"
    if not title.startswith(marker):
        return None
    rest = title[len(marker) :]
    # slug ends at the first " — " separator.
    sep = rest.find(" — ")
    if sep == -1:
        return rest.strip()
    return rest[:sep].strip()


def _resolve_owner() -> User:
    """Return the user that owns system documents.

    Preference order: first active superuser, then any user. Raises
    ``CommandError`` if no user exists (run ``createsuperuser`` first).
    """
    user = User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
    if user is not None:
        return user
    user = User.objects.order_by("id").first()
    if user is None:
        raise CommandError(
            "No user exists in the database. Create a superuser before seeding "
            "system regulation documents (e.g. `python manage.py createsuperuser`)."
        )
    return user


def _resolve_company() -> Company:
    """Return the company that system documents are attached to.

    ``PKMDocument.company`` is NOT nullable, so system (tenant-shared)
    documents are attached to the first existing company. If no company
    exists yet, a sentinel ``SYSTEM`` company is created.
    """
    company = Company.objects.order_by("id").first()
    if company is not None:
        return company
    return Company.objects.create(
        code="SYSTEM",
        name="System Regulation Documents",
        accounting_regime=Company.AccountingRegime.TT133,
    )


def _replace_chunks(document: PKMDocument, body_text: str) -> int:
    """Replace the chunks for ``document`` with a fresh split of ``body_text``.

    Existing chunks are deleted first to keep the document's chunk set in sync
    with the current regulation text (idempotent re-runs). Embeddings, if any,
    are removed via the ORM cascade.

    Returns the number of chunks created.
    """
    document.chunks.all().delete()
    chunks = split_text(body_text)
    created = 0
    for index, chunk_text in enumerate(chunks):
        DocumentChunk.objects.create(
            document=document,
            chunk_index=index,
            content=chunk_text,
            token_count=count_tokens(chunk_text),
        )
        created += 1
    return created


def _checksum(text: str) -> str:
    """Return the SHA-256 checksum of ``text`` (used for dedup metadata)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = (
        "Seed Vietnamese regulation documents (TT58/2026, PIT/BHXH/CIT/VAT rates, "
        "TT133 chart overview, ND254 e-invoice) into the PKM RAG corpus as "
        "system-level documents. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-chunks",
            action="store_true",
            default=False,
            help="Skip creating DocumentChunk rows (only create PKMDocument records).",
        )

    def handle(self, *args, **options):
        skip_chunks: bool = options["no_chunks"]
        owner = _resolve_owner()
        company = _resolve_company()

        created_docs = 0
        updated_docs = 0
        total_chunks = 0

        for slug, title, body in REGULATION_DOCUMENTS:
            full_title = _system_title(slug, title)
            checksum = _checksum(body)
            file_name = f"{slug}.md"

            # Idempotent lookup: find an existing system document by slug marker.
            existing = next(
                (
                    doc
                    for doc in PKMDocument.objects.filter(is_system=True, title=full_title)
                    if _extract_slug_from_title(doc.title) == slug
                ),
                None,
            )

            if existing is None:
                document = PKMDocument.objects.create(
                    user=owner,
                    company=company,
                    title=full_title,
                    file_type="md",
                    file_size=len(body.encode("utf-8")),
                    status=PKMDocument.Status.PROCESSED,
                    checksum=checksum,
                    is_system=True,
                )
                document.file.save(file_name, ContentFile(body.encode("utf-8")), save=True)
                created_docs += 1
                self.stdout.write(f"  + Created system document: {full_title}")
            else:
                document = existing
                # Update body + metadata in place.
                document.checksum = checksum
                document.file_size = len(body.encode("utf-8"))
                document.status = PKMDocument.Status.PROCESSED
                document.error_message = ""
                # Replace the stored file so doc_parser would read the new text.
                document.file.save(file_name, ContentFile(body.encode("utf-8")), save=False)
                document.save(
                    update_fields=[
                        "checksum",
                        "file_size",
                        "status",
                        "error_message",
                        "file",
                        "updated_at",
                    ]
                )
                updated_docs += 1
                self.stdout.write(f"  ~ Updated system document: {full_title}")

            if not skip_chunks:
                created_chunks = _replace_chunks(document, body)
                total_chunks += created_chunks
                self.stdout.write(f"    -> {created_chunks} chunk(s) stored")

        summary = (
            f"Seeded {len(REGULATION_DOCUMENTS)} regulation document(s) "
            f"({created_docs} new, {updated_docs} updated"
            + (f", {total_chunks} chunks" if not skip_chunks else ", chunks skipped")
            + f") owned by user='{owner.username}' company='{company.code}'."
        )
        self.stdout.write(self.style.SUCCESS(summary))
        return summary
