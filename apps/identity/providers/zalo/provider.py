"""Zalo OAuth2 provider for django-allauth.

Zalo Official Account OAuth2 docs:
  https://developers.zalo.me/docs/social/

Flow:
  1. Redirect user to https://oauth.zalo.me/oauth/authorize
     with app_id, redirect_uri, state.
  2. Zalo redirects back with ?code=...
  3. Exchange code for access_token at https://oauth.zalo.me/oauth/access_token
  4. Use access_token to get user profile at https://graph.zalo.me/v2.0/me
"""

from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class ZaloAccount(ProviderAccount):
    """Zalo account data wrapper."""

    def get_avatar_url(self):
        picture = self.account.extra_data.get("picture")
        if isinstance(picture, dict):
            return picture.get("data", {}).get("url")
        return picture

    def to_str(self):
        d = self.account.extra_data
        name = d.get("name") or d.get("id")
        return name or super().to_str()


class ZaloProvider(OAuth2Provider):
    """Zalo OAuth2 provider for django-allauth."""

    id = "zalo"
    name = "Zalo"
    account_class = ZaloAccount

    def extract_uid(self, data):
        return str(data.get("id", ""))

    def extract_common_fields(self, data):
        name = data.get("name", "")
        return {
            "username": data.get("id", ""),
            "email": data.get("email", "") or f"{data.get('id', '')}@zalo.me",
            "full_name": name,
        }

    def get_default_scope(self):
        return ["id", "name", "email"]
