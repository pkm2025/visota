"""E-invoice app config (Hóa đơn điện tử TT78/2021)."""

from django.apps import AppConfig


class EInvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.einvoice"
    label = "einvoice"
    verbose_name = "Hóa đơn điện tử"
