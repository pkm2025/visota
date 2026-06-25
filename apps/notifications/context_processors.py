"""Expose unread count + recent notifications to every template."""

from apps.notifications.models import Notification


def notifications(request):
    """Inject unread_count + recent notifications into context."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {"unread_count": 0, "recent_notifications": []}

    qs = Notification.objects.filter(user=user)
    unread = qs.filter(is_read=False).count()
    recent = qs[:8]
    return {
        "unread_count": unread,
        "recent_notifications": list(recent),
    }
