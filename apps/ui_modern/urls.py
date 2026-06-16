from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import DashboardView

app_name = "ui_modern"

urlpatterns = [
    path("", login_required(DashboardView.as_view()), name="dashboard"),
]
