# Phase 1B — Business Workflow Discovery

Source: URL patterns (`config/urls.py`, `apps/ui_modern/urls.py`, and 10 app-level
`urls.py`), `apps/pkm/signals.py`, 16 management commands,
`templates/modern/base/layout.html` sidebar, django-ninja API
(`apps/core/api.py`, `apps/pkm/api.py`, `apps/ledger/dnsn_api.py`).

Portal routing (from `config/urls.py`):
- `/auth/login/`, `/auth/logout/` — Django auth (VisotaLoginView / VisotaLogoutView).
- `/` — Public marketing site (`apps.public`): landing, blog, signup, contact,
  newsletter, legal pages.
- `/modern/` — Main authenticated ERP application (`apps.ui_modern`). All
  business workflows below live under this prefix and require `login_required`.
- `/api/v1/` — django-ninja REST API (session or `X-API-Key`).
- `/admin/` — Django admin.
- `/notifications/` — Notification inbox (per-user, cross-company).
- `/switch-company/` — Tenant switcher (CompanySwitchView).
- `/health/`, `/health/detailed/` — Health checks.

There is no separate role-keyed portal; the ERP is a single SPA-like app under
`/modern/` whose sidebar is permission-gated per-module via the
`has_module_access` template tag, so each user sees only the workflows their
role grants.

## Table B — Business Workflow Inventory

| # | Workflow Group | Portal(s) | Owning App(s) | Representative Path | One-line Use Case | Has Side Effects (signal) | Has Batch (cmd) |
|---|----------------|-----------|----------------|---------------------|-------------------|---------------------------|-----------------|
| 1 | Dashboard & global search | ERP | ui_modern | `/modern/`, `/modern/search/` | Home dashboard + "Super Search" across customers/products/vouchers | No | No |
| 2 | Quick expense | ERP | ui_modern, ledger | `/modern/quick-expense/` | One-click expense voucher from dashboard | No (delegates to VoucherPostingService) | No |
| 3 | Company switcher / tenant | ERP | ui_modern, core | `/switch-company/` | Switch active company context | No | No |
| 4 | Admin: roles & permissions | ERP | identity, ui_modern | `/modern/admin/roles/`, `/modern/admin/users/` | Manage roles, assign users, view my permissions | No | Yes — `seed_permissions` |
| 5 | Company profile | ERP | core, ui_modern | `/modern/admin/company-profile/` | Edit company master data (regime, tax method) | No | Yes — `create_demo_company` |
| 6 | Contact requests (public) | Public + ERP | public, ui_modern | `/contact/submit/`, `/modern/admin/contacts/` | Landing-page contact form → admin inbox | No | No |
| 7 | Migration tool | ERP | ui_modern | `/modern/admin/migration/` | Upload legacy chart-of-accounts / balances | No | No |
| 8 | Approvals workflow | ERP | approvals, ui_modern | `/modern/approvals/`, `…/approve/`, `…/reject/` | Queue, approve, reject documents; manage rules | No | No |
| 9 | E-invoice (HĐĐT) | ERP | einvoice, ui_modern | `/modern/einvoices/`, `…/publish/`, `…/cancel/` | Issue, publish, cancel e-invoices; XML/JSON/PDF download; report | No (explicit `EInvoiceService` calls) | No |
| 10 | Banking & reconciliation | ERP | banking, ui_modern | `/modern/banking/reconcile/run/` | Upload bank statements, auto-reconcile | No | No |
| 11 | VietQR | ERP | banking, ui_modern | `/modern/banking/vietqr/…/` | Generate QR code for invoice payment | No | No |
| 12 | Bank guarantees | ERP | guarantees, ui_modern | `/modern/guarantees/` | List bank guarantees | No | No |
| 13 | Bank loans | ERP | loans, ui_modern | `/modern/loans/` | List bank loans | No | No |
| 14 | Bidding opportunities | ERP | bidding, ui_modern | `/modern/bidding/`, `…/convert-to-contract/` | Track bid opportunities and convert to contracts | No | No |
| 15 | Budget | ERP | budget, ui_modern | `/modern/budget/generate/`, `…/refresh/` | Generate budgets, refresh actuals | No | No |
| 16 | Cash flow projection | ERP | budget, ui_modern | `/modern/cash-flow/generate/` | Generate direct/indirect cash flow forecasts | No | No |
| 17 | FX rates | ERP | fx, ui_modern | `/modern/fx/rates/` | Maintain exchange rates | No | No |
| 18 | FX revaluation | ERP | fx, ui_modern | `/modern/fx/revaluation/run/` | Run period-end FX revaluation | No | No |
| 19 | Accounting vouchers (phiếu KC) | ERP | ledger, ui_modern | `/modern/vouchers/`, `/modern/vouchers/new/`, `…/guided/` | Create / list / detail / print / DOCX / email / export / delete vouchers | Yes via `VoucherPostingService.post` (programmatic, not Django signal) | No |
| 20 | Voucher renumbering | ERP | ledger, ui_modern | `/modern/tools/voucher-renumber/` | Re-sequence voucher numbers for a period | No | No |
| 21 | DNSN (TT58) vouchers | ERP | ledger, ui_modern | `/modern/dnsn-vouchers/`, `…/new/`, `…/edit/`, `…/delete/` | CRUD for TT58 "Đơn vị sự nghiệp" vouchers | No (uses `DnsnPostingService`) | No |
| 22 | DNSN ledgers (TT58) | ERP | ledger, ui_modern | `/modern/dnsn-ledgers/`, `…/settings/`, `…/<ledger_type>/` | List S1/S2/S3/S4-DNSN ledgers; configure optional S4 ledgers | No | No |
| 23 | DNSN reports (TT58) | ERP | reporting, ui_modern | `/modern/dnsn-reports/b01-dnsn/`, `…/b02-dnsn/`, `…/export/` | B01/B02-DNSN financial statements + export | No | No |
| 24 | DNSN balance conversion | ERP | ledger, ui_modern | `/modern/dnsn-conversion/`, `…/result/` | Convert TT133/TT200 balances to TT58 (BalanceConversionService) | No | No |
| 25 | Reports — trial balance | ERP | reporting, ui_modern | `/modern/reports/trial-balance/`, `…/docx/` | Cân đối số phát sinh + DOCX export | No | No |
| 26 | Reports — balance sheet (B01) | ERP | reporting, ui_modern | `/modern/reports/balance-sheet/` | B01-DN financial position statement | No | No |
| 27 | Reports — P&L (B02) | ERP | reporting, ui_modern | `/modern/reports/pnl/` | B02-DN income statement | No | No |
| 28 | Reports — VAT return (01) | ERP | reporting, ui_modern | `/modern/reports/vat-return/`, `…-xml/` | VAT declaration + XML submission file | No | No |
| 29 | Reports — VAT input/output lists | ERP | reporting, ui_modern | `/modern/reports/vat-input-list/`, `…/vat-output-list/` | Bảng kê hóa đơn đầu vào / đầu ra | No | No |
| 30 | Reports — general journal & ledger | ERP | reporting, ui_modern | `/modern/reports/general-journal/`, `…/general-ledger/` | Nhật ký chung + Sổ cái TK | No | No |
| 31 | Reports — D62 / labor / salary / PIT | ERP | reporting, ui_modern | `/modern/reports/d62/`, `…/labor-usage/`, `…/salary-fund/`, `…/pit-monthly/` | HR/tax regulatory reports | No | No |
| 32 | Reports — sub-ledger & cost | ERP | reporting, ui_modern, costing | `/modern/reports/sub-ledger/`, `…/cost/` | Sổ chi tiết KH/NCC + bảng tính giá thành | No | No |
| 33 | Reports — book-entry register (S02a) | ERP | reporting, ui_modern | `/modern/reports/book-entry-register/` | Sổ đăng ký chứng từ ghi sổ | No | No |
| 34 | Reports — specialised journals | ERP | reporting, ui_modern | `/modern/reports/journal/cash-receipt/`, `…/cash-payment/`, `…/sales/`, `…/purchase/` | S03a1/a2/a3/a4-DN specialised journals | No | No |
| 35 | Reports — T-account summary | ERP | reporting, ui_modern | `/modern/reports/t-account/` | Sổ chữ T tài khoản | No | No |
| 36 | Reports — cash book (S07) & bank book (S08) | ERP | reporting, ui_modern | `/modern/reports/cash-book/`, `…/bank-book/` | Sổ quỹ tiền mặt + Sổ tiền gửi ngân hàng | No | No |
| 37 | Reports — sales detail (S35) | ERP | reporting, ui_modern | `/modern/reports/sales-detail/` | Sổ chi tiết bán hàng | No | No |
| 38 | Reports — cash flow direct/indirect (B03) | ERP | reporting, ui_modern | `/modern/reports/cash-flow/direct/`, `…/indirect/` | B03-DN cash flow statement | No | No |
| 39 | Report export (generic) | ERP | reporting, ui_modern | `/modern/reports/export/` | VAL-M3-008..015 PDF/Excel export | No | No |
| 40 | Master data — customers | ERP | master_data, ui_modern | `/modern/customers/`, `…/new/`, `…/<pk>/edit/`, `…/export/` | CRUD + export customers; opening balances | No | No |
| 41 | Master data — vendors | ERP | master_data, ui_modern | `/modern/vendors/`, `…/new/`, `…/<pk>/edit/`, `…/export/` | CRUD + export vendors | No | No |
| 42 | Master data — products | ERP | master_data, ui_modern | `/modern/products/`, `…/new/`, `…/<pk>/edit/`, `…/export/` | CRUD + export products | No | No |
| 43 | Sales invoices | ERP | sales, ui_modern | `/modern/sales-invoices/`, `…/new/` | Create/list sales invoices (drives e-invoice issuance) | No (uses `SalesInvoiceService`) | No |
| 44 | Purchase invoices | ERP | purchasing, ui_modern | `/modern/purchase-invoices/`, `…/new/` | Create/list purchase invoices | No (uses `PurchaseInvoiceService`) | No |
| 45 | Stock vouchers | ERP | inventory, ui_modern | `/modern/stock-vouchers/`, `…/new/` | Nhập/xuất kho (inventory movement vouchers) | No (uses `StockService`) | No |
| 46 | Stock dashboard, adjustments, stock card | ERP | inventory, ui_modern | `/modern/inventory/dashboard/`, `…/adjustments/new/`, `…/stock-card/` | Inventory overview, kiểm kê, thẻ kho | No | No |
| 47 | Fixed assets — register | ERP | assets, ui_modern | `/modern/assets/`, `…/new/` | Register TSCĐ / CCDC | No | No |
| 48 | Fixed assets — depreciation run | ERP | assets, ui_modern | `/modern/assets/depreciation/` | Period depreciation calculation (`DepreciationService`) | No | No |
| 49 | Fixed assets — dispose & transfer | ERP | assets, ui_modern | `/modern/assets/<pk>/dispose/`, `…/transfer/` | Asset disposal and inter-department transfer | No | No |
| 50 | Fixed assets — transactions | ERP | assets, ui_modern | `/modern/assets/transactions/` | Audit log of asset transactions | No | No |
| 51 | HR — employees | ERP | hr, ui_modern | `/modern/employees/`, `…/new/` | Employee master | No | No |
| 52 | HR — labor contracts | ERP | hr, ui_modern | `/modern/labor-contracts/`, `…/new/` | Labor contract management | No | No |
| 53 | HR — dependents | ERP | hr, ui_modern | `/modern/dependents/` | Register dependants for PIT deductions | No | No |
| 54 | HR — leave requests | ERP | hr, ui_modern | `/modern/leave/request/` | Submit leave requests | No | No |
| 55 | HR — insurance dashboard | ERP | hr, ui_modern | `/modern/insurance/` | BHXH/BHYT overview (`InsuranceService`) | No | No |
| 56 | Payroll run | ERP | payroll, ui_modern | `/modern/payroll/run/` | Calculate monthly payroll (`PayrollService`) | No | No |
| 57 | Chart of accounts (TT133) | ERP | master_data, ui_modern | `/modern/chart-of-accounts/`, `…/<pk>/change-code/` | Browse COA, request account-code change | No | Yes — `load_tt133` |
| 58 | Treasury — cash receipt (phiếu thu) | ERP | ledger, ui_modern | `/modern/treasury/receipt/new/` | Cash receipt voucher | No | No |
| 59 | Treasury — cash payment (phiếu chi) | ERP | ledger, ui_modern | `/modern/treasury/payment/new/` | Cash payment voucher | No | No |
| 60 | Contracts | ERP | contracts, ui_modern | `/modern/contracts/`, `…/wizard/`, `…/new/`, `…/<pk>/`, `…/export-docx/`, `…/email/` | Contract lifecycle; DOCX/email; wizard | No | Yes — `seed_contract_templates` |
| 61 | Contract templates | ERP | contracts, ui_modern | `/modern/contract-templates/`, `…/new/`, `…/preview-raw/`, `…/generate/…` | CRUD templates; render contract from template | No | Yes — `seed_contract_templates` |
| 62 | Input invoices (OCR) | ERP | input_docs, ui_modern | `/modern/input-invoices/`, `…/upload/`, `…/<pk>/process/` | Upload supplier invoices, OCR extract, post | No (`InvoiceExtractionService`) | No |
| 63 | CTGS (Chứng từ ghi sổ) workflow | ERP | ledger, ui_modern | `/modern/ctgs/create/`, `…/register/`, `…/check/`, `…/schedule/` | Declare, register, audit accounting-source documents | No | No |
| 64 | Source doc scheduling (S04-H) | ERP | ledger, ui_modern | `/modern/ctgs/schedule/` | Build bảng kê S04-H schedule | No | No |
| 65 | Department master | ERP | master_data, ui_modern | `/modern/departments/` | Bộ phận hạch toán | No | No |
| 66 | Recurring entries | ERP | recurring, ui_modern | `/modern/recurring/`, `…/run/` | Define and execute recurring journal entries (`RecurringService`) | No | No |
| 67 | Period closing — kết chuyển | ERP | ledger, ui_modern | `/modern/closing/` | Period-end closing (`PeriodClosingService`) | No | No |
| 68 | Period tools — allocation / declaration | ERP | ledger, ui_modern | `/modern/tools/period-allocation/`, `…/closing-entry-declaration/` | Period allocation + closing declaration | No | No |
| 69 | Year-end carry forward | ERP | ledger, ui_modern | `/modern/tools/year-end-carry-forward/` | Roll balances to next fiscal year | No | No |
| 70 | Opening balances — customers | ERP | ledger, ui_modern | `/modern/tools/opening-balances/customers/` | Set customer dư đầu kỳ | No | No |
| 71 | Opening balances — invoices | ERP | ledger, ui_modern | `/modern/tools/opening-balances/invoices/` | Set invoice dư đầu kỳ | No | No |
| 72 | Projects | ERP | projects, ui_modern | `/modern/projects/`, `…/new/`, `…/<pk>/`, `…/phases/add/`, `…/resources/add/` | Project, phase, resource management | No | No |
| 73 | CRM — leads | ERP | crm, ui_modern | `/modern/crm/leads/`, `…/new/` | Capture sales leads | No | No |
| 74 | CRM — opportunities | ERP | crm, ui_modern | `/modern/crm/opportunities/`, `…/new/`, `…/<pk>/convert/` | Pipeline + convert opportunity to customer/sale | No | No |
| 75 | CRM — tickets (CS) | ERP | crm, ui_modern | `/modern/crm/tickets/`, `…/new/` | Customer support tickets | No | No |
| 76 | CRM — campaigns | ERP | crm, ui_modern | `/modern/crm/campaigns/`, `…/new/` | Marketing campaigns | No | No |
| 77 | Attachments (universal) | ERP | documents, ui_modern | `/modern/attachments/upload/`, `…/<pk>/delete/`, `…/<pk>/download/` | Upload/delete/download attachments on any entity | No | No |
| 78 | Help center | ERP | ui_modern, public | `/modern/help/`, `…/<slug>/` | In-app help articles | No | Yes — `seed_help_articles` |
| 79 | PKM — dashboard & notes | ERP | pkm, ui_modern | `/modern/knowledge/`, `…/notes/`, `…/new/`, `…/<pk>/edit/`, `…/<pk>/delete/` | Personal knowledge notes CRUD | Yes — `post_save(KnowledgeNote)` → `log_interaction('note_create')` | No |
| 80 | PKM — search & Q&A | ERP | pkm, ui_modern | `/modern/knowledge/search/`, `…/qa/` | Semantic search + RAG Q&A over notes/documents | No | No |
| 81 | PKM — documents (RAG) | ERP | pkm, ui_modern | `/modern/knowledge/documents/`, `…/upload/`, `…/<pk>/reprocess/`, `…/<pk>/status/` | Upload PDF/DOCX/TXT/MD/XLSX for chunking + embeddings | Yes — `post_save(PKMDocument)` → `log_interaction('document_create')` | No |
| 82 | PKM — LLM config | ERP | pkm, ui_modern | `/modern/knowledge/settings/`, `…/new/`, `…/<pk>/edit/`, `…/<pk>/delete/` | Per-user LLM provider/key management (encrypted) | No | No |
| 83 | Notifications | ERP | notifications | `/notifications/`, `…/count/`, `…/<pk>/read/`, `…/mark-all-read/` | Per-user inbox; mark read | No | Yes — `send_tax_reminders` |
| 84 | Public — landing / blog | Public | public | `/`, `/blog/`, `/blog/<slug>/` | Marketing site | No | Yes — `seed_help_articles` (blog) |
| 85 | Public — signup | Public | public | `/signup/` | New tenant self-signup | No | No |
| 86 | Public — newsletter | Public | public | `/newsletter/subscribe/` | Newsletter subscription | No | No |

## Signals Map

Only one Django app registers signal handlers (`apps/pkm/apps.py::ready()` imports
`apps/pkm/signals.py`). No other `@receiver` exists across the codebase.

| App | Signal | Sender | Receiver | What it does |
|-----|--------|--------|----------|--------------|
| pkm | `post_save` | `KnowledgeNote` | `log_note_create` | On creation only (`created=True`), calls `interaction_service.log_interaction(interaction_type="note_create", module="pkm", …)` for analytics. Wrapped in `try/except` so failures never block the save. |
| pkm | `post_save` | `PKMDocument` | `log_document_create` | On creation only, logs a `document_create` interaction with title/file_type/file_size. Same non-blocking contract. |

No `pre_save`, `post_delete`, `pre_delete`, or `m2m_changed` receivers are used
anywhere. Voucher posting, depreciation, payroll, and similar "side effects"
happen via explicit service calls (e.g. `VoucherPostingService.post`,
`DnsnPostingService`, `DepreciationService.calculate`, `PayrollService.run`),
not via Django signals.

## Management Commands by Theme

### Seed / reference data
| Command | App | Purpose |
|---------|-----|---------|
| `seed_demo` | core | Seed full demo dataset |
| `create_demo_company` | core | Create a single demo company |
| `seed_tt58_demo` | core | Seed TT58 (DNSN) demo data |
| `load_tt133` | master_data | Load TT133 chart of accounts |
| `seed_tax_rates` | master_data | Seed VAT/sales tax rates |
| `seed_invoice_groups` | master_data | Seed invoice form/serial groups |
| `seed_tax_types` | core | Seed tax-type reference data |
| `seed_legal_references` | core | Seed legal regulation reference list |
| `seed_pit_history` | core | Seed personal income tax history |
| `seed_permissions` | identity | Seed default roles + permissions |
| `seed_help_articles` | public | Seed help-center / blog articles |
| `seed_contract_templates` | contracts | Seed default contract templates |

### Reporting reference data
| Command | App | Purpose |
|---------|-----|---------|
| `seed_financial_report_lines` | reporting | Seed B01/B02 financial report line templates |
| `seed_vat_tt80` | reporting | Seed VAT TT80 declaration template |

### Operations / batch
| Command | App | Purpose |
|---------|-----|---------|
| `send_tax_reminders` | notifications | Send scheduled tax-reminder notifications |

### Apps with `management/commands/` dir but no commands (only `__init__.py`)
budget, bidding, banking, approvals, fx, einvoice, guarantees, loans.

## Menu/Sidebar Entries

Official feature list from `templates/modern/base/layout.html` left sidebar,
grouped by section. All entries are permission-gated by `{% has_module_access
"<module>" %}`; each section is hidden entirely when the user has none of its
modules. Vietnamese labels are the canonical menu text.

### Top-level
- **Trang chủ** — Dashboard (`ui_modern:dashboard`)
- **Dự án** — Projects (`project_list`) [gated by `projects`]

### Ghim (Pins) — dynamic, user-pinned items via Super Search

### DNSN (TT58) [only shown when `company.accounting_regime == 'tt58'`]
- Chứng từ DNSN / Tạo chứng từ
- Tổng hợp sổ DNSN
- S1/S2a/S2b/S2c/S2d/S3a/S3b-DNSN ledgers (conditional on `tax_method_group`)
- Optional S4a/S4b/S4c/S4d-DNSN ledgers (`dnsn_optional_ledgers`)
- Tùy chọn sổ (S4) — ledger settings
- Báo cáo DNSN, B01-DNSN, B02-DNSN
- Chuyển đổi số dư TT58

### Cập nhật số liệu (Data Entry) [`ledger`, `input_docs`, `recurring`, `treasury`, `banking`, `loans`, `guarantees`]
- Phiếu kế toán — voucher_list
- Phiếu thu / Phiếu chi — cash_receipt_create / cash_payment_create
- Ngân hàng & Đối soát — banking_account_list
- Bảo lãnh ngân hàng — guarantee_list
- Vay vốn ngân hàng — loan_list
- Hóa đơn đầu vào — input_invoice_list
- Bút toán định kỳ — recurring_list

### Nghiệp vụ (Business Operations) [`sales`, `purchasing`, `master_data`, `inventory`, `contracts`, `bidding`]
- Khách hàng — customer_list
- Nhà cung cấp — vendor_list
- Hàng hóa — product_list
- Cơ hội đấu thầu — bid_list
- Hóa đơn bán — sales_invoice_list
- Phiếu nhập mua — purchase_invoice_list
- Phiếu nhập xuất — stock_voucher_list
- Tổng quan kho — stock_dashboard
- Kiểm kê — stock_adjustment_list
- Thẻ kho — stock_card_report
- Hợp đồng — contract_list
- Mẫu hợp đồng — contract_template_list

### CRM [`crm`]
- Khách tiềm năng — crm_lead_list
- Cơ hội bán hàng — crm_opportunity_list
- Chăm sóc KH — crm_ticket_list (hidden for micro/small SMEs)
- Chiến dịch — crm_campaign_list (hidden for micro/small SMEs)

### Tài sản (Assets) [`assets`]
- Tài sản cố định / CCDC — asset_list
- Tính khấu hao kỳ — depreciation_run
- Giao dịch tài sản — asset_transaction_list

### Nhân sự (Human Resources) [`hr`, `payroll`]
- Nhân viên — employee_list
- Hợp đồng lao động — labor_contract_list
- Người phụ thuộc — dependent_list
- Nghỉ phép — leave_request
- Bảo hiểm xã hội — insurance_dashboard
- Tính lương — payroll_run

### Sổ sách & Báo cáo (Books & Reports) [`ledger`, `reporting`, `einvoice`, `budget`, `fx`]
Sổ sách subgroup:
- Nhật ký chung, NK thu tiền (S03a1), NK chi tiền (S03a2), NK bán hàng (S03a4), NK mua hàng (S03a3)
- Sổ cái TK (S03b), Sổ chữ T TK
- Sổ quỹ TM (S07), Sổ TGNH (S08)
- Sổ chi tiết bán hàng (S35), Sổ chi tiết KH/NCC

Báo cáo & Thuế subgroup:
- Hóa đơn điện tử — einvoice_list
- BCĐ tài khoản (trial balance), BCTC (B01), KQ HĐKD (B02)
- Tờ khai GTGT (01), Bảng kê HĐ đầu vào / đầu ra
- Báo cáo D62 (BHXH), BC sử dụng lao động, BC quỹ lương, BC thuế TNCN
- Bảng tính giá thành, Sổ ĐK CTGS (S02a)
- BC dòng tiền trực tiếp / gián tiếp (B03)
- Ngân sách, Dự phóng dòng tiền
- Tỷ giá ngoại tệ, Định giá lại ngoại tệ

### Danh mục (Master Catalog) [`master_data`]
- Hệ thống TK — chart_of_accounts_list
- Bộ phận hạch toán — department_master

### Chứng từ ghi sổ [`ledger`]
- Khai báo CTGS — ctgs_create
- Đăng ký CTGS — ctgs_register
- Kiểm tra CTGS — ctgs_check
- Bảng kê S04-H — ctgs_schedule

### Công cụ cuối kỳ (Period Tools) [`ledger`]
- Kết chuyển cuối kỳ — period_closing
- Phân bổ cuối kỳ — period_allocation
- KK kết chuyển cuối kỳ — closing_entry_declaration
- Đánh lại số CT — voucher_renumber
- Dư đầu KH / Dư đầu hoá đơn — opening balances
- Chuyển số dư năm sau — year_end_carry_forward

### Tri thức cá nhân (PKM) [`pkm`]
- Tổng quan — pkm_dashboard
- Ghi chú — pkm_note_list
- Tài liệu — pkm_document_list
- Hỏi đáp AI — pkm_qa_chat
- Tìm kiếm — pkm_search
- Cấu hình AI — pkm_llm_config_list

### Hệ thống (System)
- Phê duyệt chờ xử lý — approval_queue [`approvals`] (with pending count badge)
- Hồ sơ công ty — company_profile
- Hộp thư thông báo — notifications:inbox
- Vai trò & phân quyền — admin_role_list [superuser/staff only]
- Người dùng — admin_user_list [superuser/staff only]
- Quyền của tôi — my_permissions
- Trợ giúp — help_index

### Mobile bottom nav
- Trang chủ, Phiếu (vouchers), Menu, Thông báo, Tài khoản

## API Endpoints (django-ninja)

Root: `/api/v1/` (`apps/core/api.py` — `NinjaAPI(title="Visota ERP API", version="1.0.0")`).
Auth: session cookie (browser) or `X-API-Key: pmk_<key>` header (service-to-service).

### Accounting (`tags=["Accounting"]`)
- `GET  /vouchers/` — list vouchers (filter by fiscal_year, period)
- `GET  /vouchers/{id}` — voucher detail with lines
- `POST /vouchers/{id}/post` — post voucher to ledger

### Master Data (`tags=["Master Data"]`)
- `GET /customers/` — list/search
- `GET /vendors/` — list/search
- `GET /products/` — list/search

### Sales (`tags=["Sales"]`)
- `GET /sales/invoices/` — list
- `GET /sales/invoices/{id}` — detail with lines

### Reports (`tags=["Reports"]`)
- `GET /reports/trial-balance?fiscal_year=&period=` — trial balance
- `GET /reports/ar-aging` — AR aging summary
- `GET /reports/cash-position?fiscal_year=&period=` — cash on hand + bank

### E-Invoice (`tags=["E-Invoice"]`)
- `POST /einvoice/issue/{sales_invoice_id}` — issue from sales invoice
- `POST /einvoice/{einvoice_id}/publish` — publish to provider

### DNSN (`tags=["DNSN"]`) — registered via `apps/ledger/dnsn_api.py`
- `GET    /dnsn/vouchers/` — list (filter type, date, status)
- `POST   /dnsn/vouchers/` — create
- `GET    /dnsn/vouchers/{id}` — retrieve
- `PATCH  /dnsn/vouchers/{id}` — update (DRAFT only)
- `DELETE /dnsn/vouchers/{id}` — delete (DRAFT only)
- `GET    /dnsn/ledgers/` — list available ledger types
- `GET    /dnsn/ledgers/{ledger_type}/entries/` — ledger entries with running balance

### PKM (`/api/v1/pkm/`) — `apps/pkm/api.py` Router
Notes:
- `POST   /notes/`, `GET /notes/`, `GET /notes/{id}/`, `PUT /notes/{id}/`, `DELETE /notes/{id}/`
- `POST   /notes/search/` — keyword search (logs `search` interaction)

LLM Configs:
- `GET /llm-configs/`, `POST /llm-configs/`, `PUT /llm-configs/{id}/`, `DELETE /llm-configs/{id}/`
- `POST /llm-configs/validate/` — validate API key without saving
- `GET /providers/` — supported LLM providers + suggested models

Documents (RAG):
- `POST   /documents/` — upload (multipart; dedup by SHA-256; enqueues RAG)
- `GET    /documents/`, `GET /documents/{id}/`, `DELETE /documents/{id}/`
- `POST   /documents/{id}/reprocess/` — re-queue RAG pipeline
- `GET    /documents/{id}/status/` — processing status

Q&A:
- `POST /qa/ask/` — RAG question answering (returns answer + sources + context)
- `GET  /qa/history/` — paginated Q&A history

Stats:
- `GET /stats/` — aggregate PKM statistics (note/doc/qa/tag counts, doc status breakdown, active config flag, role suggestions)
