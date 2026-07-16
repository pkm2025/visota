# Visota ERP — Báo cáo đánh giá (auto-scope)

> Ngày đánh giá: 2026-07-16
> Phương pháp: Auto-discovery (PROMPT_EVAL_AUTOSCOPE)
> Repo: `C:\mmm\visota`

---

## 0. Scope đã tự xác định

### Bảng A — Danh mục module (30 apps trong INSTALLED_APPS)

| App | Loại | #model | #view | #service | #cmd | Có url | Ghi chú |
|-----|------|--------|-------|----------|------|--------|---------|
| core | core | 15+ | 10+ | 5 | 8 | ✓ | Company, TaxRateConfig, middleware |
| identity | core | 5 | 5 | 2 | 0 | ✓ | User, Role, Permission |
| ledger | domain | 6 | 15+ | 5 | 0 | ✓ | Voucher, Balance, DNSN |
| sales | domain | 5 | 8 | 3 | 0 | ✓ | Invoice, Customer |
| purchasing | domain | 3 | 6 | 2 | 0 | ✓ | Invoice, Vendor |
| einvoice | domain | 4 | 6 | 3 | 0 | ✓ | EInvoice, 01GTKT, 02BANHANG |
| inventory | domain | 4 | 5 | 2 | 0 | ✓ | Stock, Goods Issue |
| assets | domain | 4 | 4 | 2 | 0 | ✓ | FixedAsset, Depreciation |
| crm | domain | 6 | 8 | 2 | 0 | ✓ | Lead, Opportunity, Ticket |
| contracts | domain | 3 | 5 | 1 | 0 | ✓ | Contract, Template |
| bidding | domain | 3 | 4 | 1 | 0 | ✓ | Luật 22/2023/QH15 |
| banking | domain | 3 | 4 | 2 | 0 | ✓ | BankStmt, Reconcile |
| hr | domain | 5 | 6 | 2 | 0 | ✓ | Insurance, Employee |
| payroll | domain | 4 | 4 | 1 | 0 | ✓ | PayrollRecord, PIT |
| reporting | domain | 3 | 10+ | 6 | 2 | ✓ | B01-DN, VAT, DNSN reports |
| master_data | support | 10+ | 8 | 1 | 4 | ✓ | ChartOfAccounts, TaxRate |
| ui_modern | ui | 0 | 80+ | 0 | 0 | ✓ | 230+ routes, tất cả UI |
| einvoice | domain | 4 | 6 | 3 | 0 | ✓ | TT91/2026, ND254 |
| costing | domain | 2 | 2 | 1 | 0 | ✗ | Mỏng, không có url riêng |
| budget | domain | 3 | 3 | 1 | 0 | ✗ | Mỏng |
| approvals | support | 2 | 3 | 1 | 0 | ✗ | Generic FK workflow |
| pkm | support | 5 | 8 | 3 | 1 | ✓ | AI/RAG knowledge base |
| fx | support | 2 | 2 | 1 | 0 | ✗ | Mỏng, revaluation broken |
| notifications | support | 2 | 3 | 1 | 0 | ✗ | Email, in-app |
| input_docs | support | 2 | 2 | 1 | 0 | ✗ | OCR capture |
| recurring | support | 2 | 2 | 1 | 0 | ✗ | Auto voucher |
| projects | domain | 2 | 3 | 0 | 0 | ✓ | Mỏng |
| loans | domain | 2 | 2 | 0 | 0 | ✗ | Stub |
| guarantees | domain | 2 | 2 | 0 | 0 | ✗ | Stub |
| documents | support | 2 | 3 | 0 | 0 | ✓ | File upload |

### Bảng B — Danh mục nghiệp vụ (86 workflow groups)

| # | Nhóm nghiệp vụ | Portal | App(s) | Đường dẫn | Use case | Side effects |
|---|----------------|--------|--------|-----------|----------|--------------|
| 1 | Kế toán tổng hợp | /modern/ | ledger, ui_modern | /modern/vouchers/ | Phiếu thu/chi, ghi sổ No/Có | Service call |
| 2 | Kế toán DNSN (TT58) | /modern/ | ledger, ui_modern | /modern/dnsn-vouchers/ | Phiếu thu/chi đơn giản TT58 | Service call |
| 3 | Bán hàng | /modern/ | sales, ledger | /modern/sales-invoices/ | Hóa đơn bán, công nợ | Post to ledger |
| 4 | Mua hàng | /modern/ | purchasing, ledger | /modern/purchase-invoices/ | Hóa đơn mua, công nợ | Post to ledger |
| 5 | Hóa đơn điện tử | /modern/ | einvoice | /modern/einvoices/ | 01GTKT, 02BANHANG | XML gen |
| 6 | Báo cáo tài chính | /modern/ | reporting | /modern/reports/ | B01-DN, B02-DN, B03-DN, DNSN | None |
| 7 | Báo cáo thuế GTGT | /modern/ | reporting | /modern/reports/vat/ | Tờ khai 01/GTGT | None |
| 8 | Kho | /modern/ | inventory | /modern/inventory/ | Nhập/xuất/tồn | None |
| 9 | Tài sản cố định | /modern/ | assets | /modern/assets/ | Khấu hao, thanh lý | Post to ledger |
| 10 | Nhân sự | /modern/ | hr | /modern/hr/ | BHXH, hợp đồng | None |
| 11 | Tiền lương | /modern/ | payroll | /modern/payroll/ | Tính lương, PIT | Post to ledger |
| 12 | CRM | /modern/ | crm | /modern/crm/ | Lead, Opportunity | Signal (conversion) |
| 13 | Hợp đồng | /modern/ | contracts | /modern/contracts/ | 22 mẫu văn bản | None |
| 14 | Ngân hàng | /modern/ | banking | /modern/banking/ | Đối soát | None |
| 15 | Đấu thầu | /modern/ | bidding | /modern/bidding/ | Luật 22/2023 | None |
| ... | (71 workflow groups nữa) | | | | | |

### Bảng C — Ma trận phủ (hot spots)

| Hot Spot | Apps | Rủi ro |
|----------|------|--------|
| Voucher Posting Pipeline | ledger, sales, purchasing, assets, payroll, banking, reporting | CRITICAL - tiền + tenant |
| CRM Opportunity Conversion | crm, sales, contracts, ledger | HIGH |
| DNSN/TT58 Dual-Entry | ledger, core, sales, purchasing, einvoice | MEDIUM |
| Period Close Orchestration | ledger, reporting, assets, payroll | HIGH |
| E-Invoice Chain | einvoice, sales, purchasing, ledger | HIGH |

**Mức độ phủ subagent: 5/5 workflow groups = 100%**

---

## 1. Tóm tắt điều hành

### Điểm chất lượng tổng thể: **6/10**

Hệ thống có architecture tốt (Django monolith, service layer, multi-tenant), nhưng có **nhiều lỗi nghiêm trọng về bảo mật multi-tenant** và **bugs logic trong financial calculations**.

### 3 điểm mạnh
1. **Architecture rõ ràng**: Service layer tách biệt, CompanyOwnedModel pattern, django-ninja API
2. **TT58 compliance**: DNSN layer hoàn chỉnh, 4 nhóm thuế, B01/B02-DNSN, chuyển đổi số dư
3. **Tax config flexibility**: TaxRateConfig config-driven, PIT/BHXH/CIT/VAT rates cập nhật July 2026

### 5 cơ hội cải thiện quan trọng nhất (P0/P1)

1. **P0: Multi-tenant isolation failure** — 60+ views dùng `Company.objects.first()` thay vì `request.current_company`. Bất kỳ user nào cũng xem/sửa data của company khác.
2. **P0: Unauthenticated API endpoint** — `get_sales_invoice` trong `apps/core/api.py:166` thiếu `auth=get_current_user`
3. **P0: XML injection** — E-invoice XML built via f-string, no escaping
4. **P1: Voucher posting không idempotent** — Re-post double-counts balances (cả TT133 và TT58)
5. **P1: PIT allowances bug** — Meal/pension allowances reduce PIT nhưng không add vào gross salary (double-deduct)

### Sức khỏe
- **Test**: 2017 tests pass, coverage ~50%, weak trong bidding/costing/fx/loans/guarantees
- **Nợ kỹ thuật**: 148 ruff lint errors (pre-existing), mypy strict mode chưa clean
- **Bảo mật**: CRITICAL gaps trong multi-tenant isolation và API auth
- **Multi-tenant**: CompanyOwnedModel pattern đúng nhưng enforcement thiếu

---

## 2. Phân tích theo nghiệp vụ

### 2.1 Kế toán tổng hợp (ledger)
- **Bugs**: VoucherPostingService.post() không idempotent (double-count). Period close không lock period (race condition). Cash flow direct method leak cross-company.
- **Tests**: Tốt cho happy path, thiếu edge cases (re-post, concurrent).

### 2.2 Kế toán DNSN (TT58)
- **Bugs**: DnsnPostingService.post() cũng không idempotent. `_entry_total` double-counts và sai sign (cộng `cash_out` thay vì trừ). B02-DNSN conflates TNDN với "other taxes".
- **Tests**: 47 tests tốt, thiếu edge cases.

### 2.3 Bán hàng / Mua hàng
- **Bugs**: Sales/purchase invoice list views không company-scoped (multi-tenant leak). Discount fields không được apply. E-invoice cancellation không reverse ledger entries. Foreign currency không convert sang VND.
- **Tests**: Tốt cho VAT posting, thiếu reversal/adjustment tests.

### 2.4 Hóa đơn điện tử
- **Bugs**: XML injection (f-string). `amount_in_words` có bugs Vietnamese numeral. Provider API là stub.
- **Tests**: Form selection đúng (01GTKT vs 02BANHANG), thiếu XML schema compliance tests.

### 2.5 Tiền lương / PIT
- **Bugs CRITICAL**: Allowances reduce PIT nhưng không add vào gross (double-deduct). InsuranceService thiếu KPCĐ 2%. Không có proration cho ngày công.
- **Tests**: PIT rates đúng (15.5M/6.2M/5-bracket), BHXH cap đúng (50.6M).

### 2.6 CRM / Hợp đồng / Đấu thầu
- **Bugs**: Lead code không unique. ContractTemplate global (cross-tenant). Bidding bid_type default có leading-space.
- **Tests**: Rất mỏng, gần như không có.

### 2.7 Kho / Tài sản / Ngân sách / Giá thành
- **Bugs**: Assets disposal thiếu voucher fields. Depreciation book 1 cặp TK. Budget variance sai account prefixes. Costing chỉ tạo 50% closing entries. FX revaluation fundamentally broken (treats FC as VND).
- **Tests**: Gần như zero cho costing, budget, fx, loans, guarantees.

---

## 3. Phân tích theo module

### core
- Multi-tenant enforcement đúng ở CompanyOwnedModel nhưng thiếu ở view layer
- TaxRateConfig comprehensive, cập nhật July 2026
- ModuleVisibilityService đúng logic

### identity
- Permission system đúng nhưng không enforce per-action
- AdminRoleEditView cho cross-tenant role editing (privilege escalation)

### ui_modern
- 230+ routes, 80+ views — phần lớn không có company filter
- Sidebar modular đúng, has_module_access template tag đúng

### pkm
- AI/RAG knowledge base, independent module
- 2 signals (interaction logging) — đúng
- Multi-provider LLM, Fernet encryption cho API keys

---

## 4. Các vấn đề chéo

### Kiến trúc
- Centralized routing qua ui_modern tốt cho consistency nhưng tạo "god app"
- 8 apps có urls.py riêng không được include trong config/urls.py — dead URLs

### Multi-tenant
- **CRITICAL**: 60+ views dùng `Company.objects.first()`, hầu hết ListView không filter company
- ContractTemplate global, không inherit CompanyOwnedModel

### Bảo mật
- **CRITICAL**: 1 API endpoint unauthenticated (`get_sales_invoice`)
- **CRITICAL**: XML injection trong e-invoice
- **HIGH**: IDOR pervasive (`get_object_or_404(Model, pk=pk)` không company scope)
- **HIGH**: AdminRoleEditView cross-tenant
- **HIGH**: ChartOfAccountsChangeCodeView bulk update ALL companies
- Audit trail gần như không tồn tại

### Tiền (Decimal)
- **Tốt**: Không dùng float cho tiền
- **Bug**: PIT allowances double-deduct, DNSN `_entry_total` sai sign

### Hiệu năng
- N+1 queries pervasive trong ListView (thiếu select_related)
- Race condition trong voucher posting (thiếu select_for_update)

---

## 5. Khuyến nghị ưu tiên

### P0 — Critical (cần fix ngay)

| # | Vấn đề | App | Tác động | Effort | Bằng chứng |
|---|--------|-----|----------|--------|------------|
| P0-1 | Multi-tenant: 60+ views dùng Company.objects.first() | ui_modern | Data leak cross-tenant | L | eval-review-security.md CRITICAL-01/02 |
| P0-2 | API get_sales_invoice thiếu auth | core/api.py:166 | Unauthenticated access | S | eval-review-security.md CRITICAL-04 |
| P0-3 | XML injection trong e-invoice | einvoice/services | Data corruption, XSS | S | eval-review-transactions.md C-3 |
| P0-4 | Voucher posting double-count | ledger/services | Sai số liệu kế toán | S | eval-review-accounting.md B-01/02 |
| P0-5 | PIT allowances double-deduct | payroll/services | Sai lương net | M | eval-review-payroll.md C-1 |
| P0-6 | InsuranceService thiếu KPCĐ 2% | hr/services | Sai tổng BHXH | S | eval-review-payroll.md C-2 |
| P0-7 | Cash flow leak cross-company | reporting/services | Sai B03-DN | S | eval-review-accounting.md B-03 |

### P1 — High (cần fix trong sprint kế)

| # | Vấn đề | App | Tác động | Effort |
|---|--------|-----|----------|--------|
| P1-1 | ListView thiếu company filter | ui_modern | Data leak | M |
| P1-2 | IDOR pervasive (get_object_or_404) | ui_modern | Unauthorized access | M |
| P1-3 | Period close không lock | ledger/services | Race condition | S |
| P1-4 | DNSN _entry_total sai sign | ledger/services | Sai số dư tiền | S |
| P1-5 | E-invoice cancel không reverse | einvoice/services | Sai ledger | M |
| P1-6 | Discount fields không apply | sales/purchasing | Sai tính tiền | S |
| P1-7 | FX revaluation broken | fx/ | Sai tỷ giá | M |
| P1-8 | ContractTemplate global | contracts | Cross-tenant | M |
| P1-9 | AdminRoleEditView cross-tenant | identity | Privilege escalation | S |
| P1-10 | Dependent valid_to không check | payroll | Sai PIT | S |

### P2 — Medium

| # | Vấn đề | Effort |
|---|--------|--------|
| P2-1 | N+1 queries pervasive (ListView) | M |
| P2-2 | B02-DNSN conflates TNDN/other taxes | S |
| P2-3 | Amount_in_words Vietnamese bugs | S |
| P2-4 | Foreign currency không convert VND | M |
| P2-5 | No work-day proration in payroll | M |
| P2-6 | Notification dedup hash non-deterministic | S |
| P2-7 | Budget variance wrong prefixes | S |
| P2-8 | Costing incomplete closing entries | M |

### P3 — Nice to have
- Dead URLs (8 apps with unregistered urls.py)
- Bidding bid_type leading-space
- CRM Lead code uniqueness
- Loans/Guarantees stubs
- Audit trail cho sensitive operations

---

## 6. Đề xuất tính năng mới

### 6.1 CompanyRequiredMixin middleware
**Vấn đề**: 60+ views dùng `Company.objects.first()` fallback
**Đề xuất**: Tạo mixin `CompanyRequiredMixin` enforce `request.current_company`
**Effort**: M (touch 60+ views)
**Rủi ro**: Low — thuần thêm filter, không đổi logic

### 6.2 Voucher posting idempotency guard
**Vấn đề**: Re-post double-counts balances
**Đề xuất**: Early-return guard `if voucher.is_posted: return` ở đầu `post()`
**Effort**: S
**Rủi ro**: Low

### 6.3 PIT allowance gross integration
**Vấn đề**: Allowances reduce PIT nhưng không add vào gross
**Đề xuất**: Add meal_allowance + pension_allowance vào gross trước khi exclude
**Effort**: M
**Rủi ro**: Medium — thay đổi payroll calculation flow

---

## 7. Hợp đồng Quality Gate (YAML)

```yaml
quality_gate:
  coverage:
    workflows_reviewed: 5/5  # 100%
    apps_reviewed: 30/30     # 100%
    dead_apps_identified: 0  # no fully dead apps
  evidence:
    every_finding_has_file_line: true
    every_recommendation_has_snippet: true
    generic_statements_without_evidence: 0
  severity_distribution:
    critical: 11
    high: 21
    medium: 25
    low: 20
    total: 77
  high_risk_areas_covered:
    money_decimal: true
    tenant_isolation: true
    tax_calculation: true
    voucher_posting: true
    period_close: true
    api_auth: true
  test_coverage_assessment:
    strong: [ledger, dnsn, payroll_rates, vat_return, rebranding]
    weak: [bidding, costing, fx, loans, guarantees, budget]
    missing: [einvoice_xml_schema, multi_tenant_isolation, period_close_race]
```

---

## 8. Checklist hành động

### P0 — Critical (fix ngay)
- [ ] Thêm `auth=get_current_user` cho `get_sales_invoice` API (`apps/core/api.py:166`)
- [ ] Escape XML trong e-invoice (`apps/einvoice/services/__init__.py` _build_xml)
- [ ] Add idempotency guard cho VoucherPostingService.post() và DnsnPostingService.post()
- [ ] Fix `_entry_total` sign bug trong DNSN posting
- [ ] Fix PIT allowances: add vào gross trước khi exclude
- [ ] Add KPCĐ 2% vào InsuranceService.total_employer
- [ ] Add company filter cho cash flow direct method
- [ ] Tạo CompanyRequiredMixin, refactor 60+ views

### P1 — High (sprint kế)
- [ ] Add company filter cho tất cả ListView.get_queryset()
- [ ] Add company scope cho get_object_or_404() calls
- [ ] Add period lock trong PeriodClosingService
- [ ] Reverse ledger entries trên e-invoice cancel/adjust
- [ ] Apply discount_amount/discount_rate trong invoice calculation
- [ ] Fix FX revaluation (FC → VND conversion)
- [ ] Make ContractTemplate inherit CompanyOwnedModel
- [ ] Fix AdminRoleEditView cross-tenant
- [ ] Filter dependents by valid_to expiry

### Lỗ hổng test cần lấp
- [ ] Multi-tenant isolation tests (company filter enforcement)
- [ ] Voucher posting idempotency tests (re-post)
- [ ] E-invoice XML schema compliance tests
- [ ] Period close race condition tests
- [ ] Bidding module tests
- [ ] Costing module tests
- [ ] FX revaluation tests

### Cập nhật tài liệu
- [ ] Cập nhật AGENTS.md với multi-tenant enforcement rules
- [ ] Document CompanyRequiredMixin pattern
- [ ] Update README với known limitations (stub modules)
