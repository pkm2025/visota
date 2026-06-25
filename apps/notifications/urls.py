"""Notification URL routes — included from config/urls.py (not gated by company)."""

from django.urls import path

from .views import (
    NotificationCountView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="inbox"),
    path("count/", NotificationCountView.as_view(), name="count"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="mark_read"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark_all_read"),
]
