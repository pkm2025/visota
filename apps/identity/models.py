"""User, Role, Permission models."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with Vietnamese-friendly fields."""

    full_name = models.CharField(max_length=255, blank=True)
    full_name_en = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True)

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.full_name:
            return f"{self.full_name} ({self.username})"
        return self.username


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permission"
        ordering = ["module", "code"]

    def __str__(self):
        return f"{self.code} ({self.name})"


class Role(models.Model):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        db_table = "role"
        unique_together = [("company", "code")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserCompanyRole(models.Model):
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="company_roles",
    )
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        "identity.Role",
        on_delete=models.PROTECT,
        related_name="user_company_roles",
    )
    is_default = models.BooleanField(default=False)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "user_company_role"
        unique_together = [("user", "company", "role")]

    def __str__(self):
        return f"{self.user} @ {self.company} = {self.role}"
