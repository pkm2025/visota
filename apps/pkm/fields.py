"""Custom Django field for MariaDB VECTOR type.

Django's ORM does not natively support MariaDB's VECTOR type. This custom
field maps the Python ``bytes``/``None`` representation to the DB-native
``VECTOR(N)`` type so that migrations and schema inspection work correctly.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper


class VectorField(models.Field):  # type: ignore[type-arg]
    """MariaDB VECTOR(N) field for embedding storage.

    The field is not writable through the Django ORM (VECTOR values must be
    stored via raw SQL using ``VEC_FromText()``). It exists so that Django's
    schema/migration system is aware of the column.
    """

    description = "MariaDB VECTOR type for embedding storage"

    def __init__(self, *args: Any, dimensions: int = 1536, **kwargs: Any) -> None:
        self.dimensions = dimensions
        kwargs.setdefault("editable", False)
        kwargs.setdefault("default", None)
        super().__init__(*args, **kwargs)

    def db_type(self, connection: BaseDatabaseWrapper) -> str:
        return f"VECTOR({self.dimensions})"

    def deconstruct(self) -> Any:
        name, path, args, kwargs = super().deconstruct()
        kwargs["dimensions"] = self.dimensions
        return name, path, args, kwargs

    def get_internal_type(self) -> str:
        return "BinaryField"
