"""Management command to export PKM data for a user.

Exports notes (title, content, tags) and wiki pages scoped by ``(user,
company)`` to a file. Supports two formats:

  * ``json`` (default) — a single JSON document.
  * ``md``              — a single Markdown document.

Usage::

    # Export user 1's data (auto-selects their first company) as JSON
    python manage.py export_pkm_data --user 1

    # Export as Markdown
    python manage.py export_pkm_data --user 1 --format md

    # Specify output file path
    python manage.py export_pkm_data --user 1 --output /tmp/pkm_export.json

    # Choose a specific company by code (multi-tenant scope)
    python manage.py export_pkm_data --user 1 --company ACME

Fulfils:
  - VAL-EXPORT-001 (in tandem with the API endpoint): export produces JSON
    with notes (title, content, tags) and wiki pages.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.services.export_service import (
    export_user_pkm_data,
    render_export_markdown,
)

logger = logging.getLogger(__name__)


SUPPORTED_FORMATS = {"json", "md"}


class Command(BaseCommand):
    help = (
        "Export a user's PKM data (notes + wiki pages) as JSON or Markdown. "
        "Scoped by --user and optionally --company. Writes to --output path "
        "or to stdout if no path is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            required=True,
            help="ID of the user whose PKM data should be exported.",
        )
        parser.add_argument(
            "--format",
            type=str,
            default="json",
            choices=sorted(SUPPORTED_FORMATS),
            help="Output format: 'json' (default) or 'md'.",
        )
        parser.add_argument(
            "--company",
            type=str,
            default="",
            help=(
                "Company code to scope the export (multi-tenant). "
                "If omitted, the user's first company is used."
            ),
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help=(
                "Output file path. If omitted, output is written to stdout. "
                "File extension should match --format (.json or .md)."
            ),
        )
        parser.add_argument(
            "--no-notes",
            action="store_true",
            dest="no_notes",
            default=False,
            help="Exclude knowledge notes from the export.",
        )
        parser.add_argument(
            "--no-wiki",
            action="store_true",
            dest="no_wiki",
            default=False,
            help="Exclude wiki pages from the export.",
        )

    def handle(self, *args, **options):
        user_id: int = options["user"]
        fmt: str = options["format"]
        company_code: str = options["company"]
        output_path: str = options["output"]
        include_notes: bool = not options["no_notes"]
        include_wiki: bool = not options["no_wiki"]

        # Resolve the user
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise CommandError(f"User with id={user_id} does not exist.") from exc

        # Resolve the company scope
        company = self._resolve_company(user, company_code)

        # Build the export payload
        payload = export_user_pkm_data(
            user=user,
            company=company,
            include_notes=include_notes,
            include_wiki=include_wiki,
        )

        # Render the output
        if fmt == "json":
            rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        else:  # fmt == "md"
            rendered = render_export_markdown(payload)

        # Write to file or stdout
        if output_path:
            self._write_to_file(output_path, rendered, fmt)
            notes_count = len(payload.get("notes", []))
            wiki_count = len(payload.get("wiki_pages", []))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Exported user='{user.username}' company='{company.code}': "
                    f"{notes_count} note(s), {wiki_count} wiki page(s) "
                    f"to {output_path}"
                )
            )
        else:
            # Write to stdout (use write so Django's test runner captures it).
            # NOTE: we intentionally return None from handle() so Django's
            # BaseCommand.execute() does not write the rendered content a
            # second time.
            self.stdout.write(rendered)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_company(self, user: User, company_code: str) -> Company:
        """Resolve the company scope for the export.

        If ``company_code`` is given, look it up. Otherwise, use the user's
        first company (via UserCompanyRole) or fall back to the first
        company in the database.
        """
        if company_code:
            company = Company.objects.filter(code=company_code).first()
            if company is None:
                raise CommandError(f"Company with code='{company_code}' does not exist.")
            return company

        # No explicit company: use user's first assigned company
        user_company = user.company_roles.select_related("company").order_by("id").first()
        if user_company is not None:
            return user_company.company

        # Fall back to the first company in the database
        company = Company.objects.order_by("id").first()
        if company is None:
            raise CommandError(
                "No company exists in the database. Create a company before exporting."
            )
        return company

    def _write_to_file(self, path: str, content: str, fmt: str) -> None:
        """Write the rendered content to ``path``, creating parent dirs."""
        out = Path(path)
        # Validate extension matches the format (warn, don't fail)
        expected_ext = ".json" if fmt == "json" else ".md"
        if out.suffix.lower() and out.suffix.lower() != expected_ext:
            logger.warning(
                "Output file extension '%s' does not match format '%s'. "
                "Output will still be written in the requested format.",
                out.suffix,
                fmt,
            )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
