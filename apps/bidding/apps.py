"""Bidding app config (Luật Đấu thầu 22/2023/QH15)."""

from django.apps import AppConfig


class BiddingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bidding"
    label = "bidding"
    verbose_name = "Đấu thầu"
