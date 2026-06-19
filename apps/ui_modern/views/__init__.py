from .asset_views import (
    AssetCreateView,
    AssetDisposeView,
    AssetListView,
    AssetTransactionListView,
    AssetTransferView,
    DepreciationRunView,
)
from .auth_views import PMKetoanLoginView, PMKetoanLogoutView
from .chart_of_accounts_views import ChartOfAccountsListView
from .closing_views import PeriodClosingView
from .contract_template_views import (
    ContractGenerateView,
    ContractTemplateListView,
    ContractTemplatePreviewView,
)
from .contract_views import ContractCreateView, ContractListView
from .crm_views import (
    AccountCreateView,
    CampaignCreateView,
    CampaignListView,
    LeadCreateView,
    LeadListView,
    OpportunityConvertView,
    OpportunityCreateView,
    OpportunityDetailView,
    OpportunityListView,
    TicketCreateView,
    TicketListView,
)
from .customer_views import (
    CustomerCreateView,
    CustomerDeleteView,
    CustomerExportView,
    CustomerListView,
    CustomerUpdateView,
)
from .dashboard_views import DashboardView
from .document_views import (
    ContractExportDocxView,
    DocumentDeleteView,
    DocumentDownloadView,
    TrialBalanceDocxView,
    VoucherPrintDocxView,
    VoucherPrintView,
    VoucherUploadView,
)
from .health_views import health_detailed, health_simple
from .hr_management_views import (
    DependentListView,
    InsuranceDashboardView,
    LaborContractCreateView,
    LaborContractListView,
    LeaveRequestView,
)
from .hr_views import EmployeeCreateView, EmployeeListView
from .input_invoice_views import (
    InputInvoiceListView,
    InputInvoiceProcessView,
    InputInvoiceUploadView,
)
from .ledger_views import (
    VoucherCreateView,
    VoucherDeleteView,
    VoucherDetailView,
    VoucherExportView,
    VoucherListView,
)
from .payroll_views import PayrollRunView
from .product_views import (
    ProductCreateView,
    ProductDeleteView,
    ProductDetailView,
    ProductExportView,
    ProductListView,
    ProductUpdateView,
)
from .project_views import (
    ProjectAddPhaseView,
    ProjectAddResourceView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectListView,
    ProjectTogglePhaseView,
)
from .purchase_views import (
    PurchaseInvoiceCreateView,
    PurchaseInvoiceListView,
)
from .recurring_views import RecurringListView, RecurringRunView
from .report_views import (
    BalanceSheetView,
    D62ReportView,
    GeneralJournalView,
    GeneralLedgerView,
    LaborUsageReportView,
    PITMonthlyReportView,
    PnLView,
    SalaryFundReportView,
    TrialBalanceView,
    VATReturnView,
)
from .sales_views import (
    SalesInvoiceCreateView,
    SalesInvoiceListView,
)
from .stock_views import (
    StockAdjustmentCreateView,
    StockAdjustmentListView,
    StockCardView,
    StockDashboardView,
    StockVoucherCreateView,
    StockVoucherListView,
)
from .treasury_views import CashPaymentCreateView, CashReceiptCreateView
from .vendor_views import (
    VendorCreateView,
    VendorDeleteView,
    VendorExportView,
    VendorListView,
    VendorUpdateView,
)

__all__ = [
    "DashboardView",
    "ChartOfAccountsListView",
    "PMKetoanLoginView",
    "PMKetoanLogoutView",
    "PeriodClosingView",
    "DocumentDeleteView",
    "DocumentDownloadView",
    "VoucherPrintView",
    "VoucherPrintDocxView",
    "ContractExportDocxView",
    "TrialBalanceDocxView",
    "VoucherUploadView",
    "AssetListView",
    "AssetCreateView",
    "AssetDisposeView",
    "AssetTransferView",
    "AssetTransactionListView",
    "DepreciationRunView",
    "health_simple",
    "health_detailed",
    "VoucherListView",
    "VoucherCreateView",
    "VoucherDetailView",
    "VoucherDeleteView",
    "VoucherExportView",
    "TrialBalanceView",
    "BalanceSheetView",
    "PnLView",
    "VATReturnView",
    "GeneralJournalView",
    "GeneralLedgerView",
    "CustomerListView",
    "CustomerCreateView",
    "CustomerUpdateView",
    "CustomerExportView",
    "CustomerDeleteView",
    "VendorListView",
    "VendorCreateView",
    "VendorUpdateView",
    "VendorExportView",
    "VendorDeleteView",
    "ProductListView",
    "ProductCreateView",
    "ProductUpdateView",
    "ProductDetailView",
    "ProductExportView",
    "ProductDeleteView",
    "SalesInvoiceListView",
    "SalesInvoiceCreateView",
    "PurchaseInvoiceListView",
    "PurchaseInvoiceCreateView",
    "StockVoucherListView",
    "StockVoucherCreateView",
    "StockDashboardView",
    "StockAdjustmentListView",
    "StockAdjustmentCreateView",
    "StockCardView",
    "EmployeeListView",
    "EmployeeCreateView",
    "PayrollRunView",
    "CashReceiptCreateView",
    "CashPaymentCreateView",
    "ContractListView",
    "ContractCreateView",
    "ContractTemplateListView",
    "ContractGenerateView",
    "ContractTemplatePreviewView",
    "InputInvoiceListView",
    "InputInvoiceUploadView",
    "InputInvoiceProcessView",
    "RecurringListView",
    "RecurringRunView",
    # HR reports & management (Task 4 + 5)
    "D62ReportView",
    "LaborUsageReportView",
    "SalaryFundReportView",
    "PITMonthlyReportView",
    "LaborContractListView",
    "LaborContractCreateView",
    "DependentListView",
    "LeaveRequestView",
    "InsuranceDashboardView",
    # Project Management
    "ProjectListView",
    "ProjectCreateView",
    "ProjectDetailView",
    "ProjectAddPhaseView",
    "ProjectTogglePhaseView",
    "ProjectAddResourceView",
    # CRM
    "LeadListView",
    "LeadCreateView",
    "AccountCreateView",
    "OpportunityListView",
    "OpportunityCreateView",
    "OpportunityDetailView",
    "OpportunityConvertView",
    "TicketListView",
    "TicketCreateView",
    "CampaignListView",
    "CampaignCreateView",
]
