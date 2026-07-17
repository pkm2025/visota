"""Ensure every TT133 company has a seeded chart of accounts.

Idempotent: skips companies that already have accounts. Designed to be called
from deploy scripts (docker entrypoint, deploy.sh, Makefile seed) so that any
company created before the signup-flow fix (which omitted --company-code and
silently failed) is back-filled automatically.

Usage:
    python manage.py ensure_tt133_charts           # all TT133 companies
    python manage.py ensure_tt133_charts --code PKM  # single company
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.core.models import Company
from apps.master_data.models import ChartOfAccounts


class Command(BaseCommand):
    help = "Ensure every TT133 company has a seeded chart of accounts (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--code",
            help="Only ensure chart for the company with this code (default: all tt133)",
        )

    def handle(self, *args, **options):
        qs = Company.objects.filter(accounting_regime="tt133", is_active=True)
        if options["code"]:
            qs = qs.filter(code=options["code"])

        if not qs.exists():
            self.stdout.write("No TT133 companies found, nothing to do.")
            return

        seeded = 0
        skipped = 0
        failed = 0

        for company in qs:
            existing = ChartOfAccounts.objects.filter(company=company).count()
            if existing >= 100:
                # Already has a full chart (load_tt133 produces ~110).
                skipped += 1
                continue
            try:
                call_command("load_tt133", company_code=company.code, verbosity=0)
                seeded += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {company.code}: seeded TT133 chart ({existing} → "
                        f"{ChartOfAccounts.objects.filter(company=company).count()} accounts)"
                    )
                )
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  {company.code}: FAILED — {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nensure_tt133_charts: {seeded} seeded, {skipped} already had chart, "
                f"{failed} failed"
            )
        )
