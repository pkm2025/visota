"""Public app — landing page + blog (no auth required)."""

from django.apps import AppConfig


class PublicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public"
    label = "public"
    verbose_name = "Trang công khai"
