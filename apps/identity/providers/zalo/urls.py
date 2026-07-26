"""Zalo OAuth2 provider URLs."""

from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import ZaloProvider

urlpatterns = default_urlpatterns(ZaloProvider)
