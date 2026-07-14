from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_tt58_company_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="dnsn_optional_ledgers",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
