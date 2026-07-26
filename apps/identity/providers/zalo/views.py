"""Zalo OAuth2 views for django-allauth."""

import requests
from allauth.socialaccount.providers.base import ProviderException
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .provider import ZaloProvider


class ZaloOAuth2Adapter(OAuth2Adapter):
    """Zalo OAuth2 adapter."""

    provider_id = ZaloProvider.id
    authorize_url = "https://oauth.zalo.me/oauth/authorize"
    access_token_url = "https://oauth.zalo.me/oauth/access_token"
    profile_url = "https://graph.zalo.me/v2.0/me"

    def complete_login(self, request, app, token, response):
        headers = {"access_token": token.token}
        resp = requests.get(self.profile_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extra_data = resp.json()

        if "error" in extra_data:
            raise ProviderException(extra_data.get("message", "Zalo API error"))

        return self.get_provider().sociallogin_from_response(request, extra_data)


oauth2_login = OAuth2LoginView.adapter_view(ZaloOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(ZaloOAuth2Adapter)
