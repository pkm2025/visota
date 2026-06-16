"""Identity services: permission checks, role management."""

from django.core.cache import cache


class UserService:
    """Service layer for user operations and permission checks."""

    CACHE_KEY = "user_perms_{user_id}_{company_id}"

    def __init__(self, user, company):
        self.user = user
        self.company = company

    def has_permission(self, perm_code: str) -> bool:
        """Check if user has a permission via role assignments."""
        if self.user.is_superuser:
            return True
        if not self.company:
            return False
        perms = self._get_permissions()
        return perm_code in perms

    def _get_permissions(self) -> set:
        """Get user's permission codes (cached for 5 minutes)."""
        cache_key = self.CACHE_KEY.format(
            user_id=self.user.id,
            company_id=self.company.id if self.company else 0,
        )
        perms = cache.get(cache_key)
        if perms is None:
            perms = self._load_permissions()
            cache.set(cache_key, perms, timeout=300)
        return perms

    def _load_permissions(self) -> set:
        """Load permissions from DB via UserCompanyRole -> Role -> Permission."""
        from apps.identity.models import UserCompanyRole

        if not self.company:
            return set()
        ucrs = (
            UserCompanyRole.objects.filter(
                user=self.user,
                company=self.company,
            )
            .select_related("role")
            .prefetch_related("role__permissions")
        )
        perms = set()
        for ucr in ucrs:
            for p in ucr.role.permissions.all():
                perms.add(p.code)
        return perms

    def invalidate_cache(self):
        """Clear permission cache for this user/company."""
        cache.delete(
            self.CACHE_KEY.format(
                user_id=self.user.id,
                company_id=self.company.id if self.company else 0,
            )
        )
