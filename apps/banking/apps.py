"""Banking app — bank reconciliation (đối soát ngân hàng)."""

from django.apps import AppConfig


class BankingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.banking"
    label = "banking"
    verbose_name = "Ngân hàng & Đối soát"
