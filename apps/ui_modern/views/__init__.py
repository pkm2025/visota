from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .customer_views import (
    CustomerCreateView,
    CustomerListView,
    CustomerUpdateView,
)
from .dashboard_views import DashboardView
from .health_views import health_detailed, health_simple
from .ledger_views import VoucherCreateView, VoucherListView
from .product_views import (
    ProductCreateView,
    ProductListView,
    ProductUpdateView,
)
from .report_views import TrialBalanceView
from .vendor_views import (
    VendorCreateView,
    VendorListView,
    VendorUpdateView,
)

__all__ = [
    "DashboardView",
    "PMKetoanLoginView",
    "PMKetoanLogoutView",
    "health_simple",
    "health_detailed",
    "VoucherListView",
    "VoucherCreateView",
    "TrialBalanceView",
    "CustomerListView",
    "CustomerCreateView",
    "CustomerUpdateView",
    "VendorListView",
    "VendorCreateView",
    "VendorUpdateView",
    "ProductListView",
    "ProductCreateView",
    "ProductUpdateView",
]
