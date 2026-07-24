from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0002_tt58_dnsn_voucher_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseinvoice",
            name="credit_account",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "TK Có override (vd 3388/112). Mặc định theo "
                    "Vendor.gl_account_payable (331)."
                ),
                max_length=20,
            ),
        ),
    ]
