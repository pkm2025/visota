"""FX app config — multi-currency deep + revaluation."""

from django.apps import AppConfig


class FxConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fx"
    label = "fx"
    verbose_name = "Tỷ giá & Chênh lệch tỷ giá"
