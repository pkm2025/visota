"""Add business event interaction types and make user nullable.

Supports business-event logging from the service layer (voucher_create,
invoice_create, dnsn_voucher_create, period_close, einvoice_issue) where
a user may not be available (system/automated events).
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pkm", "0005_qa_history_interaction_context"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="userinteractionlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="pkm_interaction_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="userinteractionlog",
            name="interaction_type",
            field=models.CharField(
                choices=[
                    ("page_view", "Page View"),
                    ("search", "Search"),
                    ("note_create", "Note Create"),
                    ("document_create", "Document Create"),
                    ("voucher_create", "Voucher Create"),
                    ("invoice_create", "Invoice Create"),
                    ("dnsn_voucher_create", "DNSN Voucher Create"),
                    ("period_close", "Period Close"),
                    ("einvoice_issue", "E-Invoice Issue"),
                ],
                max_length=30,
            ),
        ),
    ]
