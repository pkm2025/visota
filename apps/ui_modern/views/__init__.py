from .asset_views import (
    AssetCreateView,
    AssetListView,
    DepreciationRunView,
)
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .customer_views import (
    CustomerCreateView,
    CustomerListView,
    CustomerUpdateView,
)
from .dashboard_views import DashboardView
from .health_views import health_detailed, health_simple
from .hr_views import EmployeeCreateView, EmployeeListView
from .ledger_views import VoucherCreateView, VoucherListView
from .payroll_views import PayrollRunView
from .product_views import (
    ProductCreateView,
    ProductListView,
    ProductUpdateView,
)
from .purchase_views import (
    PurchaseInvoiceCreateView,
    PurchaseInvoiceListView,
)
from .report_views import BalanceSheetView, TrialBalanceView
from .sales_views import (
    SalesInvoiceCreateView,
    SalesInvoiceListView,
)
from .stock_views import (
    StockVoucherCreateView,
    StockVoucherListView,
)
from .vendor_views import (
    VendorCreateView,
    VendorListView,
    VendorUpdateView,
)

__all__ = [
    "DashboardView",
    "PMKetoanLoginView",
    "PMKetoanLogoutView",
    "AssetListView",
    "AssetCreateView",
    "DepreciationRunView",
    "health_simple",
    "health_detailed",
    "VoucherListView",
    "VoucherCreateView",
    "TrialBalanceView",
    "BalanceSheetView",
    "CustomerListView",
    "CustomerCreateView",
    "CustomerUpdateView",
    "VendorListView",
    "VendorCreateView",
    "VendorUpdateView",
    "ProductListView",
    "ProductCreateView",
    "ProductUpdateView",
    "SalesInvoiceListView",
    "SalesInvoiceCreateView",
    "PurchaseInvoiceListView",
    "PurchaseInvoiceCreateView",
    "StockVoucherListView",
    "StockVoucherCreateView",
    "EmployeeListView",
    "EmployeeCreateView",
    "PayrollRunView",
]
