"""Management command to run the PKM wiki lint (health check).

Runs all lint checks (orphan pages, contradictions, stale pages, missing
concepts) for one or all tenants and generates the health report page.

Usage::

    # Lint for a specific user+company
    python manage.py lint_pkm_wiki --user <user_id> --company <company_id>

    # Lint for all users that have wiki pages
    python manage.py lint_pkm_wiki --all

    # Dry-run: report findings without persisting the health report
    python manage.py lint_pkm_wiki --all --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import WikiPage
from apps.pkm.services.wiki_lint_service import (
    find_contradictions,
    find_missing_concept_pages,
    find_orphan_pages,
    find_stale_pages,
    generate_health_report,
)


class Command(BaseCommand):
    help = (
        "Run the PKM wiki lint (health check): detect orphan pages, "
        "potential contradictions, stale pages, and missing concept pages. "
        "Generates a health report WikiPage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            default=None,
            help="User ID whose wiki to lint (required if --all not given).",
        )
        parser.add_argument(
            "--company",
            type=int,
            default=None,
            help="Company ID scope (required if --all not given).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_tenants",
            default=False,
            help="Lint wiki pages for every (user, company) pair that has pages.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Report findings without generating the health report page.",
        )

    def handle(self, *args, **options):
        all_tenants: bool = options["all_tenants"]
        dry_run: bool = options["dry_run"]

        if all_tenants:
            tenants = self._all_tenants()
        else:
            user_id = options.get("user")
            company_id = options.get("company")
            if user_id is None or company_id is None:
                raise CommandError(
                    "Provide --user <id> and --company <id>, or use --all to lint all tenants."
                )
            tenants = [(user_id, company_id)]

        if not tenants:
            self.stdout.write("No wiki pages found. Nothing to lint.")
            return

        total_summary_parts: list[str] = []

        for user_id, company_id in tenants:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist as exc:
                raise CommandError(f"User {user_id} not found.") from exc
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist as exc:
                raise CommandError(f"Company {company_id} not found.") from exc

            label = f"user='{user.username}' company='{company.code}'"
            self.stdout.write(f"\nLinting wiki for {label}:")

            orphans = find_orphan_pages(user, company)
            contradictions = find_contradictions(user, company)
            stale = find_stale_pages(user, company)
            missing = find_missing_concept_pages(user, company)

            self._print_findings(orphans, contradictions, stale, missing)

            if not dry_run:
                findings = {
                    "orphans": orphans,
                    "contradictions": contradictions,
                    "stale": stale,
                    "missing_concepts": missing,
                }
                report = generate_health_report(user, company, findings=findings)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  -> Health report generated: '{report.title}' (id={report.id})"
                    )
                )

            total_summary_parts.append(
                f"{label}: {len(orphans)} orphan(s), {len(contradictions)} "
                f"contradiction(s), {len(stale)} stale, {len(missing)} missing"
            )

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no health report persisted."))
        self.stdout.write(self.style.SUCCESS(f"Linted {len(tenants)} tenant(s)."))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _all_tenants(self) -> list[tuple[int, int]]:
        """Return distinct (user_id, company_id) pairs that have wiki pages."""
        return list(WikiPage.objects.values_list("user_id", "company_id").distinct())

    def _print_findings(self, orphans, contradictions, stale, missing) -> None:
        """Write a human-readable summary of findings to stdout."""
        self.stdout.write(f"  Orphan pages ({len(orphans)}):")
        for p in orphans:
            self.stdout.write(f"    - {p.title} ({p.page_type})")

        self.stdout.write(f"  Potential contradictions ({len(contradictions)}):")
        for c in contradictions:
            titles = " | ".join(p.title for p in c["pages"])
            self.stdout.write(f"    - {titles} -- {c['reason']}")

        self.stdout.write(f"  Stale pages ({len(stale)}):")
        for p in stale:
            ts = p.last_ingest_at.strftime("%Y-%m-%d") if p.last_ingest_at else "?"
            self.stdout.write(f"    - {p.title} (last ingested {ts})")

        self.stdout.write(f"  Missing concept pages ({len(missing)}):")
        for title in missing:
            self.stdout.write(f"    - [[{title}]]")
