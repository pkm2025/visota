"""Dashboard view for Modern UI."""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard for authenticated users."""

    template_name = 'modern/dashboard/index.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Tổng quan'
        return ctx
