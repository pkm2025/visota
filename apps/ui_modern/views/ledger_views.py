"""Ledger views — voucher list, form, detail."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.ledger.models import AccountingVoucher


class VoucherListView(LoginRequiredMixin, ListView):
    """List of accounting vouchers for the current company."""

    template_name = 'modern/ledger/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 25
    login_url = '/auth/login/'

    def get_queryset(self):
        qs = AccountingVoucher.objects.select_related('company').order_by(
            '-voucher_date', '-id'
        )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(voucher_no__icontains=search) | qs.filter(
                description__icontains=search
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Phiếu kế toán'
        ctx['status_choices'] = AccountingVoucher.Status.choices
        return ctx
