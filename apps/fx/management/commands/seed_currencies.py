"""Seed ISO 4217 currencies for the FX module.

Fixes bug #8: /fx/rates/new/ form's "Ngoại tệ" dropdown was empty
because the Currency table had no rows.

Usage:
    python manage.py seed_currencies
"""

from django.core.management.base import BaseCommand

from apps.fx.models import Currency

# (code, name, symbol, decimals)
_CURRENCIES = [
    ("USD", "US Dollar", "$", 2),
    ("EUR", "Euro", "€", 2),
    ("JPY", "Japanese Yen", "¥", 0),
    ("GBP", "British Pound", "£", 2),
    ("CNY", "Chinese Yuan", "¥", 2),
    ("SGD", "Singapore Dollar", "S$", 2),
    ("AUD", "Australian Dollar", "A$", 2),
    ("KRW", "Korean Won", "₩", 0),
    ("THB", "Thai Baht", "฿", 2),
    ("CAD", "Canadian Dollar", "C$", 2),
    ("CHF", "Swiss Franc", "Fr", 2),
    ("HKD", "Hong Kong Dollar", "HK$", 2),
    ("NZD", "New Zealand Dollar", "NZ$", 2),
    ("INR", "Indian Rupee", "₹", 2),
    ("MYR", "Malaysian Ringgit", "RM", 2),
    ("PHP", "Philippine Peso", "₱", 2),
    ("TWD", "Taiwan Dollar", "NT$", 2),
    ("VND", "Vietnamese Đồng", "₫", 0),
    ("LAK", "Lao Kip", "₭", 0),
    ("KHR", "Cambodian Riel", "៛", 2),
]


class Command(BaseCommand):
    help = "Seed ISO 4217 currencies (excluding VND as foreign) for the FX module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-vnd",
            action="store_true",
            help="Include VND row (off by default since VND is the local currency).",
        )

    def handle(self, *args, **options):
        include_vnd = options.get("include_vnd", False)
        created = 0
        updated = 0
        for code, name, symbol, decimals in _CURRENCIES:
            if code == "VND" and not include_vnd:
                continue
            _, was_created = Currency.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "symbol": symbol,
                    "decimals": decimals,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        total = Currency.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded currencies: {created} new, {updated} updated ({total} active total)."
            )
        )
