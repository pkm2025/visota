"""Seed role-based note templates into the PKM corpus.

Creates shared, pinned ``KnowledgeNote`` records (``is_pinned=True``) with
``role_context`` matching the role codes used by Visota:

  * ``accountant``  — quy trình ghi sổ, đối chiếu công nợ
  * ``sales``       — quy trình xuất hóa đơn, theo dõi công nợ
  * ``hr_officer``  — quy trình tính lương, kê khai BHXH
  * ``viewer``      — cách đọc báo cáo tài chính

Each template is owned by the first superuser (or the first user overall)
and attached to the first ``Company`` (or a sentinel ``SYSTEM`` company
created on the fly). Templates are **shared** — every user whose
``UserCompanyRole.role__code`` matches the note's ``role_context`` sees
them in the PKM dashboard's role-based suggestions, regardless of who
owns the note.

Idempotency: templates are keyed by a stable ``slug`` stored in the title
prefix (e.g. ``"[mẫu] tpl:accountant-ghi-so-cuoi-thang — ..."``). Re-running
the command updates the body of existing templates instead of creating
duplicates.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.management.commands._role_template_content import (
    ROLE_TEMPLATES,
    SLUG_MARKER,
    TEMPLATE_TITLE_PREFIX,
)
from apps.pkm.models import KnowledgeNote

logger = logging.getLogger(__name__)


def _template_title(slug: str, title: str) -> str:
    """Build a deterministic, idempotent title for a role template note."""
    return f"{TEMPLATE_TITLE_PREFIX} {SLUG_MARKER}{slug} — {title}"


def _extract_slug_from_title(title: str) -> Optional[str]:
    """Return the slug embedded in a template note title, if any."""
    marker = f"{TEMPLATE_TITLE_PREFIX} {SLUG_MARKER}"
    if not title.startswith(marker):
        return None
    rest = title[len(marker) :]
    sep = rest.find(" — ")
    if sep == -1:
        return rest.strip()
    return rest[:sep].strip()


def _resolve_owner() -> User:
    """Return the user that owns shared template notes.

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
            "role-based note templates (e.g. `python manage.py createsuperuser`)."
        )
    return user


def _resolve_company() -> Company:
    """Return the company that shared templates are attached to.

    ``KnowledgeNote.company`` is NOT nullable, so shared templates are
    attached to the first existing company. If no company exists yet, a
    sentinel ``SYSTEM`` company is created.
    """
    company = Company.objects.order_by("id").first()
    if company is not None:
        return company
    return Company.objects.create(
        code="SYSTEM",
        name="System Shared Templates",
        accounting_regime=Company.AccountingRegime.TT133,
    )


class Command(BaseCommand):
    help = (
        "Seed role-based note templates (accountant, sales, hr_officer, viewer) "
        "as shared, pinned KnowledgeNote records with role_context matching "
        "Visota role codes. Idempotent."
    )

    def handle(self, *args, **options):
        owner = _resolve_owner()
        company = _resolve_company()

        created_notes = 0
        updated_notes = 0

        for role_code, slug, title, body in ROLE_TEMPLATES:
            full_title = _template_title(slug, title)

            # Idempotent lookup: find an existing template note by slug marker.
            existing = next(
                (
                    note
                    for note in KnowledgeNote.objects.filter(
                        user=owner,
                        company=company,
                        title=full_title,
                    )
                    if _extract_slug_from_title(note.title) == slug
                ),
                None,
            )

            if existing is None:
                KnowledgeNote.objects.create(
                    user=owner,
                    company=company,
                    title=full_title,
                    content=body,
                    role_context=role_code,
                    is_pinned=True,
                )
                created_notes += 1
                self.stdout.write(f"  + Created template ({role_code}): {full_title}")
            else:
                existing.content = body
                existing.role_context = role_code
                existing.is_pinned = True
                existing.save(
                    update_fields=[
                        "content",
                        "role_context",
                        "is_pinned",
                        "updated_at",
                    ]
                )
                updated_notes += 1
                self.stdout.write(f"  ~ Updated template ({role_code}): {full_title}")

        roles = sorted({role for role, *_ in ROLE_TEMPLATES})
        summary = (
            f"Seeded {len(ROLE_TEMPLATES)} role template(s) "
            f"({created_notes} new, {updated_notes} updated) for roles "
            f"{roles} owned by user='{owner.username}' company='{company.code}'."
        )
        self.stdout.write(self.style.SUCCESS(summary))
        return summary
