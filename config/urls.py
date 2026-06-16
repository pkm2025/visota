from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from apps.ui_modern.views import PMKetoanLoginView, PMKetoanLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/login/', PMKetoanLoginView.as_view(), name='login'),
    path('auth/logout/', PMKetoanLogoutView.as_view(), name='logout'),
    path('', RedirectView.as_view(url='/modern/', permanent=False)),
    path('modern/', include('apps.ui_modern.urls')),
]
