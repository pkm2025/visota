from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from apps.ui_modern.views import (
    PMKetoanLoginView, PMKetoanLogoutView,
    health_simple, health_detailed,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/login/', PMKetoanLoginView.as_view(), name='login'),
    path('auth/logout/', PMKetoanLogoutView.as_view(), name='logout'),
    path('health/', health_simple, name='health_simple'),
    path('health/detailed/', health_detailed, name='health_detailed'),
    path('', RedirectView.as_view(url='/modern/', permanent=False)),
    path('modern/', include('apps.ui_modern.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
