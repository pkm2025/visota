"""Rename hide_pmketoan_branding to hide_visota_branding."""

from django.db import migrations


class Migration(migrations.Migration):
    """Rename Company.hide_pmketoan_branding → hide_visota_branding."""

    dependencies = [
        ("core", "0012_company_dnsn_optional_ledgers"),
    ]

    operations = [
        migrations.RenameField(
            model_name="company",
            old_name="hide_pmketoan_branding",
            new_name="hide_visota_branding",
        ),
    ]
