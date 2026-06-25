"""Bank loans app — vay vốn ngân hàng."""

from django.apps import AppConfig


class LoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loans"
    label = "loans"
    verbose_name = "Vay vốn ngân hàng"
