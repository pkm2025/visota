"""Seed management command for InvoiceGroup (3 groups per TT133)."""

from django.core.management.base import BaseCommand

from apps.master_data.models import InvoiceGroup

# 3 nhóm hóa đơn theo TT133/TT78
INVOICE_GROUPS = [
    (
        "4",
        "Hóa đơn đầu vào (INPUT)",
        "Input VAT invoice",
        "1331",
        "331",
        1,
    ),
    (
        "5",
        "Hóa đơn đầu ra (OUTPUT)",
        "Output VAT invoice",
        "131",
        "33311",
        2,
    ),
    (
        "6",
        "Khác (OTHER)",
        "Other",
        "",
        "",
        3,
    ),
]


class Command(BaseCommand):
    help = "Seed 3 InvoiceGroup entries (#4 INPUT, #5 OUTPUT, #6 OTHER) — idempotent"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for code, name_vi, name_en, debit_acc, credit_acc, sort_order in INVOICE_GROUPS:
            _, created = InvoiceGroup.objects.update_or_create(
                code=code,
                defaults={
                    "name_vi": name_vi,
                    "name_en": name_en,
                    "default_tax_account_debit": debit_acc,
                    "default_tax_account_credit": credit_acc,
                    "sort_order": sort_order,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total = InvoiceGroup.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} created, {updated_count} updated, "
                f"{total} total InvoiceGroup rows"
            )
        )
