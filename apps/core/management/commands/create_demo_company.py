"""Create demo company matching SIS PKM."""
from django.core.management.base import BaseCommand
from apps.core.models import Company


class Command(BaseCommand):
    help = 'Create demo company (PKM) matching SIS for verification'

    def handle(self, *args, **options):
        company, created = Company.objects.update_or_create(
            code='PKM',
            defaults={
                'name': 'CÔNG TY CỔ PHẦN CÔNG NGHỆ PKM',
                'tax_code': '0101218690',
                'address': 'Tầng 06, Toà Nhà Icon4, Số 243A Đê La Thành, Hà Nội',
                'accounting_regime': 'tt133',
                'default_currency': 'VND',
                'brand_name': 'PKM Accounting',
                'brand_primary_color': '#2563eb',
                'is_active': True,
            },
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} demo company: {company.code} - {company.name}'
        ))
