"""Add company FK to ContractTemplate (multi-tenant isolation).

VAL-SEC-004: ContractTemplate inherits CompanyOwnedModel and has a
company FK. Existing rows are assigned to the first company so the
migration is reversible on existing data.

The global unique constraint on ``code`` is replaced by a
``(company, code)`` unique_together so each tenant can reuse template
codes independently.
"""

from django.db import migrations, models


def assign_existing_templates_to_first_company(apps, schema_editor):
    """Assign any pre-existing ContractTemplate rows to the first Company.

    This preserves seed data on systems that already have global templates
    loaded. New deployments start empty so this is a no-op.
    """
    ContractTemplate = apps.get_model("contracts", "ContractTemplate")
    Company = apps.get_model("core", "Company")
    if ContractTemplate.objects.exists() and not Company.objects.exists():
        # Cannot assign without a company — leave rows alone and let the
        # NOT NULL constraint surface the issue (only happens on broken data).
        return
    first_company = Company.objects.first()
    if first_company is None:
        return
    ContractTemplate.objects.filter(company__isnull=True).update(company=first_company)


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0003_pit_history_and_bidding"),
        ("core", "0019_alter_company_accounting_regime_q48_deprecated"),
    ]

    operations = [
        migrations.AddField(
            model_name="contracttemplate",
            name="company",
            field=models.ForeignKey(
                db_index=True,
                on_delete=models.deletion.CASCADE,
                related_name="+",
                to="core.company",
                null=True,
            ),
        ),
        migrations.RunPython(
            assign_existing_templates_to_first_company,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="contracttemplate",
            name="company",
            field=models.ForeignKey(
                db_index=True,
                on_delete=models.deletion.CASCADE,
                related_name="+",
                to="core.company",
            ),
        ),
        migrations.AlterField(
            model_name="contracttemplate",
            name="code",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterUniqueTogether(
            name="contracttemplate",
            unique_together={("company", "code")},
        ),
    ]
