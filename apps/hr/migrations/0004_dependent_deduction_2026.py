"""Update Dependent.deduction_amount default from 4.4M to 6.2M per NQ 110/2025."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0003_leaverecord_insurancecontribution_leavebalance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dependent",
            name="deduction_amount",
            field=models.DecimalField(
                decimal_places=4,
                default=6200000,
                max_digits=20,
            ),
        ),
    ]
