"""E-invoice app config (Hóa đơn điện tử ND 254/2026/ND-CP, TT 91/2026/TT-BTC)."""

from django.apps import AppConfig


class EInvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.einvoice"
    label = "einvoice"
    verbose_name = "Hóa đơn điện tử"
