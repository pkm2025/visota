"""Identity context processors."""


def user_permissions(request):
    """Expose permission helper to templates.

    Also prefetches the authenticated user's ``company_roles`` (with
    ``company`` and ``role`` selected) so the base layout's company
    switcher does not trigger an N+1 query for each ``ucr.company`` /
    ``ucr.role`` access. The prefetch only runs when the user actually
    has at least one ``UserCompanyRole`` (avoids an unnecessary query
    for users with no role assignments, e.g. superusers-only accounts).
    """
    user = getattr(request, "user", None)
    company = getattr(request, "current_company", None)

    if not user or not user.is_authenticated or not company:
        return {"has_perm": lambda code: False}

    from apps.identity.services import UserService

    service = UserService(user, company)

    # Prefetch company_roles (with company + role) for the company switcher
    # dropdown in the base layout. Guarded by an exists() check so we don't
    # run an unnecessary eager-load query for users with no role assignments
    # (which nplusone would flag). Cached on the user instance per-request.
    if not getattr(user, "_company_roles_prefetched", False):
        from apps.identity.models import UserCompanyRole

        if UserCompanyRole.objects.filter(user=user).exists():
            roles_qs = list(
                UserCompanyRole.objects.filter(user=user)
                .select_related("company", "role")
                .order_by("company__name")
            )
        else:
            roles_qs = []
        user._prefetched_company_roles = roles_qs
        user._company_roles_prefetched = True

    return {
        "has_perm": service.has_permission,
        "user_service": service,
        "company_roles_dropdown": user._prefetched_company_roles,
    }
