"""Seed role-based note templates into the PKM corpus for ALL companies.

Creates shared, pinned ``KnowledgeNote`` records (``is_pinned=True``) with
``role_context`` matching the role codes used by Visota:

  * ``accountant``  — quy trình ghi sổ, đối chiếu công nợ
  * ``sales``       — quy trình xuất hóa đơn, theo dõi công nợ
  * ``hr_officer``  — quy trình tính lương, kê khai BHXH
  * ``viewer``      — cách đọc báo cáo tài chính

Multi-company seeding
---------------------
Templates are seeded for **every** ``Company`` in the database (not just the
first one), so each tenant gets its own copy of the role templates. This
closes the multi-company gap where only the first company received
templates. When no companies exist, a sentinel ``SYSTEM`` company is
created on the fly so the command is still usable on a fresh database.

Each template is owned by the first superuser (or the first user overall)
within that company's scope. Templates are **shared** — every user whose
``UserCompanyRole.role__code`` matches the note's ``role_context`` sees
them in the PKM dashboard's role-based suggestions, regardless of who owns
the note.

Idempotency
-----------
Templates are keyed by the stable ``slug`` embedded in the title prefix
(e.g. ``"[mẫu] tpl:accountant-ghi-so-cuoi-thang — ..."``) **per company**.
Re-running the command updates the body of existing templates instead of
creating duplicates. The natural key is ``(company, role_context, title)``.
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


def _ensure_company_exists() -> Company:
    """Return the first company, creating a sentinel SYSTEM company if none exist.

    ``KnowledgeNote.company`` is NOT nullable, so on a fresh database we
    create a sentinel ``SYSTEM`` company to host the shared templates.
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
        "Visota role codes. Seeds templates for ALL companies. Idempotent "
        "per (company, role_context, title)."
    )

    def handle(self, *args, **options):
        owner = _resolve_owner()

        # Ensure at least one company exists (creates SYSTEM sentinel if needed).
        _ensure_company_exists()

        companies = list(Company.objects.order_by("id"))
        total_created = 0
        total_updated = 0

        per_company_reports: list[str] = []

        for company in companies:
            created, updated = self._seed_for_company(owner, company)
            total_created += created
            total_updated += updated
            per_company_reports.append(
                f"  company='{company.code}': {created} new, {updated} updated"
            )

        roles = sorted({role for role, *_ in ROLE_TEMPLATES})
        per_template_count = len(ROLE_TEMPLATES)
        summary = (
            f"Seeded {per_template_count} role template(s) per company "
            f"({total_created} new, {total_updated} updated) across "
            f"{len(companies)} company(ies) for roles {roles}."
        )

        for line in per_company_reports:
            self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS(summary))
        return summary

    # ------------------------------------------------------------------
    # Per-company seeding helper
    # ------------------------------------------------------------------

    def _seed_for_company(self, owner: User, company: Company) -> tuple[int, int]:
        """Seed all role templates for a single company.

        Returns ``(created_count, updated_count)``. Idempotent per
        ``(company, title)`` via the slug marker in the title.
        """
        created = 0
        updated = 0

        for role_code, slug, title, body in ROLE_TEMPLATES:
            full_title = _template_title(slug, title)

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
                created += 1
                self.stdout.write(
                    f"  + Created template ({role_code}) company='{company.code}': {full_title}"
                )
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
                updated += 1
                self.stdout.write(
                    f"  ~ Updated template ({role_code}) company='{company.code}': {full_title}"
                )

        return created, updated
