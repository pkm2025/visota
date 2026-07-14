"""Permission template tags for nav filtering."""

from django import template

from apps.core.module_config import ModuleVisibilityService

register = template.Library()


@register.simple_tag(takes_context=True)
def has_module_access(context, module: str) -> bool:
    """Return True if the current user has <module>.access permission AND
    the module is visible per the ModuleVisibilityService.

    Superusers bypass the permission check but are still subject to module
    visibility (so that advanced modules are hidden from the sidebar for
    DNSN companies until explicitly enabled). Unauthenticated users return
    False.
    """
    user = context.get("user")
    if not user or not getattr(user, "is_authenticated", False):
        return False

    request = context.get("request")
    company = getattr(request, "current_company", None) if request else None

    # --- Module visibility check (applies to all users including superusers) ---
    # If the module is hidden by ModuleVisibilityService, don't show it in
    # the sidebar regardless of permissions.
    vis_service = ModuleVisibilityService(company)
    if not vis_service.is_permission_module_visible(module):
        return False

    if getattr(user, "is_superuser", False):
        return True

    has_perm = context.get("has_perm")
    if has_perm is not None:
        return bool(has_perm(f"{module}.access"))

    # Context processor didn't bind has_perm — recompute from request.
    if not company:
        return False
    from apps.identity.services import UserService

    return bool(UserService(user, company).has_permission(f"{module}.access"))


@register.simple_tag(takes_context=True)
def user_permissions_for(context):
    """Return set of permission codes the current user has."""
    user = context.get("user")
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        from apps.identity.models import Permission

        return set(Permission.objects.values_list("code", flat=True))
    service = context.get("user_service")
    if service is None:
        return set()
    return service._get_permissions()
