"""Shared helpers for role-based note template queries.

Role-based templates are shared ``KnowledgeNote`` records owned by a system
user and tagged with ``role_context`` matching Visota role codes. They are
distinguished from regular user notes by the ``[mẫu]`` title prefix
(``TEMPLATE_TITLE_PREFIX`` in ``_role_template_content``).

This module provides the single source of truth for resolving which
notes/templates to show a user in the PKM dashboard's role-based
suggestions, so the UI view and the stats API stay consistent.
"""

from __future__ import annotations

from typing import Iterable

from django.db.models import QuerySet

from apps.core.models import Company
from apps.identity.models import User, UserCompanyRole
from apps.pkm.management.commands._role_template_content import (
    TEMPLATE_TITLE_PREFIX,
)
from apps.pkm.models import KnowledgeNote


def get_user_role_codes(*, user: User, company: Company) -> list[str]:
    """Return the role codes the user has in ``company``."""
    return list(
        UserCompanyRole.objects.filter(user=user, company=company).values_list(
            "role__code", flat=True
        )
    )


def get_role_template_queryset(
    *,
    company: Company,
    role_codes: Iterable[str],
) -> QuerySet[KnowledgeNote]:
    """Return shared role template notes for ``role_codes`` in ``company``.

    These are company-scoped notes whose ``role_context`` matches one of
    ``role_codes`` AND whose title starts with the template prefix. They
    are visible to any user with the matching role, regardless of owner.
    Returns an empty queryset if ``role_codes`` is empty.
    """
    codes = [c for c in role_codes if c]
    if not codes:
        return KnowledgeNote.objects.none()
    return (
        KnowledgeNote.objects.filter(company=company, role_context__in=codes)
        .filter(title__startswith=TEMPLATE_TITLE_PREFIX)
        .order_by("-is_pinned", "-updated_at")
    )


def get_role_suggestions_queryset(
    *,
    user: User,
    company: Company,
    role_codes: Iterable[str] | None = None,
) -> QuerySet[KnowledgeNote]:
    """Return role-based suggestion notes for ``user`` in ``company``.

    Combines:
      - The user's own notes whose ``role_context`` matches their roles.
      - Shared role template notes (any owner) in the company whose
        ``role_context`` matches the user's roles.

    Returns an empty queryset if the user has no role codes.
    """
    if role_codes is None:
        role_codes = get_user_role_codes(user=user, company=company)
    codes = [c for c in role_codes if c]
    if not codes:
        return KnowledgeNote.objects.none()

    own_role_notes = KnowledgeNote.objects.filter(
        user=user, company=company, role_context__in=codes
    )
    shared_templates = KnowledgeNote.objects.filter(
        company=company,
        role_context__in=codes,
        title__startswith=TEMPLATE_TITLE_PREFIX,
    )
    return (own_role_notes | shared_templates).order_by("-is_pinned", "-updated_at")
