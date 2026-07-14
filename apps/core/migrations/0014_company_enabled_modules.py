"""Add enabled_modules JSON field for modular sidebar visibility."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_rename_hide_pmketoan_to_hide_visota_branding"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="enabled_modules",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
