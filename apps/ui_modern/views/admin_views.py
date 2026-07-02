"""Admin UI: roles, permissions, user-role assignment."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.core.models import Company
from apps.identity.models import Permission, Role, UserCompanyRole
from apps.identity.services import UserService

User = get_user_model()


class StaffRequiredMixin(UserPassesTestMixin):
    """Limit to superusers / staff."""

    login_url = "/auth/login/"

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or self.request.user.is_staff
        )


class MyPermissionsView(LoginRequiredMixin, TemplateView):
    """Show the current user their roles and permissions."""

    template_name = "modern/admin/my_permissions.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        ctx["page_title"] = "Quyền của tôi"
        ctx["company"] = company

        if company:
            assignments = UserCompanyRole.objects.filter(
                user=self.request.user, company=company
            ).select_related("role")
            ctx["assignments"] = assignments
            ctx["roles"] = [a.role for a in assignments]

            service = UserService(self.request.user, company)
            perm_codes = service._get_permissions()
            ctx["permission_codes"] = sorted(perm_codes)
            ctx["permissions"] = Permission.objects.filter(code__in=perm_codes).order_by(
                "module", "code"
            )

            all_perms = Permission.objects.all().order_by("module", "code")
            ctx["all_permissions"] = all_perms
            ctx["denied_permissions"] = [p for p in all_perms if p.code not in perm_codes]
        else:
            ctx["assignments"] = []
            ctx["permissions"] = []
            ctx["permission_codes"] = []
            ctx["all_permissions"] = Permission.objects.all()
            ctx["denied_permissions"] = []

        ctx["is_superuser"] = self.request.user.is_superuser
        return ctx


class AdminRoleListView(StaffRequiredMixin, ListView):
    """List all roles for the current company."""

    template_name = "modern/admin/role_list.html"
    context_object_name = "roles"
    paginate_by = 50

    def get_queryset(self):
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        qs = Role.objects.filter(company=company).prefetch_related("permissions")
        return qs.order_by("code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Vai trò & phân quyền"
        return ctx


class AdminRoleEditView(StaffRequiredMixin, View):
    """Edit a single role — toggle permissions."""

    template_name = "modern/admin/role_edit.html"

    def get(self, request, pk, *args, **kwargs):
        role = get_object_or_404(Role, pk=pk)
        all_perms = Permission.objects.all().order_by("module", "code")
        assigned = set(role.permissions.values_list("code", flat=True))

        # Group by module
        by_module = {}
        for p in all_perms:
            by_module.setdefault(p.module, []).append((p, p.code in assigned))

        ctx = {
            "page_title": f"Sửa vai trò: {role.name}",
            "role": role,
            "by_module": sorted(by_module.items()),
            "user_count": role.user_company_roles.count(),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk, *args, **kwargs):
        role = get_object_or_404(Role, pk=pk)
        if role.is_system and role.code == "admin":
            messages.error(request, "Vai trò 'admin' không thể sửa (toàn quyền).")
            return redirect("ui_modern:admin_role_edit", pk=pk)

        selected = request.POST.getlist("permissions")
        role.permissions.set(Permission.objects.filter(code__in=selected))

        # Invalidate caches for affected users
        for ucr in role.user_company_roles.all():
            UserService(ucr.user, ucr.company).invalidate_cache()

        messages.success(
            request,
            f"Đã cập nhật vai trò '{role.name}': {len(selected)} quyền được cấp.",
        )
        return redirect("ui_modern:admin_role_list")


class AdminUserListView(StaffRequiredMixin, ListView):
    """List users and their role assignments."""

    template_name = "modern/admin/user_list.html"
    context_object_name = "users"
    paginate_by = 50

    def get_queryset(self):
        return User.objects.all().order_by("-is_superuser", "username")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = getattr(self.request, "current_company", None) or Company.objects.first()
        ctx["page_title"] = "Người dùng"
        ctx["company"] = company
        if company:
            ctx["available_roles"] = Role.objects.filter(company=company).order_by("code")
        return ctx


class AdminUserAssignView(StaffRequiredMixin, View):
    """Assign a role to a user for the current company."""

    def post(self, request, user_id, *args, **kwargs):
        if request.user.id == user_id and not request.user.is_superuser:
            messages.error(request, "Bạn không thể tự thay đổi vai trò của mình.")
            return redirect("ui_modern:admin_user_list")

        target_user = get_object_or_404(User, pk=user_id)
        company = getattr(request, "current_company", None) or Company.objects.first()
        if not company:
            messages.error(request, "Chưa cấu hình công ty.")
            return redirect("ui_modern:admin_user_list")

        role_id = request.POST.get("role_id")
        action = request.POST.get("action", "assign")

        if action == "remove":
            UserCompanyRole.objects.filter(user=target_user, company=company).delete()
            UserService(target_user, company).invalidate_cache()
            messages.success(
                request,
                f"Đã gỡ mọi vai trò của '{target_user.username}' tại {company.name}.",
            )
            return redirect("ui_modern:admin_user_list")

        if not role_id:
            messages.error(request, "Vui lòng chọn vai trò.")
            return redirect("ui_modern:admin_user_list")

        role = get_object_or_404(Role, pk=role_id, company=company)
        ucr, created = UserCompanyRole.objects.update_or_create(
            user=target_user,
            company=company,
            role=role,
            defaults={"is_default": True},
        )
        # Other assignments lose default
        UserCompanyRole.objects.filter(user=target_user, company=company).exclude(pk=ucr.pk).update(
            is_default=False
        )

        UserService(target_user, company).invalidate_cache()
        verb = "Đã gán" if created else "Đã cập nhật"
        messages.success(
            request,
            f"{verb} vai trò '{role.name}' cho '{target_user.username}'.",
        )
        return redirect("ui_modern:admin_user_list")
