"""Data-retention cleanup command for the PKM module.

Purges **ephemeral, high-volume** data only, while preserving the user's
compounding knowledge artifacts (notes, wiki pages, processed documents,
LLM config). The retention policy is:

  =============================== ==================================== ============
  Model                            Filter                               Default
  =============================== ==================================== ============
  ``UserInteractionLog``           ``created_at`` older than N days     90 days
  ``QAHistory``                    ``created_at`` older than N days     180 days
  ``Embedding``                    orphaned (chunk deleted)             n/a
  ``PKMDocument``                  ``status=failed`` older than N days  30 days
  =============================== ==================================== ============

Safety contract
---------------
The following models are **never** touched by this command:

  * ``KnowledgeNote``  (user-authored notes)
  * ``WikiPage``       (the LLM-maintained wiki)
  * ``PKMDocument``    in non-failed states (pending/processing/processed)
  * ``UserLLMConfig``  (per-user LLM configuration)
  * ``Tag``, ``WikiPage``, ``DocumentChunk`` (only cascaded via parents)

Use ``--dry-run`` to preview what would be deleted without committing any
deletions.

Fulfils:
  - VAL-RETENTION-001: Cleanup purges old interaction logs (and other
    ephemeral records), preserving recent data.
  - VAL-RETENTION-002: Dry-run mode reports counts without deleting.

Usage::

    # Preview what would be purged (deletes nothing)
    python manage.py cleanup_pkm_data --dry-run

    # Run cleanup with default thresholds
    python manage.py cleanup_pkm_data

    # Custom thresholds
    python manage.py cleanup_pkm_data \\
        --interaction-days 30 \\
        --qa-days 90 \\
        --failed-doc-days 7
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.pkm.models import (
    PKMDocument,
    QAHistory,
    UserInteractionLog,
)

logger = logging.getLogger(__name__)

# Default retention thresholds (days). Older rows are eligible for purge.
DEFAULT_INTERACTION_DAYS = 90
DEFAULT_QA_DAYS = 180
DEFAULT_FAILED_DOC_DAYS = 30


@dataclass
class PurgeReport:
    """Counts of rows that would be (or were) purged per category."""

    interaction_logs: int = 0
    qa_history: int = 0
    orphaned_embeddings: int = 0
    failed_documents: int = 0

    @property
    def total(self) -> int:
        return (
            self.interaction_logs
            + self.qa_history
            + self.orphaned_embeddings
            + self.failed_documents
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "UserInteractionLog": self.interaction_logs,
            "QAHistory": self.qa_history,
            "Embedding (orphaned)": self.orphaned_embeddings,
            "PKMDocument (failed)": self.failed_documents,
        }


# ---------------------------------------------------------------------------
# Pure query builders (no side effects) - reusable, testable
# ---------------------------------------------------------------------------


def interaction_logs_to_purge(days: int):
    """Return a queryset of UserInteractionLog rows older than ``days``."""
    cutoff = timezone.now() - timedelta(days=days)
    return UserInteractionLog.objects.filter(created_at__lt=cutoff)


def qa_history_to_purge(days: int):
    """Return a queryset of QAHistory rows older than ``days``."""
    cutoff = timezone.now() - timedelta(days=days)
    return QAHistory.objects.filter(created_at__lt=cutoff)


def failed_documents_to_purge(days: int):
    """Return a queryset of failed PKMDocument rows older than ``days``.

    Only ``status=failed`` documents are ever eligible. Documents in
    pending/processing/processed states are **never** purged regardless of
    age - they are user-owned knowledge artifacts.
    """
    cutoff = timezone.now() - timedelta(days=days)
    return PKMDocument.objects.filter(
        status=PKMDocument.Status.FAILED,
        created_at__lt=cutoff,
    )


def compute_purge_report(
    interaction_days: int,
    qa_days: int,
    failed_doc_days: int,
) -> PurgeReport:
    """Compute a PurgeReport of eligible rows without deleting anything."""
    return PurgeReport(
        interaction_logs=interaction_logs_to_purge(interaction_days).count(),
        qa_history=qa_history_to_purge(qa_days).count(),
        orphaned_embeddings=_orphaned_embeddings_count(),
        failed_documents=failed_documents_to_purge(failed_doc_days).count(),
    )


def _orphaned_embeddings_count() -> int:
    """Count Embedding rows whose chunk_id no longer references an existing chunk.

    Uses a raw anti-join to detect orphaned vectors efficiently.
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM pkm_embedding e "
            "LEFT JOIN pkm_documentchunk c ON e.chunk_id = c.id "
            "WHERE c.id IS NULL"
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


def _delete_orphaned_embeddings() -> int:
    """Delete Embedding rows whose chunk no longer exists. Returns count."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "DELETE e FROM pkm_embedding e "
            "LEFT JOIN pkm_documentchunk c ON e.chunk_id = c.id "
            "WHERE c.id IS NULL"
        )
        return cur.rowcount


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Purge old PKM data per the retention policy: "
        "UserInteractionLog > 90 days, QAHistory > 180 days, "
        "orphaned embeddings, failed documents > 30 days. "
        "Safe: never deletes notes, wiki pages, processed documents, or configs. "
        "Use --dry-run to preview."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interaction-days",
            type=int,
            default=DEFAULT_INTERACTION_DAYS,
            help=(
                f"Retention window for UserInteractionLog in days "
                f"(default: {DEFAULT_INTERACTION_DAYS})."
            ),
        )
        parser.add_argument(
            "--qa-days",
            type=int,
            default=DEFAULT_QA_DAYS,
            help=(f"Retention window for QAHistory in days (default: {DEFAULT_QA_DAYS})."),
        )
        parser.add_argument(
            "--failed-doc-days",
            type=int,
            default=DEFAULT_FAILED_DOC_DAYS,
            help=(
                f"Retention window for failed PKMDocument rows in days "
                f"(default: {DEFAULT_FAILED_DOC_DAYS})."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Report what would be purged without deleting anything.",
        )

    def handle(self, *args, **options):
        interaction_days: int = options["interaction_days"]
        qa_days: int = options["qa_days"]
        failed_doc_days: int = options["failed_doc_days"]
        dry_run: bool = options["dry_run"]

        self.stdout.write(
            f"PKM retention cleanup "
            f"(interaction={interaction_days}d, qa={qa_days}d, "
            f"failed-doc={failed_doc_days}d)"
        )

        report = compute_purge_report(
            interaction_days=interaction_days,
            qa_days=qa_days,
            failed_doc_days=failed_doc_days,
        )

        self._print_report(report)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: no data deleted. {report.total} row(s) would be purged."
                )
            )
            return

        # Actually delete.
        deleted = self._execute_purge(
            interaction_days=interaction_days,
            qa_days=qa_days,
            failed_doc_days=failed_doc_days,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Cleanup complete: purged {deleted.total} row(s) total.")
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print_report(self, report: PurgeReport) -> None:
        """Write a human-readable summary of eligible rows."""
        for label, count in report.as_dict().items():
            self.stdout.write(f"  {label}: {count}")

    def _execute_purge(
        self,
        *,
        interaction_days: int,
        qa_days: int,
        failed_doc_days: int,
    ) -> PurgeReport:
        """Execute the deletions inside a transaction and return counts."""
        with transaction.atomic():
            # 1. Old interaction logs
            interactions_qs = interaction_logs_to_purge(interaction_days)
            interactions_deleted, _ = interactions_qs.delete()

            # 2. Old QA history
            qa_qs = qa_history_to_purge(qa_days)
            qa_deleted, _ = qa_qs.delete()

            # 3. Orphaned embeddings (raw SQL anti-join)
            embeddings_deleted = _delete_orphaned_embeddings()

            # 4. Failed documents older than threshold
            docs_qs = failed_documents_to_purge(failed_doc_days)
            docs_deleted, _ = docs_qs.delete()

        report = PurgeReport(
            interaction_logs=interactions_deleted,
            qa_history=qa_deleted,
            orphaned_embeddings=embeddings_deleted,
            failed_documents=docs_deleted,
        )
        logger.info("PKM cleanup purged: %s", report.as_dict())
        return report
