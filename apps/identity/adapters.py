"""Custom allauth adapters for Visota ERP."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class VisotaAccountAdapter(DefaultAccountAdapter):
    """Customize allauth account behavior for Visota."""

    def get_login_redirect_url(self, request):
        """Redirect to dashboard after login."""
        return "/modern/"


class VisotaSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Auto-link social accounts with existing users by email.

    If a user with the same email already exists, the social account
    is automatically linked instead of creating a new user.
    """

    def pre_social_login(self, request, sociallogin):
        """Link social account to existing user if email matches."""
        from apps.identity.models import User

        if sociallogin.is_existing:
            return  # Already linked

        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass  # Will auto-signup a new user

    def populate_user(self, request, sociallogin, data):
        """Populate User fields from social data."""
        user = super().populate_user(request, sociallogin, data)

        # Map provider-specific fields
        provider = sociallogin.account.provider
        extra = sociallogin.account.extra_data

        if provider == "google":
            user.full_name = extra.get("name", "")
            if extra.get("picture"):
                # Avatar URL — actual download happens later if needed
                pass
        elif provider == "facebook" or provider == "zalo":
            user.full_name = extra.get("name", "")

        return user
