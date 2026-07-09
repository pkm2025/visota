from django.apps import AppConfig


class PKMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pkm"
    verbose_name = "Personal Knowledge Management"

    def ready(self) -> None:
        """Import signal handlers to connect post_save hooks.

        This ensures the note_create and document_create interaction logging
        signal receivers are registered when Django starts.
        """
        # noqa: F401 — import for side-effect (signal registration)
        from . import signals  # noqa: F401
