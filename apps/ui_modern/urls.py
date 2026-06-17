from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import (
    CustomerCreateView,
    CustomerListView,
    CustomerUpdateView,
    DashboardView,
    ProductCreateView,
    ProductListView,
    ProductUpdateView,
    TrialBalanceView,
    VendorCreateView,
    VendorListView,
    VendorUpdateView,
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
    # Master data — Customer
    path(
        "customers/",
        login_required(CustomerListView.as_view()),
        name="customer_list",
    ),
    path(
        "customers/new/",
        login_required(CustomerCreateView.as_view()),
        name="customer_create",
    ),
    path(
        "customers/<int:pk>/edit/",
        login_required(CustomerUpdateView.as_view()),
        name="customer_update",
    ),
    # Master data — Vendor
    path(
        "vendors/",
        login_required(VendorListView.as_view()),
        name="vendor_list",
    ),
    path(
        "vendors/new/",
        login_required(VendorCreateView.as_view()),
        name="vendor_create",
    ),
    path(
        "vendors/<int:pk>/edit/",
        login_required(VendorUpdateView.as_view()),
        name="vendor_update",
    ),
    # Master data — Product
    path(
        "products/",
        login_required(ProductListView.as_view()),
        name="product_list",
    ),
    path(
        "products/new/",
        login_required(ProductCreateView.as_view()),
        name="product_create",
    ),
    path(
        "products/<int:pk>/edit/",
        login_required(ProductUpdateView.as_view()),
        name="product_update",
    ),
]
