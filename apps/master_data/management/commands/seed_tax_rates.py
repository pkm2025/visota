"""Seed management command for TaxRateCode (8 TT78/2021 codes)."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.master_data.models import TaxRateCode

# 8 mã thuế GTGT theo Thông tư 78/2021/TT-BTC
TAX_RATES = [
    ("00", Decimal("0"), "0% - Hàng xuất khẩu", 1),
    ("05", Decimal("5"), "5% - Thuế suất 5%", 2),
    ("04", Decimal("5"), "5% - Hàng dịch vụ đặc thù", 3),
    ("10", Decimal("10"), "10% - Thuế suất 10%", 4),
    ("08", Decimal("10"), "10% - Đặc biệt (KKK)", 5),
    ("KT", Decimal("0"), "Không chịu thuế", 6),
    ("TS05", Decimal("5"), "TS tính 5%", 7),
    ("kht", Decimal("0"), "Không tính thuế", 8),
]


class Command(BaseCommand):
    help = "Seed 8 TaxRateCode entries per TT78/2021 (idempotent)"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for code, rate, name, sort_order in TAX_RATES:
            _, created = TaxRateCode.objects.update_or_create(
                code=code,
                defaults={
                    "rate": rate,
                    "display_name": name,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total = TaxRateCode.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} created, {updated_count} updated, "
                f"{total} total TaxRateCode rows"
            )
        )
