"""Add tk_doi_ung_pattern to FinancialReportLine.

This field stores the counterpart (offsetting) account-code pattern
used by the cash-flow direct method.  A direct-method line aggregates
the cash leg (TK 111*/112*) but only for vouchers whose other leg
hits an account matching this pattern, per TT133/TT200.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialreportline",
            name="tk_doi_ung_pattern",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
            ),
        ),
    ]
