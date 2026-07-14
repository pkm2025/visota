"""Add form_symbol field to EInvoice for 02BANHANG support (TT58)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_company_dnsn_optional_ledgers"),
        ("einvoice", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="einvoice",
            name="form_symbol",
            field=models.CharField(
                choices=[
                    ("01GTKT", "01GTKT — Hóa đơn GTGT"),
                    ("02BANHANG", "02BANHANG — Hóa đơn bán hàng"),
                ],
                default="01GTKT",
                max_length=10,
            ),
        ),
    ]
