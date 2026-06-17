from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import (
    DashboardView,
    TrialBalanceView,
    VoucherCreateView,
    VoucherListView,
)

app_name = "ui_modern"

urlpatterns = [
    path("", login_required(DashboardView.as_view()), name="dashboard"),
    path(
        "vouchers/",
        login_required(VoucherListView.as_view()),
        name="voucher_list",
    ),
    path(
        "vouchers/new/",
        login_required(VoucherCreateView.as_view()),
        name="voucher_create",
    ),
    path(
        "reports/trial-balance/",
        login_required(TrialBalanceView.as_view()),
        name="trial_balance",
    ),
]
