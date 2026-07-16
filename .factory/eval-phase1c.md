# Phase 1C — Coverage Matrix

> Auto-scope evaluation of Visota ERP (C:\mmm\visota).
> Method: traced FK relationships across model files, `from apps.X` import
> statements in service layers, signal receivers, and URL routing.
> No Phase 1A/1B artifacts existed at time of writing; all discovery done
> from source.

## Table C — Module × Workflow Matrix

Legend: **X** = direct participation (FK, service call, signal, or URL);
**x** = indirect / read-only participation (e.g. reporting reads model).

Workflows (columns):

1. **Auth & Tenancy** — login, company switch, RBAC, user management
1. **Sales / AR** — sales invoice → GL voucher → e-invoice
1. **Purchasing / AP** — purchase invoice → GL voucher
1. **Inventory** — stock receipt/issue/transfer → GL voucher
1. **GL & Voucher Posting** — core accounting engine (the hub)
1. **DNSN (TT58) Ledger** — dual-entry DNSN voucher + balance conversion
1. **Period Close** — KC → 911 → 421, period lock
7. **Payroll & HR** — employee, insurance, salary calc → GL voucher
8. **Fixed Assets** — depreciation, lifecycle → GL voucher
9. **FX Revaluation** — period-end FX revaluation → GL voucher
10. **Banking & Reconciliation** — statement import, auto-match
11. **Budget & Cash Flow** — budget variance, cash flow projection
12. **Costing** — cost collection, costing, allocation → GL
13. **Reporting** — P&L, BS, CFS, VAT return, DNSN report, HR report
14. **Contracts** — contract lifecycle, templates, print
15. **Projects** — project, phases, resources, transactions
16. **CRM** — leads, opportunities, conversion to contract+invoice
17. **Bidding** — bid opportunities → contract conversion
18. **Loans** — bank loan disbursement, repayment, interest → GL
19. **Guarantees** — bank guarantee issuance, release → GL
20. **E-Invoice** — issue, publish, PDF, XML per ND 254/2026
21. **Input Doc Capture** — OCR/XML extraction → auto-create purchase invoice
22. **Recurring / Automation** — template-based recurring runners
23. **Approvals** — approval chain on any object before posting
24. **PKM** — personal knowledge management / RAG / LLM
25. **Notifications** — in-app + email notifications
26. **Documents** — attachments, voucher docs, print, docx export
27. **Public / Marketing** — landing page, blog, contact form

| App \ WF | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **core** | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X |
| **identity** | X | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | X | X | x | x | X |
| **master_data** | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | x | x | x | X |
| **ledger** | x | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | x |
| **ui_modern** | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X |
| **sales** | x | X | | | X | X | X | | X | | | X | x | | | X | | | | X | | X | X | | | | |
| **purchasing** | x | | X | | X | X | X | | X | | | X | x | | | | | | | | X | X | X | | | | |
| **inventory** | x | | | X | X | | X | | | | | X | x | | | | | | | | | X | | | | | |
| **hr** | x | | | | X | | X | X | | | | | X | | X | | | | | | | X | | | | | |
| **payroll** | x | | | | X | | X | X | | | | | X | | | | | | | | | X | X | | | | |
| **assets** | x | | | | X | | X | X | | | | | x | | | | | | | | | X | X | | | | |
| **costing** | x | | | | X | | X | | | | | X | x | | X | | | | | | | X | | | | | |
| **fx** | x | | | | X | | X | | X | | | | x | | | | | | | | | X | | | | | |
| **banking** | x | x | x | | X | | X | | X | X | | | x | | | | | X | X | X | | X | | | | | |
| **budget** | x | | | | X | | X | | | | X | | x | | | | | | | | | X | | | | | |
| **reporting** | x | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | X | x | X | X | x | x | x | |
| **contracts** | x | | | | | | | | | | | | x | X | X | X | X | X | X | | | | X | | | X | |
| **projects** | x | | | x | | | | x | | | | X | x | X | X | | X | | | | | X | | | | | |
| **crm** | x | x | | | | | | | | | | | x | X | X | X | | | | | | | | | | | |
| **bidding** | x | | | | | | | | | | | | x | X | | | X | | | | | X | | | | | |
| **loans** | x | | | | X | | X | | X | | | | x | X | | | | X | | | | X | | | | | |
| **guarantees** | x | | | | X | | X | | X | | | | x | X | | | | | X | | | X | | | | | |
| **einvoice** | x | X | | | | | | | | | | | x | | | x | | | | X | | X | | X | | | |
| **input_docs** | x | | X | | X | | | | | | | | x | | | | | | | | X | X | | | | | |
| **recurring** | x | | | | X | X | X | X | | | | | | | | | | | | | | X | X | | | | |
| **approvals** | x | x | x | x | X | X | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | x | X | | X | | | |
| **notifications** | x | x | x | x | X | x | x | x | x | x | x | x | x | x | x | x | x | x | x | X | x | x | X | x | X | x | X |
| **documents** | x | x | x | x | X | x | x | x | x | x | x | x | x | X | x | x | x | x | x | x | x | x | x | x | x | X | x |
| **pkm** | X | | | | | | | | | | | | | | | | | | | | | | | X | x | | |
| **public** | X | | | | | | | | | | | | | | | | | | | | | | | | x | | X |

## Cross-App Connection Points

| # | Connection | Apps Involved | Type (FK/Signal/Service/URL) | Risk Level | Description |
|---|---|---|---|---|---|
| 1 | `VoucherPostingService.post()` | ledger, notifications, approvals | Service | **Critical** | Central posting hub. Calls NotificationService on post; approvals gate posting. Every domain app depends on this. |
| 2 | `SalesInvoiceService.create()` → ledger | sales, ledger, master_data, core | Service + FK | **Critical** | Creates SalesInvoice + AccountingVoucher + DnsnVoucher in one `@transaction.atomic`. FK: `SalesInvoice.gl_voucher → ledger.AccountingVoucher`. |
| 3 | `PurchaseInvoiceService.create()` → ledger | purchasing, ledger, master_data, core | Service + FK | **Critical** | Mirror of sales. Creates PurchaseInvoice + AccountingVoucher + DnsnVoucher atomically. |
| 4 | `PayrollService.calculate()` → ledger | payroll, hr, ledger, core | Service + FK | **High** | Reads Employee + InsuranceContribution from hr; posts GL voucher. FK: `PayrollRun.gl_voucher → ledger`. |
| 5 | `DepreciationService` → ledger | assets, ledger | Service + FK | **High** | Posts depreciation voucher. FK: `AssetDepreciation.gl_voucher → ledger`. Recurring runner triggers this. |
| 6 | `OpportunityConverter.convert()` | crm, master_data, contracts, projects, sales | Service | **Critical** | Single `@transaction.atomic` creates Customer + Contract + Project + SalesInvoice. 5-app cascade. |
| 7 | `BidConverterService.convert_to_contract()` | bidding, contracts | Service + FK | **High** | Bid WON → Contract creation. FK: `BidResult.contract → contracts.Contract`. |
| 8 | `EInvoiceService.issue_from_sales_invoice()` | einvoice, sales, notifications | Service + FK | **High** | Generates XML from SalesInvoice; sends notification. Cross-domain: sales → einvoice → notifications. |
| 9 | `InvoiceExtractionService` → purchasing | input_docs, purchasing, master_data | Service + FK | **High** | Parses uploaded invoice XML/OCR, auto-creates PurchaseInvoice via `PurchaseInvoiceService`. FK: `InputInvoice.purchase_invoice → purchasing.PurchaseInvoice`. |
| 10 | `ApprovalService` → ledger posting | approvals, ledger, identity, notifications | Service + Generic FK | **Critical** | Approval uses ContentType generic FK to any object. On final approval, can trigger `VoucherPostingService.post()`. |
| 11 | `FxRevaluationService` → ledger | fx, ledger | Service + FK | **High** | Period-end FX revaluation posts GL voucher. FK: `FxRevaluation.gl_voucher → ledger` and `reversal_voucher → ledger`. |
| 12 | Bank loan lifecycle → ledger | loans, contracts, ledger | Service + FK | **High** | Disbursement, repayment, interest accrual all post GL vouchers. FK: `BankLoan.contract → contracts.Contract`, 3× `gl_voucher → ledger`. |
| 13 | Bank guarantee lifecycle → ledger | guarantees, contracts, ledger | Service + FK | **Medium** | Guarantee issuance + release post GL vouchers. FK: `BankGuarantee.contract → contracts.Contract`, `gl_voucher → ledger`, `release_voucher → ledger`. |
| 14 | `RecurringService` runners | recurring, assets, payroll, ledger | Service | **High** | Dotted-path runner callables import and invoke DepreciationService, PayrollService, PeriodClosingService. |
| 15 | `PeriodClosingService` | ledger, reporting | Service | **High** | KC → 911 → 421 closing entries; calls DnsnReportService from reporting during close. |
| 16 | `DnsnPostingService` + `BalanceConversionService` | ledger, core | Service | **High** | TT58 dual-entry: converts AccountPeriodBalance ↔ DnsnLedgerBalance. Core seed_demo calls DnsnPostingService. |
| 17 | Bank reconciliation matching | banking, sales, einvoice, ledger | Service + Generic FK | **High** | `ReconciliationMatch` uses ContentType generic FK to match BankTransaction against SalesInvoice or EInvoice. Auto-creates GL voucher. |
| 18 | `AttachmentService` (generic attachments) | documents, all domain apps | Service + Generic FK | **Medium** | ContentType-based attachments used by contracts, crm, projects, ledger, sales, purchasing. |
| 19 | Reporting formula engine | reporting, ledger, hr, payroll | Service | **High** | `ReportEngine` reads `AccountPeriodBalance` + `VoucherLine` from ledger; HR reports read Employee + PayrollRun. |
| 20 | Budget variance refresh | budget, ledger | Service | **Medium** | `BudgetVarianceService.refresh_actuals()` queries `AccountPeriodBalance` for each budget line. |
| 21 | `CostingService` → ledger | costing, ledger, projects | Service | **Medium** | Reads VoucherLine for TK 621/622/623; allocates cost to projects. |
| 22 | PKM signal handlers | pkm, identity, core | Signal | **Low** | `post_save` on KnowledgeNote / PKMDocument triggers interaction logging. PKM middleware logs all interactions. |
| 23 | Notifications → identity | notifications, identity | Service | **Medium** | `NotificationService` resolves Role + UserCompanyRole for targeting. Used by approvals, einvoice, banking, bidding, ledger. |
| 24 | Public signup → identity + notifications | public, identity, core, notifications | Service + URL | **Medium** | Public registration creates User + UserCompanyRole + Company; sends welcome email via NotificationService. |
| 25 | Documents print/export → contracts + ledger | documents, contracts, ledger | Service | **Medium** | `DocxExportService` and `ContractPrintService` render Contract + AccountingVoucher data to DOCX/PDF. |
| 26 | Inventory → GL voucher | inventory, ledger, master_data | Service + FK | **High** | StockVoucher posts GL voucher. FK: `StockVoucher.gl_voucher → ledger`. StockLedger tracks movements. |
| 27 | Project resource allocation → inventory | projects, hr, master_data, contracts | Service + FK | **Medium** | ProjectResource links Employee + Product; ProjectTransaction tracks usage. |

## Hot Spots (3+ apps converge)

These workflows require **joint cross-app review** in Phase 2 because failures
can cascade across module boundaries.

### Hot Spot 1: Voucher Posting Pipeline (9 apps)
**Apps:** ledger (hub), sales, purchasing, inventory, payroll, assets, fx, banking, approvals, notifications
**Why critical:** `VoucherPostingService.post()` is the single point through which
all financial transactions enter the GL. It validates balance, updates
`AccountPeriodBalance`, fires notifications, and is gated by approvals.
Any bug here corrupts the entire accounting system.
**Joint review needed:** ledger + approvals + notifications + at least one
consumer from each domain (sales, purchasing, payroll, assets).

### Hot Spot 2: CRM Opportunity → Full Chain Conversion (6 apps)
**Apps:** crm, master_data, contracts, projects, sales, (ledger via sales)
**Why critical:** `OpportunityConverter.convert()` creates Customer + Contract +
Project + SalesInvoice in one atomic transaction. A failure mid-chain leaves
partial data. The SalesInvoice creation cascades into ledger voucher posting.
**Joint review needed:** crm + contracts + projects + sales.

### Hot Spot 3: DNSN / TT58 Dual-Entry System (5 apps)
**Apps:** ledger (hub), core, sales, purchasing, reporting
**Why critical:** TT58 companies maintain a parallel DNSN ledger alongside GL.
Every sales/purchase invoice creates both `AccountingVoucher` and `DnsnVoucher`.
`BalanceConversionService` converts between the two. Reporting reads both.
Data integrity between the two ledgers is paramount.
**Joint review needed:** ledger (DNSN models + posting + conversion) + sales +
purchasing + reporting (DNSN report).

### Hot Spot 4: Period Close Orchestration (6 apps)
**Apps:** ledger, reporting, recurring, assets, payroll, fx
**Why critical:** `PeriodClosingService.close_period()` runs KC entries. The
recurring runner orchestrates depreciation + payroll + closing in sequence.
FX revaluation must happen before close. Reporting's DnsnReportService is
called during close. Ordering dependencies are critical.
**Joint review needed:** ledger (period closing) + recurring (runners) + fx +
reporting (dnsn report).

### Hot Spot 5: E-Invoice Issuance Chain (4 apps)
**Apps:** einvoice, sales, notifications, banking
**Why critical:** E-invoice issuance reads SalesInvoice data, generates XML per
ND 254/2026, sends notifications, and banking reconciliation matches against
e-invoices. Incorrect invoice data propagates to tax authority submissions.
**Joint review needed:** einvoice + sales + notifications.

### Hot Spot 6: Bank Reconciliation (5 apps)
**Apps:** banking, ledger, sales, einvoice, approvals
**Why critical:** Bank statement import parses external data; auto-matching uses
generic FK to link transactions to SalesInvoice / EInvoice; matched items can
trigger GL voucher creation. Approval may gate reconciliation posting.
**Joint review needed:** banking + ledger + (sales or einvoice).

### Hot Spot 7: Input Doc Capture → Purchasing (4 apps)
**Apps:** input_docs, purchasing, master_data, ledger
**Why critical:** Invoice extraction service parses Vietnamese invoice XML/OCR
and auto-creates PurchaseInvoice + GL voucher. Incorrect extraction creates
wrong accounting entries. Vendor matching relies on master_data.
**Joint review needed:** input_docs + purchasing + master_data.

### Hot Spot 8: Recurring Automation Engine (5 apps)
**Apps:** recurring, assets, payroll, ledger, notifications
**Why critical:** Recurring templates use dotted-path runner callables that
import and invoke services from assets (depreciation), payroll, and ledger
(period closing). These run unattended; failures are silent. Notification
integration needed for failure alerts.
**Joint review needed:** recurring + assets + payroll + ledger.

### Hot Spot 9: Approval Workflow (6+ apps)
**Apps:** approvals, ledger, identity, notifications, (any app with postable objects)
**Why critical:** Approval uses ContentType generic FK — it can wrap ANY model.
On final approval it can trigger `VoucherPostingService.post()`. The generic
nature means a bug affects sales, purchasing, payroll, assets, fx, banking,
loans, and guarantees indiscriminately.
**Joint review needed:** approvals + ledger + identity + notifications.

## Recommended Subagent Boundaries

For Phase 2 review, split **by workflow group** (not by app) to ensure cross-app
connections are reviewed holistically within each subagent.

### Group A: Core Accounting Engine
**Apps:** ledger (all models + all services), core (services only)
**Focus:** VoucherPostingService, DnsnPostingService, BalanceConversionService,
PeriodClosingService. Balance calculation, status transitions, locking.
**Size:** ~8 source files

### Group B: Revenue Cycle (Sales → E-Invoice → Banking)
**Apps:** sales (models + services), einvoice (models + services), banking (reconciliation only)
**Focus:** SalesInvoiceService, EInvoiceService, BankReconciliationService.
Tax calculation, VAT methods, e-invoice XML generation, reconciliation matching.
**Size:** ~10 source files

### Group C: Procurement & Input Capture
**Apps:** purchasing (models + services), input_docs (models + services)
**Focus:** PurchaseInvoiceService, InvoiceExtractionService. Vendor matching,
XML/OCR parsing, auto-voucher creation.
**Size:** ~5 source files

### Group D: HR, Payroll & Insurance
**Apps:** hr (models + services), payroll (models + services)
**Focus:** PayrollService, InsuranceService. PIT calculation, insurance
contributions, salary → GL voucher posting.
**Size:** ~6 source files

### Group E: Fixed Assets & Costing
**Apps:** assets (models + services), costing (services), inventory (models + services)
**Focus:** DepreciationService, AssetLifecycleService, CostingService,
StockService. Depreciation calc, asset transactions, stock movements, cost allocation.
**Size:** ~10 source files

### Group F: Financial Close & FX
**Apps:** fx (models + services), recurring (models + services + runners), budget (models + services)
**Focus:** FxRevaluationService, RecurringService + runners, BudgetVarianceService.
Period-end revaluation, recurring automation, budget variance.
**Size:** ~8 source files

### Group G: CRM → Project → Contract Lifecycle
**Apps:** crm (models + services), projects (models + services), contracts (models + services), bidding (models + services), loans (models), guarantees (models)
**Focus:** OpportunityConverter, ProjectService, ContractPrintService,
BidConverterService. Multi-object atomic creation, contract lifecycle.
**Size:** ~12 source files

### Group H: Reporting & Compliance
**Apps:** reporting (all services), core (tndn + tax config services)
**Focus:** PnLService, BalanceSheetService, CashFlowService, VATReturnService,
DnsnReportService, ReportEngine/formula_parser. Report formula evaluation,
VAT return, financial statement generation.
**Size:** ~10 source files

### Group I: Platform & Cross-Cutting
**Apps:** identity (models + services), notifications (models + services), approvals (models + services), documents (models + services), core (models + middleware + module_config)
**Focus:** UserService, NotificationService, ApprovalService, AttachmentService,
DocumentService. RBAC, permission checks, generic approval workflow, attachment system.
**Size:** ~12 source files

### Group J: PKM & Public (Low coupling)
**Apps:** pkm (all), public (all)
**Focus:** RAG pipeline, LLM service, encryption, signal handlers. Public
signup flow. These are the most isolated modules.
**Size:** ~12 source files

---

**Summary:** 30 apps mapped across 27 workflows. 9 hot spots identified where
3+ apps converge. 27 cross-app connection points catalogued. Recommended 10
Phase 2 subagent groups organized by workflow rather than by individual app,
ensuring each group stays under ~12 source files for effective review.
