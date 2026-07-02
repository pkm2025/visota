from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from apps.ui_modern.views import (
    PMKetoanLoginView, PMKetoanLogoutView,
    health_simple, health_detailed,
)
from apps.ui_modern.views.company_switch import CompanySwitchView
from apps.core.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/login/', PMKetoanLoginView.as_view(), name='login'),
    path('auth/logout/', PMKetoanLogoutView.as_view(), name='logout'),
    path('health/', health_simple, name='health_simple'),
    path('health/detailed/', health_detailed, name='health_detailed'),
    path(
        'no-access/',
        TemplateView.as_view(template_name='modern/no_access.html'),
        name='no_access',
    ),
    path(
        'offline/',
        TemplateView.as_view(template_name='modern/offline.html'),
        name='offline',
    ),
    path('notifications/', include('apps.notifications.urls')),
    # Public pages (landing + blog)
    path('', include('apps.public.urls', namespace='public')),
    # Company switcher
    path('switch-company/', CompanySwitchView.as_view(), name='switch_company'),
    # App redirect
    path('app/', RedirectView.as_view(url='/modern/', permanent=False)),
    path('modern/', include('apps.ui_modern.urls')),
    # REST API (django-ninja)
    path('api/v1/', api.urls),
]

if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
