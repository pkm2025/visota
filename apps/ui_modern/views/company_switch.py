"""Company switcher — lets user change which company they're working in."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View


class CompanySwitchView(LoginRequiredMixin, View):
    """POST: switch current company in session."""

    login_url = "/auth/login/"

    def post(self, request, *args, **kwargs):
        company_id = request.POST.get("company_id")
        if company_id:
            # Verify user has access to this company
            from apps.identity.models import UserCompanyRole
            has_access = (
                UserCompanyRole.objects.filter(
                    user=request.user, company_id=company_id
                ).exists()
                or request.user.is_superuser
            )
            if has_access:
                request.session["current_company_id"] = int(company_id)
        return redirect(request.META.get("HTTP_REFERER", "/modern/"))
