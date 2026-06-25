"""Bank guarantees app — bảo lãnh ngân hàng."""

from django.apps import AppConfig


class GuaranteesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.guarantees"
    label = "guarantees"
    verbose_name = "Bảo lãnh ngân hàng"
