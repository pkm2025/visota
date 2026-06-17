"""Reporting views — trial balance, etc."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.ledger.models import AccountPeriodBalance


class TrialBalanceView(LoginRequiredMixin, TemplateView):
    """Bảng cân đối tài khoản (S06-DN)."""

    template_name = 'modern/reporting/trial_balance.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        try:
            fiscal_year = int(self.request.GET.get('fiscal_year', today.year))
        except (TypeError, ValueError):
            fiscal_year = today.year
        try:
            period = int(self.request.GET.get('period', today.month))
        except (TypeError, ValueError):
            period = today.month

        balances = AccountPeriodBalance.objects.filter(
            fiscal_year=fiscal_year,
            period=period,
        ).select_related('company').order_by('account_code')

        total_opening_d = Decimal('0')
        total_opening_c = Decimal('0')
        total_period_d = Decimal('0')
        total_period_c = Decimal('0')
        total_closing_d = Decimal('0')
        total_closing_c = Decimal('0')

        rows = []
        for b in balances:
            od = b.opening_debit or 0
            oc = b.opening_credit or 0
            pd_ = b.period_debit or 0
            pc = b.period_credit or 0
            cd_ = b.closing_debit or 0
            cc = b.closing_credit or 0
            if od == 0 and oc == 0 and pd_ == 0 and pc == 0:
                continue

            rows.append(b)
            total_opening_d += od
            total_opening_c += oc
            total_period_d += pd_
            total_period_c += pc
            total_closing_d += cd_
            total_closing_c += cc

        ctx.update(
            {
                'page_title': 'Bảng cân đối tài khoản',
                'fiscal_year': fiscal_year,
                'period': period,
                'balances': rows,
                'total_opening_debit': total_opening_d,
                'total_opening_credit': total_opening_c,
                'total_period_debit': total_period_d,
                'total_period_credit': total_period_c,
                'total_closing_debit': total_closing_d,
                'total_closing_credit': total_closing_c,
                'is_balanced': total_closing_d == total_closing_c,
                'period_choices': list(range(1, 13)),
                'year_choices': [2024, 2025, 2026, 2027],
            }
        )
        return ctx
