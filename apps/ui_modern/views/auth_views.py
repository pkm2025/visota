"""Auth views: login + logout."""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from apps.ui_modern.forms import LoginForm


class VisotaLoginView(LoginView):
    """Login view with Visota ERP branding and Vietnamese UI."""

    template_name = "modern/auth/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("ui_modern:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Đăng nhập"
        return ctx


class VisotaLogoutView(LogoutView):
    """Logout view — POST-only (Django 4+ security)."""

    next_page = "/auth/login/"
