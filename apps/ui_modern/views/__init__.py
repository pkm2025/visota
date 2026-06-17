from .asset_views import (
    AssetCreateView,
    AssetListView,
    DepreciationRunView,
)
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .closing_views import PeriodClosingView
from .contract_views import ContractCreateView, ContractListView
from .customer_views import (
    CustomerCreateView,
    CustomerListView,
    CustomerUpdateView,
)
from .dashboard_views import DashboardView
from .document_views import (
    DocumentDeleteView,
    DocumentDownloadView,
    VoucherPrintView,
    VoucherUploadView,
)
from .health_views import health_detailed, health_simple
from .hr_views import EmployeeCreateView, EmployeeListView
from .input_invoice_views import (
    InputInvoiceListView,
    InputInvoiceProcessView,
    InputInvoiceUploadView,
)
from .ledger_views import VoucherCreateView, VoucherDetailView, VoucherListView
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
from .report_views import (
    BalanceSheetView,
    GeneralJournalView,
    GeneralLedgerView,
    PnLView,
    TrialBalanceView,
    VATReturnView,
)
from .sales_views import (
    SalesInvoiceCreateView,
    SalesInvoiceListView,
)
from .stock_views import (
    StockVoucherCreateView,
    StockVoucherListView,
)
from .recurring_views import RecurringListView, RecurringRunView
from .treasury_views import CashPaymentCreateView, CashReceiptCreateView
from .vendor_views import (
    VendorCreateView,
    VendorListView,
    VendorUpdateView,
)

__all__ = [
    "DashboardView",
    "PMKetoanLoginView",
    "PMKetoanLogoutView",
    "PeriodClosingView",
    "DocumentDeleteView",
    "DocumentDownloadView",
    "VoucherPrintView",
    "VoucherUploadView",
    "AssetListView",
    "AssetCreateView",
    "DepreciationRunView",
    "health_simple",
    "health_detailed",
    "VoucherListView",
    "VoucherCreateView",
    "VoucherDetailView",
    "TrialBalanceView",
    "BalanceSheetView",
    "PnLView",
    "VATReturnView",
    "GeneralJournalView",
    "GeneralLedgerView",
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
    "CashReceiptCreateView",
    "CashPaymentCreateView",
    "ContractListView",
    "ContractCreateView",
    "InputInvoiceListView",
    "InputInvoiceUploadView",
    "InputInvoiceProcessView",
    "RecurringListView",
    "RecurringRunView",
]
