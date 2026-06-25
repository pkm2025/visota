# Pre-Deploy Test Plan — Visota (PMKetoan)

> Full browser + unit test before go-live. **Fail = block deploy.**

## Test Matrix

### Tier 1 — Smoke (P0, must pass)

| ID | Test | Method | Expected |
|----|------|--------|----------|
| S01 | Landing page renders | Browser GET `/` | 200, "Visota" visible |
| S02 | Blog list + detail | Browser GET `/blog/` + `/blog/<slug>/` | 200, articles visible |
| S03 | Contact form submit | POST `/contact/submit/` | 302, ContactRequest saved |
| S04 | Newsletter signup | POST `/newsletter/subscribe/` | 302, Subscriber saved |
| S05 | Login (admin) | Browser login flow | Redirect `/modern/` |
| S06 | Login (wrong password) | Browser login flow | Error shown |
| S07 | Dashboard renders | GET `/modern/` | 200, KPI cards + quick actions |
| S08 | Logout | POST `/auth/logout/` | Session cleared |
| S09 | Every module URL | GET all 78 URLs | 200 or 302 |
| S10 | No 500 errors | Full URL sweep | 0 errors |

### Tier 2 — Core ERP flows (P0)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| E01 | Voucher list + detail | `/modern/vouchers/` → click row | Detail loads |
| E02 | Voucher create form | `/modern/vouchers/new/` | Form renders |
| E03 | Voucher print PDF | `/modern/vouchers/<id>/print/` | PDF download |
| E04 | Voucher print DOCX | `/modern/vouchers/<id>/print-docx/` | DOCX download |
| E05 | Sales invoice list | `/modern/sales-invoices/` | 200, table visible |
| E06 | Sales invoice create | `/modern/sales-invoices/new/` | Form renders |
| E07 | Purchase invoice list | `/modern/purchase-invoices/` | 200 |
| E08 | Customer list + export | `/modern/customers/` → export | 200 + XLSX |
| E09 | Vendor list | `/modern/vendors/` | 200 |
| E10 | Period closing | `/modern/closing/` | 200 |
| E11 | Trial balance | `/modern/reports/trial-balance/` | 200, table |
| E12 | Balance sheet B01 | `/modern/reports/balance-sheet/` | 200 |
| E13 | P&L B02 | `/modern/reports/pnl/` | 200 |
| E14 | VAT return | `/modern/reports/vat-return/` | 200 |

### Tier 3 — Contract + Template system (P0)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| C01 | Template list (21) | `/modern/contract-templates/` | 21 templates |
| C02 | Template create | New → fill → save | Redirect to list |
| C03 | Template edit | Edit #1 → modify → save | Changes saved |
| C04 | Template delete | Delete custom → confirm | Redirect to list |
| C05 | Template duplicate | Duplicate #1 | Form with _copy |
| C06 | Template preview AJAX | POST preview-raw | Rendered HTML |
| C07 | Generate PDF from template | generate/bb_nghiem_thu/<id>/ | PDF file |
| C08 | Contract detail has template dropdown | Contract detail page | Dropdown visible |
| C09 | Contract detail has related modules | Project/Guarantee/Loan cards | Cards visible |

### Tier 4 — HR + Payroll (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| H01 | Employee list | `/modern/employees/` | 200 |
| H02 | Employee create | `/modern/employees/new/` | Form renders |
| H03 | Labor contract list | `/modern/labor-contracts/` | 200 |
| H04 | Payroll run | `/modern/payroll/run/` | 200 |
| H05 | Insurance dashboard | `/modern/insurance/` | 200 |
| H06 | Leave request | `/modern/leave/request/` | 200 |
| H07 | Dependent list | `/modern/dependents/` | 200 |
| H08 | D62 report | `/modern/reports/d62/` | 200 |
| H09 | PIT monthly | `/modern/reports/pit-monthly/` | 200 |

### Tier 5 — CRM + Projects (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| P01 | CRM leads | `/modern/crm/leads/` | 200 |
| P02 | CRM opportunities | `/modern/crm/opportunities/` | 200 |
| P03 | CRM tickets | `/modern/crm/tickets/` | 200 |
| P04 | CRM campaigns | `/modern/crm/campaigns/` | 200 |
| P05 | Project list | `/modern/projects/` | 200 |
| P06 | Project detail (biên bản dropdown) | `/modern/projects/<id>/` | BB links visible |

### Tier 6 — E-Invoice + Banking + Approvals (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| F01 | E-invoice list | `/modern/einvoices/` | 200 |
| F02 | E-invoice detail | `/modern/einvoices/<id>/` | 200, link to SI |
| F03 | E-invoice BC01 form | Bottom of list | Form visible |
| F04 | Approval queue | `/modern/approvals/` | 200 |
| F05 | Approval rules | `/modern/approvals/rules/` | 7 rules |
| F06 | Banking accounts | `/modern/banking/accounts/` | 200 |
| F07 | Banking reconcile | `/modern/banking/reconcile/` | 200 |

### Tier 7 — RBAC Permission system (P0)

| ID | Test | User | URL | Expected |
|----|------|------|-----|----------|
| R01 | Sales denied vouchers | e2e_sales | /modern/vouchers/ | 302 → /no-access/ |
| R02 | Sales allowed sales | e2e_sales | /modern/sales-invoices/ | 200 |
| R03 | Purchaser denied sales | e2e_purchaser | /modern/sales-invoices/ | 302 |
| R04 | Purchaser allowed purchase | e2e_purchaser | /modern/purchase-invoices/ | 200 |
| R05 | HR denied contracts | e2e_hr | /modern/contracts/ | 302 |
| R06 | HR allowed employees | e2e_hr | /modern/employees/ | 200 |
| R07 | PM allowed projects | e2e_pm | /modern/projects/ | 200 |
| R08 | PM denied vouchers | e2e_pm | /modern/vouchers/ | 302 |
| R09 | Accountant allowed all acc | e2e_accountant | /modern/vouchers/ | 200 |
| R10 | Viewer denied sales | e2e_viewer | /modern/sales-invoices/ | 302 |

### Tier 8 — Multi-tenant (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| T01 | Company switcher visible | Topbar | Dropdown with companies |
| T02 | Switch company | POST /switch-company/ | Session updated |
| T03 | Data isolation | Switch company → verify data changes | Different records |

### Tier 9 — Mobile / PWA (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| M01 | Landing mobile responsive | 390px viewport | No h-scroll |
| M02 | Dashboard mobile | Login at 390px | No h-scroll |
| M03 | Voucher list mobile | 390px | Table scroll wrapper |
| M04 | Bottom nav visible | 390px | 5 items |
| M05 | Bottom nav hidden desktop | 1280px | Display none |
| M06 | Right sidebar hidden mobile | 390px | Display none |
| M07 | PWA manifest valid | GET /static/manifest.json | JSON with icons |
| M08 | Service worker | Check navigator.serviceWorker | Registered |
| M09 | iPad layout | 768px | No h-scroll |
| M10 | Galaxy S20 layout | 360px | No h-scroll |

### Tier 10 — Admin (P1)

| ID | Test | Steps | Expected |
|----|------|-------|----------|
| A01 | Company profile 4 tabs | `/modern/admin/company-profile/` | Legal/Reps/Bank/Brand |
| A02 | Logo upload | Upload file | Saved |
| A03 | Stamp upload | Upload file | Saved |
| A04 | Bank accounts add/remove | Dynamic table | Rows update |
| A05 | Roles list (8 roles) | `/modern/admin/roles/` | 8 rows |
| A06 | Users list | `/modern/admin/users/` | Users visible |
| A07 | Contact list (leads) | `/modern/admin/contacts/` | Test visitor visible |
| A08 | My permissions | `/modern/me/permissions/` | Module list |

### Tier 11 — New modules (P2)

| ID | Test | URL | Expected |
|----|------|-----|----------|
| N01 | Bidding | /modern/bidding/ | 200 |
| N02 | Budget | /modern/budget/ | 200 |
| N03 | Cash flow | /modern/cash-flow/ | 200 |
| N04 | FX rates | /modern/fx/rates/ | 200 |
| N05 | FX revaluation | /modern/fx/revaluation/ | 200 |
| N06 | Guarantees | /modern/guarantees/ | 200 |
| N07 | Loans | /modern/loans/ | 200 |
| N08 | Notifications inbox | /notifications/ | 200 |

### Tier 12 — Unit tests (P0)

| Suite | Expected |
|-------|----------|
| 458 unit/integration | All pass |
| 164 E2E desktop | All pass |
| 33 E2E mobile | All pass |
| **Total 655** | **0 fail** |

## Execution order

1. **Unit tests** (fast, catch code regressions)
2. **URL smoke sweep** (all 78 URLs)
3. **RBAC permission matrix** (10 tests)
4. **Core ERP flow** (voucher/sales/purchase)
5. **Template CRUD** (create/edit/delete/generate)
6. **Mobile/PWA** (viewport tests)
7. **Multi-tenant** (company switch)
8. **Admin** (company profile + contacts)
9. **E2E browser suite** (Playwright)
