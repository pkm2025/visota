"""Signal handlers for PKM interaction logging.

This module connects ``post_save`` signals for ``KnowledgeNote`` and
``PKMDocument`` to log ``note_create`` and ``document_create`` interactions
respectively. The logging is non-blocking: all errors are swallowed so that
interaction capture can NEVER break the main operation (VAL-CAP-009).

Signal handlers only fire on *new* object creation (``created=True``), not
on updates, to avoid duplicate interaction logs for edits/status changes.
"""

from __future__ import annotations

import logging

from django.db.models import Model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.pkm.models import KnowledgeNote, PKMDocument
from apps.pkm.services.interaction_service import log_interaction

logger = logging.getLogger(__name__)

__all__ = [
    "log_note_create",
    "log_document_create",
]


@receiver(post_save, sender=KnowledgeNote)
def log_note_create(
    sender: type[Model],
    instance: KnowledgeNote,
    created: bool,
    **kwargs: object,
) -> None:
    """Log a ``note_create`` interaction when a new note is created.

    Only fires on creation (not updates) to avoid duplicate logs. Wrapped in
    ``try/except`` so logging failures never break the note save operation.
    """
    if not created:
        return
    try:
        log_interaction(
            user=instance.user,
            company=instance.company,
            interaction_type="note_create",
            module="pkm",
            entity_type="note",
            entity_id=str(instance.pk),
            metadata={"title": instance.title},
        )
    except Exception:
        logger.debug(
            "log_note_create: failed to log note_create for note %s — "
            "interaction logging is non-blocking.",
            getattr(instance, "pk", None),
            exc_info=True,
        )


@receiver(post_save, sender=PKMDocument)
def log_document_create(
    sender: type[Model],
    instance: PKMDocument,
    created: bool,
    **kwargs: object,
) -> None:
    """Log a ``document_create`` interaction when a new document is uploaded.

    Only fires on creation (not status updates) to avoid duplicate logs.
    Wrapped in ``try/except`` so logging failures never break the upload.
    """
    if not created:
        return
    try:
        log_interaction(
            user=instance.user,
            company=instance.company,
            interaction_type="document_create",
            module="pkm",
            entity_type="document",
            entity_id=str(instance.pk),
            metadata={
                "title": instance.title,
                "file_type": instance.file_type,
                "file_size": instance.file_size,
            },
        )
    except Exception:
        logger.debug(
            "log_document_create: failed to log document_create for "
            "document %s — interaction logging is non-blocking.",
            getattr(instance, "pk", None),
            exc_info=True,
        )
