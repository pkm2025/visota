"""Notification UI views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView

from .models import Notification
from .services import NotificationService


class NotificationListView(LoginRequiredMixin, ListView):
    """Full inbox for the current user."""

    template_name = "modern/notifications/inbox.html"
    context_object_name = "notifications"
    paginate_by = 50
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        only_unread = self.request.GET.get("unread")
        if only_unread:
            qs = qs.filter(is_read=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hộp thư thông báo"
        ctx["unread_count"] = Notification.objects.filter(
            user=self.request.user, is_read=False
        ).count()
        return ctx


class NotificationMarkReadView(LoginRequiredMixin, View):
    """POST: mark a single notification as read."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        NotificationService.mark_read(pk, request.user)
        # If HTMX/JSON request, return JSON; otherwise redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect(request.META.get("HTTP_REFERER", "/modern/"))


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """POST: mark all as read."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        NotificationService.mark_all_read(request.user)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect(request.META.get("HTTP_REFERER", "/modern/"))


class NotificationCountView(LoginRequiredMixin, View):
    """JSON endpoint for polling unread count (for AJAX refresh)."""

    login_url = "/auth/login/"

    def get(self, request, *args, **kwargs):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({"count": count})
