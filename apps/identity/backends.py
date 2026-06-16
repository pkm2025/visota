"""Identity auth backend stub — implemented in Task 7."""
from django.contrib.auth.backends import ModelBackend


class RoleBasedBackend(ModelBackend):
    """Role-based auth backend — extended in Task 7."""
    pass
