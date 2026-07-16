"""Add is_system flag to PKMDocument for shared regulation documents.

System documents (is_system=True) are seeded by the ``seed_pkm_regulations``
management command and represent Vietnamese regulations (TT58, PIT/CIT/VAT
rates, TT133 chart overview, ND254 e-invoice basics). They are shared across
tenants via a sentinel company or company=first and excluded from normal
per-user document listings.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pkm", "0006_business_event_interaction_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="pkmdocument",
            name="is_system",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If True, this document is a system-seeded regulation or "
                    "reference shared across tenants (e.g. TT58, PIT rates, "
                    "TT133 overview)."
                ),
            ),
        ),
        migrations.AddIndex(
            model_name="pkmdocument",
            index=models.Index(fields=["is_system"], name="pkm_doc_is_system_idx"),
        ),
    ]
