"""Expose pending approval count to templates for sidebar badge."""

from apps.identity.services import UserService


def approvals(request):
    """Inject ``pending_approvals_count`` for the current user/company."""
    user = getattr(request, "user", None)
    company = getattr(request, "current_company", None)
    if not user or not getattr(user, "is_authenticated", False) or not company:
        return {"pending_approvals_count": 0}
    if not UserService(user, company).has_permission("approvals.access"):
        return {"pending_approvals_count": 0}
    from apps.approvals.services import ApprovalService

    try:
        count = ApprovalService.pending_for_user(user, company).count()
    except Exception:
        count = 0
    return {"pending_approvals_count": count}
