"""Chart of accounts list view — TT133 account tree."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.master_data.models import ChartOfAccounts


class ChartOfAccountsListView(LoginRequiredMixin, ListView):
    """List all TT133 accounts for the current company."""

    template_name = "modern/ledger/chart_of_accounts_list.html"
    context_object_name = "accounts"
    paginate_by = 200
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = ChartOfAccounts.objects.select_related("company").order_by("account_code")
        account_type = self.request.GET.get("account_type")
        if account_type:
            qs = qs.filter(account_type=account_type)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(account_code__icontains=search) | qs.filter(
                account_name__icontains=search
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Hệ thống tài khoản"
        ctx["account_type_choices"] = ChartOfAccounts.objects.values_list(
            "account_type", flat=True
        ).distinct().order_by("account_type")
        return ctx
