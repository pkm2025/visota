"""Audit logging for auth events."""


def record_login(user, request):
    """Record successful login for audit purposes (IP, reset failed count)."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
        "REMOTE_ADDR"
    )
    user.last_login_ip = ip
    user.failed_login_count = 0
    user.save(update_fields=["last_login_ip", "failed_login_count"])
