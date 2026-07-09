"""Interaction logging and smart-context summary service for the PKM module.

This module provides three public functions:

  - ``log_interaction`` - Captures a user interaction as a ``UserInteractionLog``
    row. When django-q2 is available, the insert is enqueued asynchronously so
    the caller (e.g. a view or middleware) is never blocked. If django-q2 is
    unavailable or the enqueue fails, it falls back to a synchronous insert.
    Any exception during logging is swallowed so that interaction capture can
    NEVER break the main user operation.

  - ``get_context_summary`` - Builds a human-readable summary of a user's
    recent activity (e.g. "Recently viewed 3 ledger pages, created 2 notes").
    Used to enrich Q&A prompts with interaction context.

  - ``get_recent_interactions`` - Returns a queryset of recent interaction
    logs scoped by user + company, ordered by ``created_at`` descending.

All queries are scoped by ``user_id`` and ``company_id`` to enforce per-user
and multi-tenant isolation.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Count
from django.utils import timezone

from apps.pkm.models import UserInteractionLog

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "log_interaction",
    "get_context_summary",
    "get_recent_interactions",
    "DEFAULT_SUMMARY_HOURS",
    "DEFAULT_RECENT_LIMIT",
]

#: Default time window (in hours) for the activity summary.
DEFAULT_SUMMARY_HOURS: int = 24

#: Default maximum number of recent interactions returned by ``get_recent_interactions``.
DEFAULT_RECENT_LIMIT: int = 20

#: Human-readable labels for each interaction type, used in the summary.
INTERACTION_LABELS: dict[str, str] = {
    "page_view": "page views",
    "search": "searches",
    "note_create": "notes created",
    "document_create": "documents uploaded",
    "voucher_create": "vouchers created",
}

#: Module-specific labels for page views (nicer summaries).
MODULE_PAGE_LABELS: dict[str, str] = {
    "ledger": "ledger pages",
    "pkm": "PKM pages",
    "sales": "sales pages",
    "purchasing": "purchasing pages",
    "inventory": "inventory pages",
    "hr": "HR pages",
    "reporting": "reporting pages",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _django_q_available() -> bool:
    """Return True if django-q2 can actually execute tasks in this process.

    A common production bug: django-q2 is importable and ``async_task``
    successfully enqueues a row to the ORM broker, but no worker process is
    running to dequeue and execute it. The enqueue call does not raise, so
    the naive "library is importable" check silently swallows the interaction
    log - it sits in ``django_q_ormq`` forever and is never turned into a
    ``UserInteractionLog`` row.

    This helper returns True only when the task will actually run. We consider
    it available when EITHER:

      1. ``Q_CLUSTER['sync']`` is True (django-q2 runs the task inline during
         the ``async_task`` call - no separate worker needed). This is the
         configuration used by the test and dev settings.
      2. ``Q_CLUSTER['sync']`` is False AND there is evidence that a django-q
         worker is actively processing tasks (at least one row in
         ``django_q_task`` or ``django_q_success`` with a recent timestamp).
         This detects a live worker in production.

    Returns False (so the caller falls back to ``_create_sync``) when:
      - django-q2 is not importable, OR
      - the cluster is async but no worker activity is detected (the dev
        server runs without a ``qcluster`` process, so enqueued tasks would
        never be processed).
    """
    try:
        import django_q.tasks  # noqa: F401
    except ImportError:
        return False

    from django.conf import settings

    cluster = getattr(settings, "Q_CLUSTER", {}) or {}
    if cluster.get("sync"):
        # Sync mode runs the task inline during async_task - always reliable.
        return True

    # Async mode: only advertise availability if a worker is actively running.
    # We probe the django-q bookkeeping tables for evidence of recent worker
    # activity. If neither table has any rows, no worker has ever processed a
    # task in this database, so enqueueing would silently no-op.
    return _worker_is_active()


def _worker_is_active() -> bool:
    """Detect whether a django-q worker is currently processing tasks.

    Probes the django-q bookkeeping tables for evidence of worker activity.
    Used by :func:`_django_q_available` to decide whether async enqueueing is
    safe. Returns True only when there is concrete evidence that a worker has
    processed at least one task in this database.

    The check is intentionally cheap (single indexed COUNT/SELECT) so it can
    run on every ``log_interaction`` call without measurable overhead.
    """
    try:
        from django_q.models import OrmQueue, Success, Task  # noqa: F401
    except Exception:
        return False

    try:
        # A running worker populates Success (completed tasks) or Task
        # (in-flight/failed tasks). If both are empty, no worker has ever run.
        return bool(Success.objects.exists() or Task.objects.exists())
    except Exception:
        # Tables not migrated yet or DB error - treat as no worker.
        return False


def _enqueue_async(
    user: User,
    company: Company,
    interaction_type: str,
    module: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any],
) -> Any:
    """Enqueue a synchronous log-creation task via django-q2's ``async_task``.

    The task target is ``_create_sync`` (imported by string path) so django-q2
    workers can resolve it. Raises if the enqueue itself fails (the caller is
    responsible for fallback).
    """
    from django_q.tasks import async_task

    return async_task(
        "apps.pkm.services.interaction_service._create_sync",
        user.id,
        company.id,
        interaction_type,
        module,
        entity_type,
        entity_id,
        metadata,
    )


def _create_sync(
    user_id: int,
    company_id: int,
    interaction_type: str,
    module: str,
    entity_type: str = "",
    entity_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> UserInteractionLog | None:
    """Create a ``UserInteractionLog`` row synchronously.

    This function is also the target of ``async_task`` (called by django-q2
    workers), so it accepts IDs rather than model instances to stay
    serializable across the task broker.

    Returns the created instance, or ``None`` if creation fails.
    """
    try:
        from apps.core.models import Company
        from apps.identity.models import User

        return UserInteractionLog.objects.create(
            user=User.objects.get(pk=user_id),
            company=Company.objects.get(pk=company_id),
            interaction_type=interaction_type,
            module=module,
            entity_type=entity_type or "",
            entity_id=str(entity_id) if entity_id else "",
            metadata=metadata if metadata is not None else {},
        )
    except Exception:
        logger.exception(
            "interaction_service._create_sync: failed to log interaction "
            "(user=%s, company=%s, type=%s, module=%s)",
            user_id,
            company_id,
            interaction_type,
            module,
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def log_interaction(
    user: User,
    company: Company,
    interaction_type: str,
    module: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UserInteractionLog | None:
    """Log a user interaction, preferring async insertion for non-blocking behaviour.

    Behaviour:
      1. If django-q2 is available, the insert is enqueued via ``async_task``
         so the caller returns immediately (non-blocking).
      2. If django-q2 is unavailable OR the enqueue raises, fall back to a
         synchronous insert.
      3. If the synchronous insert also fails, the exception is logged and
         ``None`` is returned. Interaction logging NEVER raises to the caller,
         because it must not break the main user operation (e.g. a page load
         or note creation).

    Args:
        user: The user performing the interaction.
        company: The user's current company (multi-tenant scope).
        interaction_type: One of ``UserInteractionLog.InteractionType`` values
            (e.g. ``"page_view"``, ``"search"``, ``"note_create"``).
        module: The Visota module where the interaction occurred
            (e.g. ``"ledger"``, ``"pkm"``).
        entity_type: Optional entity type label (e.g. ``"note"``).
        entity_id: Optional entity identifier as a string.
        metadata: Optional free-form JSON metadata (e.g. ``{"query": "VAT"}``).

    Returns:
        The created ``UserInteractionLog`` instance (sync path), or ``None``
        if the async path was used or creation failed.
    """
    etype = entity_type or ""
    eid = str(entity_id) if entity_id else ""
    meta = metadata if metadata is not None else {}

    # Try the non-blocking async path first
    if _django_q_available():
        try:
            _enqueue_async(user, company, interaction_type, module, etype, eid, meta)
            return None  # async path does not return a model instance
        except Exception:
            logger.warning(
                "log_interaction: async enqueue failed, falling back to sync "
                "(user=%s, type=%s, module=%s)",
                getattr(user, "id", user),
                interaction_type,
                module,
                exc_info=True,
            )
            # Fall through to sync path

    # Synchronous fallback - never raise to the caller
    try:
        return _create_sync(
            user_id=user.id,
            company_id=company.id,
            interaction_type=interaction_type,
            module=module,
            entity_type=etype,
            entity_id=eid,
            metadata=meta,
        )
    except Exception:
        logger.exception(
            "log_interaction: synchronous create failed "
            "(user=%s, type=%s, module=%s)",
            getattr(user, "id", user),
            interaction_type,
            module,
        )
        return None


def get_recent_interactions(
    user: User,
    company: Company,
    limit: int = DEFAULT_RECENT_LIMIT,
) -> Any:
    """Return recent interaction logs for a user within a company.

    The queryset is scoped by ``user`` + ``company`` (per-user and
    multi-tenant isolation) and ordered by ``created_at`` descending (most
    recent first), leveraging the model's default ordering.

    Args:
        user: The user whose interactions to retrieve.
        company: The company scope.
        limit: Maximum number of records to return (default 20).

    Returns:
        A queryset of ``UserInteractionLog`` instances (not yet evaluated).
    """
    return (
        UserInteractionLog.objects.filter(user=user, company=company)
        .order_by("-created_at")[:limit]
    )


def _format_page_views(page_view_modules: dict[str, int]) -> str | None:
    """Format the page-view portion of the summary.

    Returns a string like "viewed 3 ledger pages, 2 PKM pages" or ``None``
    if there are no page views.
    """
    if not page_view_modules:
        return None
    module_parts = []
    for mod, cnt in sorted(page_view_modules.items()):
        label = MODULE_PAGE_LABELS.get(mod, f"{mod} pages")
        module_parts.append(f"{cnt} {label}")
    return "viewed " + ", ".join(module_parts)


def _format_interaction(itype: str, count: int) -> str | None:
    """Format a non-page-view interaction into a readable fragment.

    Returns ``None`` if the interaction type is not one of the known types.
    """
    if itype == "note_create":
        return f"created {count} note" + ("s" if count != 1 else "")
    if itype == "document_create":
        return f"uploaded {count} document" + ("s" if count != 1 else "")
    if itype == "search":
        return f"performed {count} search" + ("es" if count != 1 else "")
    if itype == "voucher_create":
        return f"created {count} voucher" + ("s" if count != 1 else "")
    return None


def get_context_summary(
    user: User,
    company: Company,
    hours: int = DEFAULT_SUMMARY_HOURS,
) -> str:
    """Build a human-readable summary of the user's recent activity.

    Aggregates interaction logs within the given time window by interaction
    type and produces a sentence such as::

        "Recently: viewed 3 ledger pages, created 2 notes, uploaded 1 document."

    If no activity is recorded in the window, returns a message indicating
    no recent activity.

    Args:
        user: The user whose activity to summarise.
        company: The company scope.
        hours: Time window in hours (default 24).

    Returns:
        A human-readable summary string.
    """
    cutoff = timezone.now() - datetime.timedelta(hours=hours)

    # Aggregate counts per interaction_type within the window
    qs = UserInteractionLog.objects.filter(
        user=user,
        company=company,
        created_at__gte=cutoff,
    )

    counts_by_type: dict[str, int] = {}
    page_view_modules: dict[str, int] = {}

    for row in qs.values("interaction_type", "module").annotate(count=Count("id")):
        itype = row["interaction_type"]
        module = row["module"]
        count = row["count"]
        counts_by_type[itype] = counts_by_type.get(itype, 0) + count
        if itype == "page_view":
            page_view_modules[module] = page_view_modules.get(module, 0) + count

    if not counts_by_type:
        return "No recent activity in the last %d hours." % hours

    parts: list[str] = []

    # Page views: break down by module for a richer summary
    page_fragment = _format_page_views(page_view_modules) if "page_view" in counts_by_type else None
    if page_fragment:
        parts.append(page_fragment)

    # Non-page-view interactions in a stable order
    type_order = ["note_create", "document_create", "search", "voucher_create"]
    handled = {"page_view"} | set(type_order)
    for itype in type_order:
        if itype in counts_by_type:
            fragment = _format_interaction(itype, counts_by_type[itype])
            if fragment:
                parts.append(fragment)

    # Include any interaction types not explicitly handled above
    for itype, count in counts_by_type.items():
        if itype not in handled:
            label = INTERACTION_LABELS.get(itype, itype)
            parts.append(f"{count} {label}")

    if not parts:
        return "No recent activity in the last %d hours." % hours

    return "Recently: " + ", ".join(parts) + "."
