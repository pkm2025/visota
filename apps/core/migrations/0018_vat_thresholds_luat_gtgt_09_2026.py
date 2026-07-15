# Generated for VAT law 09/2026 thresholds (Luật GTGT 09/2026)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_cit_exemption_threshold_nd141"),
    ]

    operations = [
        migrations.AddField(
            model_name="taxrateconfig",
            name="vat_exemption_threshold",
            field=models.DecimalField(
                decimal_places=4,
                default=1000000000,
                max_digits=20,
            ),
        ),
        migrations.AddField(
            model_name="taxrateconfig",
            name="vat_refund_threshold",
            field=models.DecimalField(
                decimal_places=4,
                default=300000000,
                max_digits=20,
            ),
        ),
    ]
