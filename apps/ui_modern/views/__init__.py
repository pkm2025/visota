from apps.approvals.views import (
    ApprovalApproveView,
    ApprovalDetailView,
    ApprovalQueueView,
    ApprovalRejectView,
    ApprovalRuleListView,
)
from apps.banking.views import (
    BankAccountListView,
    BankReconciliationRunView,
    BankReconciliationView,
    BankStatementImportDetailView,
    BankStatementImportListView,
    BankStatementUploadView,
    VietQRModalView,
)
from apps.bidding.views import (
    BidConvertToContractView,
    BidOpportunityDetailView,
    BidOpportunityListView,
)
from apps.budget.views import (
    BudgetDetailView,
    BudgetGenerateView,
    BudgetListView,
    BudgetRefreshActualsView,
    CashFlowGenerateView,
    CashFlowView,
)
from apps.einvoice.views import (
    EInvoiceCancelView,
    EInvoiceDetailView,
    EInvoiceIssueFromSalesView,
    EInvoiceJsonDownloadView,
    EInvoiceListView,
    EInvoicePublishView,
    EInvoiceReportView,
    EInvoiceXmlDownloadView,
)
from apps.fx.views import (
    ExchangeRateListView,
    FxRevaluationListView,
    FxRevaluationRunView,
)
from apps.guarantees.views import BankGuaranteeListView
from apps.loans.views import BankLoanListView
from apps.public.views import ContactListAdminView

from .admin_views import (
    AdminRoleEditView,
    AdminRoleListView,
    AdminUserAssignView,
    AdminUserListView,
    MyPermissionsView,
)
from .asset_views import (
    AssetCreateView,
    AssetDisposeView,
    AssetListView,
    AssetTransactionListView,
    AssetTransferView,
    DepreciationRunView,
)
from .attachment_views import (
    AttachmentDeleteView,
    AttachmentDownloadView,
    AttachmentUploadView,
)
from .auth_views import VisotaLoginView, VisotaLogoutView
from .chart_of_accounts_views import (
    ChartOfAccountsChangeCodeView,
    ChartOfAccountsListView,
    ChartOfAccountsSeedView,
)
from .closing_views import PeriodClosingView
from .company_views import CompanyProfileView
from .contract_template_views import (
    ContractGenerateView,
    ContractTemplateCreateView,
    ContractTemplateDeleteView,
    ContractTemplateEditView,
    ContractTemplateListView,
    ContractTemplatePreviewRawView,
    ContractTemplatePreviewView,
    ContractWizardView,
)
from .contract_views import ContractCreateView, ContractDetailView, ContractListView
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
from .dashboard_views import DashboardView, QuickExpenseView
from .dnsn_ledger_views import (
    DnsnLedgerDetailView,
    DnsnLedgerListView,
    DnsnLedgerSettingsView,
)
from .dnsn_report_views import (
    DnsnB01ReportView,
    DnsnB02ReportView,
    DnsnReportExportView,
    DnsnReportListView,
)
from .dnsn_conversion_views import (
    DnsnConversionResultView,
    DnsnConversionView,
)
from .dnsn_voucher_views import (
    DnsnVoucherCreateView,
    DnsnVoucherDeleteView,
    DnsnVoucherDetailView,
    DnsnVoucherEditView,
    DnsnVoucherListView,
)
from .document_views import (
    ContractEmailView,
    ContractExportDocxView,
    DocumentDeleteView,
    DocumentDownloadView,
    TrialBalanceDocxView,
    VoucherEmailView,
    VoucherPrintDocxView,
    VoucherPrintView,
    VoucherUploadView,
)
from .einvoice_pdf_view import EinvoicePDFView
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
    VoucherGuidedView,
    VoucherListView,
)
from .migration_views import MigrationTemplateView, MigrationUploadView
from .payroll_views import PayrollRunView
from .pkm_views import (
    DocumentDeleteView,
    DocumentDetailView,
    DocumentListView,
    DocumentReprocessView,
    DocumentStatusBadgeView,
    DocumentUploadView,
    KnowledgeNoteCreateView,
    KnowledgeNoteDeleteView,
    KnowledgeNoteDetailView,
    KnowledgeNoteListView,
    KnowledgeNoteUpdateView,
    LLMConfigCreateView,
    LLMConfigDeleteView,
    LLMConfigListView,
    LLMConfigUpdateView,
    PKMDashboardView,
    PKMSearchView,
    QAChatView,
)
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
from .report_export_views import ReportExportView
from .report_views import (
    BalanceSheetView,
    D62ReportView,
    GeneralJournalView,
    GeneralLedgerView,
    LaborUsageReportView,
    PITMonthlyReportView,
    PnLView,
    SalaryFundReportView,
    SubLedgerView,
    TrialBalanceView,
    VATReturnView,
)
from .sales_views import (
    SalesInvoiceCreateView,
    SalesInvoiceListView,
)
from .search_views import GlobalSearchView, SearchClickView
from .stock_views import (
    StockAdjustmentCreateView,
    StockAdjustmentListView,
    StockCardView,
    StockDashboardView,
    StockVoucherCreateView,
    StockVoucherListView,
)
from .treasury_views import CashPaymentCreateView, CashReceiptCreateView
from .vat_list_views import VATInputListView, VATOutputListView
from .vat_xml_views import VATXmlView
from .vendor_views import (
    VendorCreateView,
    VendorDeleteView,
    VendorExportView,
    VendorListView,
    VendorUpdateView,
)

__all__ = [
    "DashboardView",
    "QuickExpenseView",
    "DnsnVoucherListView",
    "DnsnVoucherCreateView",
    "DnsnVoucherDetailView",
    "DnsnVoucherEditView",
    "DnsnVoucherDeleteView",
    "DnsnLedgerListView",
    "DnsnLedgerDetailView",
    "DnsnLedgerSettingsView",
    "DnsnReportListView",
    "DnsnB01ReportView",
    "DnsnB02ReportView",
    "DnsnReportExportView",
    "DnsnConversionView",
    "DnsnConversionResultView",
    "ChartOfAccountsListView",
    "ChartOfAccountsChangeCodeView",
    "ChartOfAccountsSeedView",
    "VisotaLoginView",
    "VisotaLogoutView",
    "CompanyProfileView",
    "ContactListAdminView",
    "MigrationUploadView",
    "MigrationTemplateView",
    "PeriodClosingView",
    "MyPermissionsView",
    "AdminRoleListView",
    "AdminRoleEditView",
    "AdminUserListView",
    "AdminUserAssignView",
    "ApprovalQueueView",
    "ApprovalDetailView",
    "ApprovalApproveView",
    "ApprovalRejectView",
    "ApprovalRuleListView",
    "EInvoiceListView",
    "EInvoiceDetailView",
    "EInvoiceIssueFromSalesView",
    "EInvoicePublishView",
    "EInvoiceCancelView",
    "EInvoiceXmlDownloadView",
    "EInvoiceJsonDownloadView",
    "EInvoiceReportView",
    "EinvoicePDFView",
    "BankAccountListView",
    "BankStatementImportListView",
    "BankStatementUploadView",
    "BankStatementImportDetailView",
    "BankReconciliationView",
    "BankReconciliationRunView",
    "VietQRModalView",
    "BankGuaranteeListView",
    "BankLoanListView",
    "BidOpportunityListView",
    "BidOpportunityDetailView",
    "BidConvertToContractView",
    "BudgetListView",
    "BudgetDetailView",
    "BudgetGenerateView",
    "BudgetRefreshActualsView",
    "CashFlowView",
    "CashFlowGenerateView",
    "ExchangeRateListView",
    "FxRevaluationListView",
    "FxRevaluationRunView",
    "AttachmentUploadView",
    "AttachmentDeleteView",
    "AttachmentDownloadView",
    "DocumentDeleteView",
    "DocumentDownloadView",
    "VoucherPrintView",
    "VoucherPrintDocxView",
    "VoucherEmailView",
    "ContractExportDocxView",
    "ContractEmailView",
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
    "VoucherGuidedView",
    "VoucherDetailView",
    "VoucherDeleteView",
    "VoucherExportView",
    "TrialBalanceView",
    "BalanceSheetView",
    "PnLView",
    "VATReturnView",
    "VATXmlView",
    "VATInputListView",
    "VATOutputListView",
    "ReportExportView",
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
    "GlobalSearchView",
    "SearchClickView",
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
    "ContractDetailView",
    "ContractTemplateListView",
    "ContractTemplateCreateView",
    "ContractTemplateEditView",
    "ContractTemplateDeleteView",
    "ContractTemplatePreviewRawView",
    "ContractTemplatePreviewView",
    "ContractGenerateView",
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
    # PKM (Personal Knowledge Management)
    "PKMDashboardView",
    "KnowledgeNoteListView",
    "KnowledgeNoteDetailView",
    "KnowledgeNoteCreateView",
    "KnowledgeNoteUpdateView",
    "KnowledgeNoteDeleteView",
    "PKMSearchView",
    "QAChatView",
    "LLMConfigListView",
    "LLMConfigCreateView",
    "LLMConfigUpdateView",
    "LLMConfigDeleteView",
    "DocumentListView",
    "DocumentUploadView",
    "DocumentDetailView",
    "DocumentDeleteView",
    "DocumentStatusBadgeView",
    "DocumentReprocessView",
]
from .cash_flow_views import CashFlowDirectView, CashFlowIndirectView
from .costing_views import CostReportView
from .ctgs_views import (
    CTGSCheckView,
    CTGSCreateView,
    CTGSRegisterView,
    DepartmentMasterView,
    SourceDocScheduleView,
)
from .detail_book_views import BankBookView, CashBookView, SalesDetailView
from .help_views import HelpDetailView, HelpIndexView
from .report_views import BookEntryRegisterView
from .specialized_journal_views import (
    CashPaymentJournalView,
    CashReceiptJournalView,
    PurchaseJournalView,
    SalesJournalView,
    TAccountSummaryView,
)
from .tool_views import (
    ClosingEntryDeclarationView,
    CustomerOpeningBalanceView,
    InvoiceOpeningBalanceView,
    PeriodAllocationView,
    VoucherRenumberView,
    YearEndCarryForwardView,
)
