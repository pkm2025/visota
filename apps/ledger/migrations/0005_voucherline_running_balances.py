# Generated for m3-running-balance-db

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0004_voucherline_is_auto_tax_posting"),
    ]

    operations = [
        migrations.AddField(
            model_name="voucherline",
            name="running_balance_debit",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name="voucherline",
            name="running_balance_credit",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=20),
        ),
    ]
