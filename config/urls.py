from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path
from django.views.defaults import page_not_found, server_error
from django.views.generic import RedirectView, TemplateView

from apps.core.api import api
from apps.ui_modern.views import (
    VisotaLoginView,
    VisotaLogoutView,
    health_detailed,
    health_simple,
)
from apps.ui_modern.views.company_switch import CompanySwitchView
from config.sitemap import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path("sitemap.xml", sitemap_view, {"sitemaps": sitemaps}, name="sitemap"),
    path("admin/", admin.site.urls),
    path("auth/login/", VisotaLoginView.as_view(), name="login"),
    path("auth/logout/", VisotaLogoutView.as_view(), name="logout"),
    # Social login (Google, Facebook, Zalo)
    path("accounts/", include("allauth.urls")),
    path("accounts/zalo/", include("apps.identity.providers.zalo.urls")),
    path("health/", health_simple, name="health_simple"),
    path("health/detailed/", health_detailed, name="health_detailed"),
    path(
        "no-access/",
        TemplateView.as_view(template_name="modern/no_access.html"),
        name="no_access",
    ),
    path(
        "offline/",
        TemplateView.as_view(template_name="modern/offline.html"),
        name="offline",
    ),
    path("notifications/", include("apps.notifications.urls")),
    # Public pages (landing + blog)
    path("", include("apps.public.urls", namespace="public")),
    # Company switcher
    path("switch-company/", CompanySwitchView.as_view(), name="switch_company"),
    # App redirect
    path("app/", RedirectView.as_view(url="/modern/", permanent=False)),
    path("modern/", include("apps.ui_modern.urls")),
    # REST API (django-ninja)
    path("api/v1/", api.urls),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]


# Branded error pages — Vietnamese templates extending modern/base/layout.html.
# These module-level variables override Django's default error handlers.
# Using lambdas to bind template_name to the built-in default views.
handler404 = lambda request, exception: page_not_found(request, exception, template_name="404.html")  # noqa: E731
handler500 = lambda request: server_error(request, template_name="500.html")  # noqa: E731
