"""Role-based authentication backend."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class RoleBasedBackend(ModelBackend):
    """Authenticate via username or email. Permissions via UserService (template helper)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        # Try username first, then email
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            # Track IP + reset failed counter (audit)
            if request is not None:
                from apps.identity.audit import record_login
                record_login(user, request)
            return user
        return None

