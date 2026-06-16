"""Identity context processors."""


def user_permissions(request):
    """Expose permission helper to templates."""
    user = getattr(request, 'user', None)
    company = getattr(request, 'current_company', None)

    if not user or not user.is_authenticated or not company:
        return {'has_perm': lambda code: False}

    from apps.identity.services import UserService
    service = UserService(user, company)

    return {
        'has_perm': service.has_permission,
        'user_service': service,
    }
