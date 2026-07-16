# Tax, E-Invoice, and Sales/Purchasing Investigation — TT58/2026 Gap Analysis

> **Date**: 2026-07-14
> **Scope**: Analysis of existing tax handling, e-invoice, and business transaction flows for Thông tư 58/2026/TT-BTC compliance.

---

## Executive Summary

Visota currently implements a **single tax regime**: GTGT by **khấu trừ** (deduction method) with TNDN computed on taxable income. The codebase has **no support** for:

- GTGT by percentage on revenue (phương pháp tính trực tiếp / % trên doanh thu)
- TNDN by percentage on revenue (% trên doanh thu)
- Household business (hộ kinh doanh) entity types per TT132/2018
- Any of the 4 tax method combinations required by TT58

The VAT engine (TT80/2021 form 01/GTGT), e-invoice module (TT78/2021), and sales/purchasing flows are **hardcoded to the deduction method**: sales post output VAT to TK 33311, purchases post input VAT to TK 1331, and the VAT return calculates payable = output − input. No alternative tax method selection exists at the Company, Customer, or invoice level.

**Bottom line**: TT58 compliance requires substantial new models, services, and UI, not minor field additions.

---

## 1. Tax Configuration

### 1.1 Company Model (`apps/core/models.py`)

The `Company` model has an `AccountingRegime` enum with three choices:

```python
class AccountingRegime(models.TextChoices):
    TT133 = "tt133", "TT133/2016 (DN nhỏ và vừa)"
    TT200 = "tt200", "TT200/2014 (DN lớn)"
    Q48 = "q48", "QĐ48/2006 (cũ)"
```

**No `vat_method` or `tax_method` field exists.** The accounting regime controls chart-of-accounts layout (TT133 vs TT200), not the tax calculation method. There is no way to configure whether a company uses GTGT khấu trừ vs GTGT by % on revenue.

**SME classification** (`sme_size` field) exists with four tiers: micro, small, medium, large. This is used by `TaxConfigService` to select CIT rate (15% / 17% / 20%), but does not affect the VAT method.

### 1.2 TaxRateConfig (`apps/core/models.py`)

A comprehensive global/per-company tax rate configuration table covering:

| Tax | Fields | Current Values |
|------|--------|----------------|
| CIT (TNDN) | `cit_rate_standard`, `cit_rate_small`, `cit_rate_micro` | 20%, 17%, 15% |
| VAT (GTGT) | `vat_rate_standard`, `vat_rate_reduced`, `vat_rate_reduced_active` | 10%, 8% (ND 174/2025) |
| PIT (TNCN) | `pit_personal_deduction`, `pit_dependent_deduction`, `pit_brackets` | 13.2M / 5.2M (2026) |
| PIT 2026 | `pit_personal_deduction_2026`, `pit_brackets_2026` | 15.5M / 6.2M |
| SCT (TTĐB) | alcohol, beer, tobacco, car rates | Various |
| Fees | môn bài, trước bạ | Fixed amounts |
| FCT | `fct_cit_rate`, `fct_vat_rate` | 5% / 5% |

**Gap**: All CIT rates are flat percentages applied to taxable income. There is no CIT-by-%-on-revenue rate (e.g., 0.5%, 1%, 1.5%, 2% on gross revenue per household business tiers).

### 1.3 TaxRateCode (`apps/master_data/models/tax_rate.py`)

GTGT tax rate codes per TT78/2021:

| Code | Rate | Meaning |
|------|------|---------|
| 00 | 0% | Non-taxable / 0% |
| 05 | 5% | 5% rate |
| 04 | 5% | 5% special |
| 10 | 10% | Standard |
| 08 | 10% | 10% special (8% reduced) |
| KT | 0% | Không chịu thuế (not subject to VAT) |

These codes are used on `VoucherLine.tax_code` to drive the TT80 VAT return. They represent VAT rates only, not tax methods.

### 1.4 TaxConfigService (`apps/core/services/tax_config_service.py`)

- `get_cit_rate(company)` — returns CIT rate based on SME size (15/17/20%)
- `get_vat_rate(is_reduced)` — returns 10% or 8% based on ND 174/2025 toggle
- `classify_sme(annual_revenue, total_capital, employee_count, sector)` — ND 80/2021 classification

**Gap**: No method to select or determine VAT calculation method (khấu trừ vs trực tiếp). No CIT-by-revenue calculation path.

---

## 2. E-Invoice Module (`apps/einvoice/`)

### 2.1 Models (`apps/einvoice/models.py`)

Three models:
- **EInvoiceProvider** — enum: MANUAL, MISA, VNPT, EHOADON, BKAV, VIETTEL
- **EInvoiceConfig** — per-company provider config (pattern, serial, API credentials)
- **EInvoice** — individual issued e-invoice with XML/JSON/PDF file storage
- **EInvoiceReportBatch** — BC01/BC26/TB04 report submissions

E-invoice fields include: buyer/seller snapshot, subtotal, `vat_rate`, `vat_amount`, `total_amount`, status lifecycle (draft → issued → adjusted/replaced/cancelled).

### 2.2 EInvoiceService (`apps/einvoice/services/__init__.py`)

Key operations:
- `issue_from_sales_invoice()` — creates draft EInvoice from SalesInvoice, generates XML/JSON
- `publish()` — assigns invoice number, calls provider API (or marks manual)
- `cancel()` — cancels issued invoice
- `adjust()` — creates adjusting invoice with negative amounts
- `EInvoiceReportService.generate_bc01()` — monthly usage report

XML generation follows a **simplified TT78 schema** with `<Invoice>`, `<Seller>`, `<Buyer>`, `<Items>`, `<Summary>` elements. Each item line includes `<VATRate>` and `<VATAmount>`.

### 2.3 TT58 Gaps in E-Invoice

1. **No invoice type differentiation for tax methods**: TT58 requires different e-invoice formats depending on the seller's tax method. Hóa đơn GTGT (for deduction-method sellers) vs Hóa đơn bán hàng (for direct-method / household businesses). The current `form_symbol` defaults to `01GTKT` (GTGT invoice) with no support for `02BANHANG` (sales invoice for non-VAT entities).

2. **No household business invoice fields**: TT132/2018 household business invoices require specific fields (business type, tax-by-revenue rate) not present in the model.

3. **No TT32/2025 support**: The legal references seed mentions TT32/2025 (replacing TT78), but the e-invoice XML schema and service code still reference TT78/2021 patterns only.

4. **Provider API is stubbed**: `_call_provider_api()` returns a hardcoded success response. No real provider integration exists.

5. **No e-invoice for purchase-side input**: EInvoice only links to `SalesInvoice` (output side). There is no model for receiving/validating supplier e-invoices (input VAT invoices).

---

## 3. Sales Module (`apps/sales/`)

### 3.1 Models (`apps/sales/models.py`)

- **SalesInvoice** — header: invoice_no, customer, totals (subtotal, discount, vat_amount, total_amount), GL voucher link, status
- **SalesInvoiceLine** — per-line: product, quantity, unit_price, `vat_rate`, `vat_amount`, account codes (revenue=5111, vat=33311, cost=632)

### 3.2 SalesInvoiceService (`apps/sales/services/invoice_service.py`)

The `create()` method:
1. Builds lines with per-line `vat_rate` (defaults from `Product.default_vat_rate`)
2. Computes `vat_amount = amount_before_vat * vat_rate` per line
3. Aggregates totals on the invoice header

The `_post()` method generates accounting entries:

```
N131 (Customer AR)     total_amount
  C5111 (Revenue)      amount_before_vat per line
  C33311 (VAT output)  vat_amount aggregated by account
```

**Key observation**: The journal entry **always** posts output VAT to TK 33311 (Thuế GTGT đầu ra phải nộp). This is the deduction-method account. For the direct-percentage method (tính trực tiếp), output VAT should go to TK 33312 (Thuế GTGT hàng bán chịu thuế), and revenue should be recorded gross (including VAT) differently.

### 3.3 TT58 Gaps in Sales

1. **No tax method on SalesInvoice**: No field to select whether this invoice uses deduction method or direct method. The service always generates TK 33311 entries.

2. **Revenue account hardcoded to 5111**: For businesses using % on revenue for TNDN, revenue recognition may differ. The system assumes deduction-method accounting.

3. **No COGS posting**: The `_post()` method does NOT post cost of goods sold (N632 / C156). Only revenue and AR are recorded. This means period closing cannot accurately compute gross profit for TNDN-on-income calculation.

4. **No revenue-based tax calculation**: For GTGT-by-% and TNDN-by-%, tax = revenue × prescribed rate. No service path exists for this calculation.

---

## 4. Purchasing Module (`apps/purchasing/`)

### 4.1 Models (`apps/purchasing/models.py`)

- **PurchaseInvoice** — header: vendor, totals, GL voucher link
- **PurchaseInvoiceLine** — per-line: product, quantity, unit_price, `vat_rate`, `vat_amount`, account codes (inventory=156, vat=1331, cost=632)

### 4.2 PurchaseInvoiceService (`apps/purchasing/services/invoice_service.py`)

The `_post()` method generates:

```
N156 (Inventory)       amount_before_vat per line
N1331 (VAT input)     vat_amount aggregated
  C331 (Vendor AP)     total_amount
```

**Key observation**: Always posts input VAT to TK 1331 (Thuế GTGT được khấu trừ). This is only valid for deduction-method taxpayers. Direct-method businesses do not claim input VAT deductions.

### 4.3 TT58 Gaps in Purchasing

1. **No conditional input VAT posting**: For companies using GTGT by % on revenue, input VAT is NOT deductible and should be included in the cost of goods (N156 includes VAT, no N1331 line). The current service always posts N1331.

2. **No purchase e-invoice reception**: No mechanism to receive/parse supplier e-invoices for input VAT matching.

3. **No import VAT handling**: The InvoiceType includes "import" but the posting logic does not handle import VAT (which goes through customs, not TK 1331 directly).

---

## 5. Household Business (Hộ Kinh Doanh) Support

### 5.1 Search Results

Comprehensive grep for `hộ kinh doanh`, `hkd`, `household`, `TT132`, `tt132`, `TT58`, `tt58` across the entire codebase (Python, HTML, JSON, YAML, MD files):

**Result: ZERO matches found.**

There is no mention of household businesses, TT132/2018, or TT58/2026 anywhere in the codebase, documentation, tests, or seed data.

### 5.2 What TT132/2018 Requires

TT132/2018/NĐ-CP governs household business registration and operations. Household businesses in Vietnam:
- Can choose between GTGT deduction method OR GTGT by % on revenue
- If revenue < threshold (currently 3 billion VND/year), can opt for presumptive tax (% on revenue for both GTGT and TNDN)
- Have different e-invoice requirements
- Have different accounting record-keeping requirements (simplified)

### 5.3 Gaps

1. **No entity type differentiation**: Company model has no field to distinguish between corporate enterprise and household business. The `sme_size` field classifies company size but not legal form.

2. **No TT132 legal reference**: The `seed_legal_references` command includes TT133, TT200, TT78, TT80, TT32, TT99, but **not** TT132/2018 or TT58/2026.

3. **No presumptive tax rates**: TaxRateConfig has no fields for household business presumptive rates (e.g., 0.5% GTGT on revenue, 0.5-1.5% TNDN on revenue by sector).

---

## 6. Services Layer

### 6.1 VoucherPostingService (`apps/ledger/services/voucher_posting_service.py`)

Core posting engine:
- `post(voucher)` — validates debit=credit balance, updates AccountPeriodBalance, sets status=LEDGER
- `unpost(voucher)` — reverses balance updates, recomputes running balances
- Recomputes running cumulative balances for affected account codes

**Tax-aware features**: The service has an `is_auto_tax_posting` flag on VoucherLine (for automatically generated 1331/33311 lines), but the posting logic itself is tax-method-agnostic. It simply posts whatever debit/credit amounts are on the voucher lines.

### 6.2 PeriodClosingService (`apps/ledger/services/period_closing_service.py`)

Closing entries (kết chuyển):
1. Close revenue accounts (5xx, 7xx) → N5xx / C911
2. Close expense accounts (6xx, 8xx) → N911 / C6xx
3. Transfer profit/loss → N911/C421 (profit) or N421/C911 (loss)

**Gap**: The closing service does NOT calculate or post CIT (TNDN) expense. There is no step that computes `N8211 / C3334` for CIT provision. The closing entry declaration view (tool_views.py) lists step 8 as "Xác định & kết chuyển TNDN" (debit 911 / credit 821), but this is a display-only tool — the actual PeriodClosingService does not generate CIT entries.

### 6.3 VATReturnService (`apps/reporting/services/vat_return.py`)

Config-driven TT80/2021 VAT return engine:
- Reads `VATReportLine` config from database
- Aggregates `VoucherLine` amounts filtered by account code patterns, invoice group, and tax rate code
- Supports formula expressions (`[25]+[26]-[27]`) with recursive resolution and cycle detection
- Computes: input VAT (TK 1331, group #4), output VAT (TK 33311, group #5), payable/credit
- Splits output by tax rate: 0% → [29], 5% → [30]/[31], 10% → [32]/[33]

**Gap**: This entire return form is designed for the **deduction method** (01/GTGT). The direct-percentage method uses a different return form (03/GTGT for household businesses or 01/TĐ-TNCN). There is no model or service for generating direct-method VAT returns.

---

## 7. Summary of TT58 Compliance Gaps

### 7.1 The 4 Required Tax Method Combinations

| # | GTGT Method | TNDN Method | Current Support |
|---|-------------|-------------|-----------------|
| 1 | % on revenue | % on revenue | **NOT SUPPORTED** |
| 2 | % on revenue | On taxable income | **NOT SUPPORTED** |
| 3 | Khấu trừ (deduction) | % on revenue | **NOT SUPPORTED** |
| 4 | Khấu trừ (deduction) | On taxable income | **PARTIALLY SUPPORTED** (current default, but CIT not auto-calculated/posted) |

### 7.2 Required New Features (Prioritized)

**P0 — Data Model Changes:**
1. Add `vat_method` field to `Company` model (choices: `deduction`, `percentage_on_revenue`)
2. Add `tndn_method` field to `Company` model (choices: `on_taxable_income`, `percentage_on_revenue`)
3. Add `business_type` / `legal_form` field to `Company` (enterprise, household_business, individual)
4. Add presumptive tax rate fields to `TaxRateConfig` (GTGT % on revenue rates by sector, TNDN % on revenue rates by sector)
5. Add `tax_method` override on `SalesInvoice` / `PurchaseInvoice` for per-transaction flexibility

**P0 — Posting Logic Changes:**
6. Modify `SalesInvoiceService._post()` to conditionally post to TK 33312 (direct method) instead of TK 33311 (deduction method) based on company's VAT method
7. Modify `PurchaseInvoiceService._post()` to skip input VAT (N1331) for percentage-on-revenue companies, including VAT in cost instead
8. Add CIT calculation + posting service (N8211 / C3334) to period closing

**P1 — Tax Returns:**
9. New model + service for 03/GTGT return form (direct/percentage method VAT return)
10. New model + service for presumptive TNDN return (% on revenue)
11. CIT provisional payment tracking (tạm nộp quý)

**P1 — E-Invoice:**
12. Support invoice form `02BANHANG` (sales invoice for non-VAT-deduction sellers)
13. Household business-specific e-invoice fields
14. TT32/2025 schema migration (TT78 successor)

**P2 — Household Business:**
15. Seed TT132/2018 and TT58/2026 legal references
16. Household business registration fields (business location, sector code for presumptive rate)
17. Simplified accounting mode for household businesses

### 7.3 What Already Works Well

- **VAT deduction method accounting**: Full posting pipeline (sales → 33311, purchase → 1331) works correctly
- **TT80 VAT return form**: Config-driven engine with formula support, tested for deduction method
- **E-invoice lifecycle**: Draft → issued → adjusted/replaced/cancelled with XML/JSON/PDF generation
- **VAT rate flexibility**: Per-line VAT rates (0%, 5%, 8%, 10%, KT) supported on both sales and purchase invoices
- **Multi-company tenancy**: TaxRateConfig can be global or company-specific
- **Legal reference tracking**: LegalReference model tracks applicable regulations with effective/expiry dates
- **CIT rate tiers**: 15%/17%/20% based on SME classification per ND 80/2021 and Luật TNDN 2025

---

## 8. Key File Reference

| Area | File Path |
|------|-----------|
| Company + TaxRateConfig models | `apps/core/models.py` |
| Tax config service | `apps/core/services/tax_config_service.py` |
| E-invoice models | `apps/einvoice/models.py` |
| E-invoice service (issue/publish/cancel) | `apps/einvoice/services/__init__.py` |
| E-invoice PDF service | `apps/einvoice/services/einvoice_pdf_service.py` |
| E-invoice views | `apps/einvoice/views.py` |
| Sales models | `apps/sales/models.py` |
| Sales invoice service (posting) | `apps/sales/services/invoice_service.py` |
| Purchase models | `apps/purchasing/models.py` |
| Purchase invoice service (posting) | `apps/purchasing/services/invoice_service.py` |
| Ledger voucher models | `apps/ledger/models/voucher.py` |
| Voucher posting service | `apps/ledger/services/voucher_posting_service.py` |
| Period closing service | `apps/ledger/services/period_closing_service.py` |
| VAT return service (TT80) | `apps/reporting/services/vat_return.py` |
| VAT return config model | `apps/reporting/models.py` (VATReportLine) |
| TT80 seed data | `apps/reporting/management/commands/seed_vat_tt80.py` |
| TaxRateCode model (GTGT codes) | `apps/master_data/models/tax_rate.py` |
| Customer/Vendor models | `apps/master_data/models/party.py` |
| Product model (default VAT) | `apps/master_data/models/product.py` |
| InvoiceGroup model | `apps/master_data/models/invoice_group.py` |
| Legal references seed | `apps/core/management/commands/seed_legal_references.py` |
| Closing entry declaration view | `apps/ui_modern/views/tool_views.py` |
| Feature flags | `apps/core/feature_flags.py` |
