# Visota Regulatory Compliance Audit

> **Audit date**: 2026-07-16
> **Scope**: Codebase review of `apps/` for compliance with current Vietnamese regulations
> **Sources**: Code paths reviewed include `apps/ledger/`, `apps/core/`, `apps/hr/`, `apps/payroll/`, `apps/einvoice/`, `apps/bidding/`, `apps/reporting/`, `apps/contracts/`, `apps/master_data/`, plus seed commands and tests.
> **Cross-referenced with** `.factory/regulatory-research.md` (regulatory source-of-truth) and `.factory/tax-investigation.md` (TT58 gap analysis).

---

## 1. Kế toán (Accounting)

### 1.1 TT133/2016/TT-BTC (DN nhỏ và vừa) — **PARTIALLY IMPLEMENTED**

- **Chart of accounts**: `apps/master_data/management/commands/load_tt133.py` ships a full TT133 chart (Type 1-9, accounts 111-642+, ~100+ accounts). The `seed_demo` command auto-loads it.
- **Statutory reports**: `apps/reporting/models.py` declares `FinancialReportLine` for `B01-DN` (balance sheet), `B02-DN` (P&L), `B03-DN-direct` and `B03-DN-indirect` (cash flow). Layout is DB-driven via `seed_financial_report_lines`.
- **Voucher types**: `apps/ledger/models/voucher.py` supports `AccountingVoucher` with double-entry `VoucherLine` (No/Có) — fully compatible with TT133.
- **Tests**: `tests/test_load_tt133.py`, `tests/test_chart_of_accounts.py`, `tests/test_balance_sheet.py`, `tests/test_pnl.py`, `tests/test_cash_flow_direct_offset.py`.

**Status**: This is the most mature regime. Production-grade.

### 1.2 TT200/2014/TT-BTC (DN lớn) — **NOT IMPLEMENTED**

- `Company.AccountingRegime` enum exposes the choice `TT200 = "tt200"` (`apps/core/models.py`), and the `seed_legal_references` command references a planned replacement `TT99/2025` (effective 2026-01-01).
- **However**: there is no `load_tt200.py` (or `load_tt99.py`) management command. Searching `apps/` for `load_tt200` returns no matches.
- The reporting layouts `B01-DN / B02-DN / B03-DN` are tagged as "TT133/TT200 conventions" in the docstring, but TT200 has additional account codes (e.g. longer sub-account detail, account 242 treatment differences) and report variations (e.g. `B01-DN` vs `B01-BC`) that are not seeded.
- No tests for TT200 regime.
- A user can set `accounting_regime = "tt200"` on a Company, but the chart and reports will silently fall back to TT133 data — a hidden correctness bug.

**Gap**: HIGH. Either remove the `TT200` choice or implement a `load_tt200` / `load_tt99` loader plus the corresponding report lines.

### 1.3 QĐ48/2006 (cũ) — **CHOICE ONLY, NO IMPLEMENTATION**

- Enum exposes `Q48 = "q48"`. No chart loader, no reports, no tests. Appears to be a legacy placeholder. Should likely be marked as deprecated/removed.

### 1.4 TT58/2026/TT-BTC (DNSN — DN siêu nhỏ) — **IMPLEMENTED, RECENTLY ADDED**

- Full DNSN ledger bypassing double-entry: `apps/ledger/models/dnsn.py` (`DnsnVoucher`, `DnsnLedgerEntry`, `DnsnLedgerBalance`) with simplified amount fields (revenue/cost/vat/cash) classified by ledger type S1-S4.
- Ledger-type availability by tax-method group (1-4): `apps/ledger/dnsn_ledger_types.py` correctly maps groups → required S ledgers, with optional S4a-S4d toggle via `Company.dnsn_optional_ledgers` JSON field.
- Posting service: `apps/ledger/services/dnsn_posting_service.py`.
- Reports: `apps/reporting/services/dnsn_report_service.py` generates `B01-DNSN` (balance sheet) and `B02-DNSN` (P&L), plus BCTC mandatory check (groups 2/4 → mandatory, groups 1/3 → optional).
- Seed: `apps/core/management/commands/seed_tt58_demo.py` builds demo companies for all 4 tax-method groups + a HKD entity with posted vouchers, ledger entries, balances.
- API: `apps/ledger/dnsn_api.py` exposes DNSN endpoints.
- UI views: `apps/ui_modern/views/dnsn_voucher_views.py`, `dnsn_ledger_views.py`, `dnsn_report_views.py`, `dnsn_conversion_views.py`.
- Tax-method support: `apps/core/services/tndn_calculation_service.py` correctly implements both `ty_le_phan_tram` (TT58 % on revenue, per NĐ 218/2013 industry rates 0.5%/1%/1.5%/2%) and `tinh_thue` (taxable income × CIT rate).
- Tests: `tests/test_dnsn_models.py`, `test_dnsn_voucher_crud.py`, `test_dnsn_reports.py`, `test_dnsn_report_bugfixes.py`, `test_dnsn_ledger_views.py`, `test_dnsn_balance_conversion.py`, `test_tt58_sales_purchasing_integration.py`, `test_tt58_hkd_and_seed.py`, `test_tt58_company_config.py`.

**Gaps**:
- **Missing report `B03-DNSN` (cash flow)**: TT58 requires a simplified cash-flow statement for groups electing S2d. Only `B01-DNSN` and `B02-DNSN` are implemented.
- **No DNSN tax-declaration forms**: TT58 specifies simplified quarterly tax declarations (01/DNSN-GTGT, 01/DNSN-TNDN). No template or service generates these.
- **No end-of-year finalization report**: per TT58, the year-end revenue/expense summary (used for groups 2/4 with `tinh_thue`) is not generated.

---

## 2. Thuế (Tax)

### 2.1 Tax configuration — **WELL STRUCTURED, CURRENT TO JAN-2026**

`apps/core/models.py` `TaxRateConfig` covers CIT/VAT/PIT/TTĐB/môn bài/trước bạ/FCT/BHXH cap. `TaxConfigService` (`apps/core/services/tax_config_service.py`) provides lookup + SME classification per NĐ 80/2021.

### 2.2 Thuế GTGT (VAT) — **PARTIALLY CURRENT**

- Standard 10% and reduced 8% (NĐ 174/2025, active through 2026-12-31) are present with toggle `vat_rate_reduced_active`.
- VAT TT80/2021 declaration form 01/GTGT is fully DB-driven via `apps/reporting/management/commands/seed_vat_tt80.py` and `VATReportLine` engine (`apps/reporting/services/vat_return.py`).
- Form 01/GTGT test coverage: `tests/test_vat_return.py`, `test_vat_engine.py`, `test_vat_lists.py`, `test_vat_xml.py`.
- **Gaps**:
  - **Luật GTGT 2026 (Law 09/2026/QH16, effective 2026-01-01)** is referenced in `seed_legal_references.py` but **not implemented**: it removes the 500-million revenue threshold for VAT registration, raises car (10-16 seats) VAT from 2% → 7% by 2031, allows refund when input VAT ≥ 300M, and exempts businesses with revenue < 1 billion VND. None of these rules are encoded.
  - **VAT codes** (`apps/master_data/management/commands/seed_tax_rates.py` and `apps/master_data/models/tax_rate.py` referenced indirectly): codes 00/04/05/08/10/KT exist for 0%/5%/8%/10%/not-subject. No code for the new "1 billion VND revenue exempt" category or for the new hybrid/EV car categories from Luật GTGT 2026.
  - VAT 8% reduction ends **2026-12-31**: no scheduler/alert to flip `vat_rate_reduced_active` back to False.

### 2.3 Thuế TNDN (CIT) — **PARTIALLY CURRENT**

- Tiered CIT rates 15% (micro, ≤3 tỷ), 17% (small, 3-50 tỷ), 20% (standard) are seeded per Luật TNDN 2025 (67/2025/QH15) and NĐ 320/2025.
- `TaxConfigService.get_cit_rate(company)` selects rate based on `Company.sme_size`.
- **Gaps**:
  - **NĐ 141/2026/NĐ-CP** (effective 2026-01-01) exempts enterprises with revenue ≤ 1 billion VND/year from CIT entirely. **No 0% / exempt tier is implemented.** `TaxRateConfig` has no field for an exemption threshold; `TaxConfigService.classify_sme` does not surface a "revenue under 1 tỷ → exempt" branch.
  - **NĐ 20/2026/NĐ-CP** (cited in `seed_legal_references`) grants CIT holiday: 3-year exemption + 50% reduction for 4 further years for new SMEs and innovative startups. **Not implemented** — no incentive-tracking model or rate-override service.
  - **No CIT declaration form 03/TNDN**: there is no `cit_return.py` analog to `vat_return.py`. CIT computation exists but no statutory declaration layout is generated.
  - `LegalReference` row "Luật Thuế TNDN" still cites the **old 2008 law** (with 2022 amendment note), not the current 67/2025/QH15 as primary.

### 2.4 Thuế TNCN (PIT) — **MIXED (CURRENT DEFAULT, OUTDATED FALLBACK)**

- Default values in `TaxRateConfig` (seeded by `seed_demo`): personal deduction 13,200,000 VND/month, dependent 5,200,000 VND/month, 5-bracket system 5%/10%/15%/20%/25% per Luật 09/2026/QH16 (effective from tax period 2026, i.e., 2026-01-01).
- Reserved future fields `pit_personal_deduction_2026` (15,500,000), `pit_dependent_deduction_2026` (6,200,000), and `pit_brackets_2026` are populated but **not wired into PayrollService**.
- `PITRateHistory` model + `seed_pit_history.py` correctly track 4 historical periods (2009/2013/2020/2026) with `is_current` flag.
- `apps/payroll/services/payroll_service.py` reads `TaxConfigService.get_active(company)` and applies `pit_personal_deduction` / `pit_dependent_deduction` / `pit_brackets` from the active config. **It uses the default 13.2M/5.2M fields, NOT the reserved 2026 fields.**
- **Gaps**:
  - **NQ 110/2025/UBTVQH15 (effective 2026-07-01)**: raises personal deduction to 15,500,000 VND/month, dependent to 6,200,000 VND/month. The seed_pit_history command has this entry **commented out**. Today's date is 2026-07-16 — this regulation is **already in force and not applied**.
  - **NĐ 253/2026/NĐ-CP + TT 87/2026/TT-BTC** (effective 2026-07-01): new non-taxable allowances — meal 1,200,000 VND/month (was 730,000), supplementary pension/life insurance 3,000,000 VND/month (was 1,000,000), dependent income threshold 3,000,000 VND/month (was 1,000,000), 10% withholding threshold 5,000,000 VND/payment (was 2,000,000), new medical deduction 23,000,000 VND/year, new education deduction 24,000,000 VND/year, 5-year PIT exemption for digital-tech professionals. **None of these are modeled.**
  - **PayrollService fallback constants**: `PERSONAL_DEDUCTION = Decimal("11000000")` and `DEPENDENT_DEDUCTION = Decimal("4400000")` (TT 111/2013 values) — used when `TaxRateConfig` is missing. Outdated by 6 months (Luật 09/2026 effective 2026-01-01). Should be 13,200,000 / 5,200,000 minimum.
  - **PayrollService PIT_BRACKETS** fallback: 7-bracket system (5%-35%) per TT 111/2013. Outdated. The 2026 system is 5-bracket (5%-25%).
  - **`Dependent` model** default `deduction_amount = 4400000`: hardcoded outdated value. Should pull from active config.
  - **Form 05/QTT-TNCN** (year-end PIT finalization): no template or service.
  - **Form 05/KH-TNCN** (monthly PIT withholding): no template or service.

### 2.5 Thuế TTĐB (Special Consumption Tax) — **CONFIG ONLY, NO CALCULATION**

- `TaxRateConfig` fields cover alcohol-high (65%/90% by 2031), alcohol-low (35%/60%), beer (65%/90%), tobacco rate (75%) + absolute (5,000 VND/pack), car-under-9 (15%), hybrid discount (70%) per Luật TTĐB 66/2025/QH15.
- **No SCT calculation service**: the rates are stored but never referenced by any invoice/posting path. Searches for `ttdb_` consumers return only `core/models.py` and `core/management/commands/seed_demo.py`.
- **No SCT declaration form 01/TTĐB**: no template.
- **Scheduled rate increases** (rượu ≥20° → 90% by 2031, bia → 90% by 2031, etc.): no year-aware lookup.

### 2.6 Thuế môn bài — **CONFIG ONLY**

- Two flat fees seeded per NĐ 22/2020 (>10 tỷ: 3M, ≤10 tỷ: 2M). No model field for chi nhánh (1M) or Hộ kinh doanh (300K-1M tiers). No annual declaration form 01/MBAI.

### 2.7 Other taxes

- **Thuế tài nguyên, thuế BVMT, thuế SD đất NN, thuế nhà thầu, thuế chuyển nhượng vốn, thuế lợi tức vốn nước ngoài, thuế XNK, lệ phí trước bạ**: all exist as `TaxType` dictionary entries seeded by `seed_tax_types.py`. No calculation services, no declaration forms, no invoice integration. Pure reference data only.

---

## 3. Lao động (Labor)

### 3.1 Insurance rates — **PARTIALLY OUTDATED**

- `apps/hr/services/insurance_service.py` `RATES` dict:
  - Employee: BHXH 8% + BHYT 1.5% + BHTN 1% = **10.5%** ✓ correct
  - Employer: BHXH 17% + BHYT 3% + BHTN 1% + BHTNLĐ-BNN 0.5% + KPCĐ 2% = **23.5%** ✓ correct
- **Mismatch in BHXH employer rate comment**: `payroll_service.py` line 24 says `BHXH DN đóng 17.5%` but the actual `RATES["bhxh_er"] = 0.17`. The comment is wrong; the code (17%) matches the canonical split (14% hưu trí + 3% ốm đau/thai sản). The remaining 0.5% for TNLĐ-BNN is separately captured in `bhtnld_er`. The combined "BHXH广义" is 17.5% but the code narrowly defines `bhxh_er = 0.17`. Behavior is correct; documentation is misleading.
- **Cap is OUTDATED**: `apps/hr/models/insurance.py` hardcodes `INSURANCE_CAP = 46800000` (20 × 2,340,000). NĐ 161/2026 (effective 2026-07-01) raised base salary to **2,530,000 VND/month**, making the new cap **50,600,000 VND/month**. Code is stale as of today (2026-07-16).
- `TaxRateConfig` has the same stale defaults: `base_salary = 2340000`, `bhxh_cap = 46800000` (seeded in `seed_demo.py`).
- **InsuranceService does not read from TaxRateConfig**: it imports `INSURANCE_CAP` constant directly. The `TaxRateConfig.bhxxh_cap` field exists but is never consumed.

### 3.2 Lương tối thiểu vùng (Minimum Wage) 2026 — **NOT IMPLEMENTED**

- No model, no service, no constant for region-based minimum wage.
- Searches for `luong_toi_thieu`, `minimum_wage`, `region_i`, `vung_i`, `2.680.000`, `3.420.000`, `4.960.000`, `5.310.000`, `4.730.000`, `4.140.000`, `3.700.000` return no matches in `apps/`.
- NĐ 293/2025 (effective 2026-01-01, +7.2% average) and NĐ 74/2024 (effective 2025-07-01) are referenced only as `LegalReference` rows, not in code.
- No `LaborContract.salary_base ≥ minimum_wage_for_region` validation.

### 3.3 Thuế TNCN từ lương — **SEE SECTION 2.4**

The payroll PIT pipeline (TaxConfigService → PayrollService) works but is frozen on Jan-2026 deductions; it does not pick up the Jul-2026 hike.

### 3.4 Hợp đồng lao động — **IMPLEMENTED, BASIC**

- `apps/hr/models/labor_contract.py` covers 4 contract types (Probation, Fixed-term, Indefinite, Seasonal) per Bộ luật Lao động 2019.
- `apps/contracts/management/commands/seed_contract_templates.py` provides PDF templates.
- Tests: `tests/test_labor_contract.py`.
- **Gaps**:
  - No fields for:BhxH start date, work-position classification, remote-work flag, part-time flag, secondment.
  - No automated check for the 12-month probation cap, 36-month fixed-term cap, or conversion-to-indefinite trigger.

### 3.5 BHXH/BHYT/BHTN declaration forms — **NOT IMPLEMENTED**

- No monthly BHXH declaration (Mẫu C12-TS), no labor-declaration form (TBHXH), no D02-TS template.

---

## 4. Đấu thầu (Bidding)

### 4.1 Luật Đấu thầu 23/2023/QH15 — **DISCREPANCY ON LAW NUMBER**

- `apps/bidding/apps.py` and `apps/bidding/models.py` docstring reference **"Luật Đấu thầu 23/2023/QH15"**.
- `apps/core/management/commands/seed_legal_references.py` and `apps/contracts/models.py` reference **"Luật Đấu thầu số 22/2023/QH15"**.
- The correct law is **22/2023/QH15** (passed 2023-06-19). `apps/bidding/apps.py` and `apps/bidding/models.py` have the wrong number "23/2023".

### 4.2 Models implemented — **ADEQUATE FOR CRM-STYLE TRACKING**

- `ContractorProfile` (capability level I/II/III/unranked).
- `BidOpportunity`: bidding methods (Open/Limited/Direct/Self-performed/Community) — matches Luật 22/2023 Article 20.
- Bid forms (one-stage, one-stage-two-envelopes, two-stage) — matches Article 39.
- `BidDocument`, `BidSubmission`, `BidResult`.
- Link to national procurement system (`muasamcong.mpi.gov.vn`) via `bid_system_ref`.

### 4.3 Services — **CONVERT-TO-CONTRACT ONLY**

- `BidConverterService` (`apps/bidding/services.py`) marks a bid WON and auto-creates a `Contract`. No bid evaluation, no scoring, no dossiers, no notice publication.

### 4.4 Contract types — **3 of 8 IMPLEMENTED**

- `apps/contracts/models.py` `Contract.ContractType` exposes 3 bidding flavors: `BIDDING_LUMP_SUM`, `BIDDING_UNIT_PRICE`, `BIDDING_CONSULTING`.
- Luật 22/2023 Article 68 defines 8 contract types (trọn gói, đơn giá cố định, đơn giá điều chỉnh, theo thời gian, khung, quản lý dự án, tư vấn, khác). Missing: fixed-unit-price vs adjustable-unit-price distinction (collapsed into one), time-based, framework, project-management.

### 4.5 Templates — **NONE FOR BIDDING**

- `seed_contract_templates.py` ships labor/sale/purchase/construction templates but searches for "bid" / "thầu" inside the file return no matches. No bid-document templates, no bid-security guarantee template, no advance-payment guarantee template.

### 4.6 Implementing decrees — **REFERENCED BUT NOT ENFORCED**

- `LegalReference` rows for NĐ 24/2024 (Lựa chọn nhà thầu), TT 02/2023/TT-BXD (sample contracts) are seeded. None of the actual procedural rules are encoded.

### 4.7 Tests — **EXIST BUT LIGHT**

- `tests/test_bidding.py`, `tests/test_pit_history_bidding.py` (the latter actually tests PIT history despite the name).

**Overall**: Bidding module is a CRM-style opportunity tracker, not a full procurement system. Acceptable for sales-led bidding shops; insufficient for owner-side procurement or contractor-side compliance with Luật 22/2023.

---

## 5. Hóa đơn điện tử (E-invoice)

### 5.1 TT78/2021/TT-BTC — **CODE LABEL IS STALE**

- `apps/einvoice/models.py` docstring says "per TT78/2021/TT-BTC". Real regulation is now **NĐ 254/2026/NĐ-CP** (effective 2026-07-01) + **TT 91/2026/TT-BTC** (effective 2026-07-01) + **Luật Quản lý thuế 108/2025/QH15**. Today is 2026-07-16; the new framework is already in force.
- `LegalReference` rows for these three documents are **missing** — `seed_legal_references.py` includes `TT32/2025` (already superseded) and `NĐ123/2020` (already superseded) but not NĐ 254/2026, TT 91/2026, or Luật QLT 108/2025.

### 5.2 Forms supported — **BOTH 01GTKT and 02BANHANG**

- `EInvoiceFormSymbol` enum: `01GTKT` (Hóa đơn GTGT — for VAT khấu trừ) and `02BANHANG` (Hóa đơn bán hàng — for VAT tỷ lệ %). 
- `EInvoiceService.default_form_symbol_for_company` correctly selects based on `Company.vat_method`.
- Tests: `tests/test_einvoice.py`, `test_einvoice_02banhang.py`, `test_einvoice_pdf.py`.

### 5.3 Providers supported — **GOOD COVERAGE**

- `EInvoiceProvider`: Manual, MISA, VNPT, eHoadon, BKAV, Viettel. API calls are stubbed (`_call_provider_api` echoes back) — only the `MANUAL` mode (operator uploads signed PDF) is fully functional.

### 5.4 Reports — **BC01 / BC26 / TB04**

- `EInvoiceReportBatch.ReportType`: BC01 (situational usage), BC26 (periodic), TB04 (issuance notice). `EInvoiceReportService.generate_bc01` produces XML.

### 5.5 XML schema — **SIMPLIFIED, NOT COMPLIANT**

- `_build_xml` produces a hand-rolled XML. Real TT78 (and now TT91/2026) schemas are far more structured (UBL-style with `LTHDL`, `KHMSHIEU`, `KHHDon`, `TgCTb`, signature block `DS:Signature`). No XSD validation. No digital signature integration.

### 5.6 NĐ 254/2026 specific requirements — **NOT IMPLEMENTED**

- **Coded vs uncoded invoices** (HĐĐT có mã / không mã của CQT): the model has `status` (Draft/Issued/Adjusted/Replaced/Cancelled) but no field distinguishing the new NĐ 254 "có mã" vs "không mã" taxonomy, nor the new "HĐĐT khởi tạo từ máy tính tiền" (cash-register invoice per TT 32/2025).
- **Tax-authority pre-issuance validation**: NĐ 254 requires invoices to be transmitted to CQT before delivery to buyer. No transmission service exists.
- **Invoice adjustment/replacement** is implemented (`adjust`, `cancel`) but does not follow the new TT 91/2026 procedure (which mandates a specific replacement-record format and a 24-hour cooling-off).
- **Cash-register invoice** (TT 32/2025, recently replaced by TT 91/2026 §3): no model.
- **Bill of lading / warehouse receipt e-document** (NĐ 254 §6 new category): no model.

### 5.7 Households (HKD) — **MISSING**

- Per NĐ 254/2026 and TT 50/2026/TT-BTC, household businesses with revenue > 1 billion VND/year must use e-invoices. `Company.EntityType` includes `HO_KINH_DOANH` and `CA_NHAN_KINH_DOANH` but no e-invoice gating logic.

---

## 6. Summary of Compliance Gaps

### Priority 1 — Regulatory now in force, code not updated (HIGH RISK)

| # | Area | Issue | Regulation | In force since |
|---|------|-------|------------|----------------|
| 1.1 | PIT | Personal/dependent deductions 13.2M/5.2M used by PayrollService; should be 15.5M/6.2M | NQ 110/2025 + NĐ 253/2026 + TT 87/2026 | 2026-07-01 |
| 1.2 | PIT | PayrollService fallback constants stuck at 11M/4.4M (TT 111/2013) and 7-bracket | Luật 09/2026/QH16 | 2026-01-01 |
| 1.3 | Labor | Insurance cap 46.8M; should be 50.6M. Base salary 2.34M; should be 2.53M | NĐ 161/2026 | 2026-07-01 |
| 1.4 | Labor | `InsuranceService` imports hardcoded `INSURANCE_CAP` constant, ignores `TaxRateConfig.bhxh_cap` | NĐ 161/2026 | 2026-07-01 |
| 1.5 | PIT | New NĐ 253/2026 non-taxable allowances not modeled (meal 1.2M, pension 3M, medical 23M/yr, education 24M/yr, etc.) | NĐ 253/2026 + TT 87/2026 | 2026-07-01 |
| 1.6 | E-invoice | Module labeled "TT78/2021"; current law is NĐ 254/2026 + TT 91/2026 + Luật QLT 108/2025 (all in force) | NĐ 254/2026, TT 91/2026, Luật 108/2025 | 2026-07-01 |
| 1.7 | CIT | No CIT exemption for enterprises with revenue ≤ 1 billion VND/year | NĐ 141/2026 | 2026-01-01 |

### Priority 2 — Required features missing (MEDIUM RISK)

| # | Area | Issue |
|---|------|-------|
| 2.1 | Accounting | No `load_tt200` / `load_tt99` chart loader despite TT200 enum being selectable. Silent fall-through to TT133 chart. |
| 2.2 | Accounting | TT58 missing `B03-DNSN` (cash-flow) report. |
| 2.3 | Accounting | TT58 missing quarterly tax-declaration forms 01/DNSN-GTGT, 01/DNSN-TNDN. |
| 2.4 | Tax | No CIT declaration form 03/TNDN. CIT computed but never declared. |
| 2.5 | Tax | No PIT declaration forms 05/QTT-TNCN (finalization), 05/KH-TNCN (monthly withholding). |
| 2.6 | Tax | TTĐB rates stored but no calculation service, no 01/TTĐB declaration form, no year-aware scheduled increases. |
| 2.7 | Labor | No region-based minimum wage table (4 regions). Labor contracts have no minimum-wage validation. |
| 2.8 | Labor | No BHXH declaration forms (C12-TS, D02-TS). |
| 2.9 | E-invoice | No coded/uncoded invoice taxonomy. No cash-register invoice (TT 32/2025 → TT 91/2026). No CQT pre-issuance transmission. |
| 2.10 | E-invoice | XML schema is hand-rolled; not TT78/TT91-compliant. No digital signature. |
| 2.11 | VAT | Luật GTGT 2026 (Law 09/2026/QH16): 1-billion-revenue exemption, 300M refund threshold, 10-16-seat car schedule — not encoded. |
| 2.12 | VAT | VAT 8% reduction toggle ends 2026-12-31 — no auto-flip or alert scheduler. |
| 2.13 | CIT | NĐ 20/2026 CIT holiday (3yr exempt + 4yr 50%) not modeled. |

### Priority 3 — Data hygiene and correctness bugs (LOWER RISK)

| # | Area | Issue |
|---|------|-------|
| 3.1 | Bidding | Law number mismatch: `apps/bidding/apps.py` and `apps/bidding/models.py` cite "23/2023/QH15" (wrong); correct is **22/2023/QH15**. |
| 3.2 | Dependent | `Dependent.deduction_amount` default hardcoded to 4,400,000 (out of date). |
| 3.3 | LegalReference | Row "Luật Thuế TNDN" still cites the old 2008/2022 law as primary instead of 67/2025/QH15. |
| 3.4 | LegalReference | Missing NĐ 254/2026, TT 91/2026, Luật QLT 108/2025, NĐ 161/2026, NĐ 293/2025, TT 87/2026, NĐ 253/2026, TT 50/2026, NĐ 141/2026 — none seeded. |
| 3.5 | Accounting | QĐ48/2006 enum choice has no implementation; should be deprecated. |
| 3.6 | Bidding | Only 3 of 8 contract types in `Contract.ContractType` per Luật 22/2023 Article 68. |
| 3.7 | E-invoice | `EInvoiceService._call_provider_api` is a stub returning echo — only MANUAL mode is functional. |
| 3.8 | Reporting | No tax declaration forms at all (only financial statements + 01/GTGT). Tax type list seeded but no declaration engine per type. |
| 3.9 | Payroll | Misleading comment "BHXH DN đóng 17.5%" in `payroll_service.py` (actual rate is 17% + 0.5% BHTNLĐ-BNN separately). |

### Test coverage observations

- Strong: TT58 DNSN (9 test files), VAT engine (4 files), ledger/voucher (8 files).
- Weak: Bidding (1 test file), CIT (none — no test for tiered rate lookup), TTĐB (none), PIT 2026 hike (only `test_pit_2026_fix.py` for Jan-2026 values; no test for Jul-2026 hike).
- Missing: TT200/QĐ48 (none), minimum wage (none), e-invoice XML schema compliance (none), NĐ 254 cash-register invoice (none).

---

## Appendix A — Key file paths

- Tax configuration: `apps/core/models.py` (TaxRateConfig, PITRateHistory, TaxType, LegalReference)
- Tax lookup services: `apps/core/services/tax_config_service.py`, `apps/core/services/tndn_calculation_service.py`
- Insurance: `apps/hr/models/insurance.py`, `apps/hr/services/insurance_service.py`
- Payroll + PIT: `apps/payroll/services/payroll_service.py`, `apps/payroll/models.py`
- DNSN ledger: `apps/ledger/models/dnsn.py`, `apps/ledger/dnsn_ledger_types.py`, `apps/ledger/services/dnsn_posting_service.py`
- E-invoice: `apps/einvoice/models.py`, `apps/einvoice/services/__init__.py`
- Bidding: `apps/bidding/models.py`, `apps/bidding/services.py`
- Reporting: `apps/reporting/models.py`, `apps/reporting/services/{vat_return,pnl,balance_sheet,cash_flow,dnsn_report_service,hr_reports}.py`
- Seeds: `apps/core/management/commands/{seed_demo,seed_legal_references,seed_pit_history,seed_tax_types,seed_tt58_demo}.py`, `apps/master_data/management/commands/load_tt133.py`, `apps/reporting/management/commands/seed_vat_tt80.py`

## Appendix B — Outdated constants to update

| File | Constant | Current | Should be |
|------|----------|---------|-----------|
| `apps/hr/models/insurance.py` | `INSURANCE_CAP` | 46,800,000 | 50,600,000 |
| `apps/payroll/services/payroll_service.py` | `PERSONAL_DEDUCTION` | 11,000,000 | 15,500,000 |
| `apps/payroll/services/payroll_service.py` | `DEPENDENT_DEDUCTION` | 4,400,000 | 6,200,000 |
| `apps/payroll/services/payroll_service.py` | `PIT_BRACKETS` | 7-bracket 5-35% | 5-bracket 5-25% |
| `apps/hr/models/labor_contract.py` | `Dependent.deduction_amount` default | 4,400,000 | derive from TaxRateConfig |
| `apps/core/management/commands/seed_demo.py` | `TaxRateConfig.base_salary` | 2,340,000 | 2,530,000 |
| `apps/core/management/commands/seed_demo.py` | `TaxRateConfig.bhxh_cap` | 46,800,000 | 50,600,000 |
| `apps/core/management/commands/seed_pit_history.py` | commented-out NQ 110/2025 row | (disabled) | enable as current |
| `apps/bidding/apps.py`, `apps/bidding/models.py` | "23/2023/QH15" | wrong | "22/2023/QH15" |
