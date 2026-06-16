# 01. Lộ trình triển khai (Roadmap)

> Đề xuất thứ tự phát triển, timeline, milestones.

## 1. Tổng quan timeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                       PMKETOAN DEVELOPMENT ROADMAP                    │
└──────────────────────────────────────────────────────────────────────┘

Phase 0: Foundation     [Tuần 1-4]      ████████░░░░░░░░░░░░░░░░░░░░░░
Phase 1: GL & Master    [Tuần 5-12]     ░░░░░░░░██████████████░░░░░░░░
Phase 2: Core BIZ       [Tuần 13-20]    ░░░░░░░░░░░░░░░░░░░░██████████
Phase 3: Asset & Cost   [Tuần 21-26]    ░░░░░░░░░░░░░░░░░░░░░░░░██████
Phase 4: HR & Payroll   [Tuần 27-32]    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░██
Phase 5: Reports        [Tuần 33-36]    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Phase 6: Polish & GA    [Tuần 37-40]    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← Modern UI live
─ ─ ─ ─ ─ GO-LIVE Modern UI ─ ─ ─ ─ ─
Phase 7: Classic UI     [Tháng 11-12]   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← Classic layout pack
Phase 8: Mobile PWA     [Tháng 13-15]   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← Mobile layout pack
Phase 9: Portal UI      [Tháng 16-17]   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← Customer/vendor portal

Phase 0-6: ~9-10 tháng (Modern UI đầy đủ)
Phase 7-9: +6-7 tháng (multi-UI đầy đủ)
```

## 2. Phân chia giai đoạn

### Phase 0: Foundation (4 tuần)

**Mục tiêu**: Setup project, infrastructure, conventions.

**Deliverables**:
- [ ] Repository + branching strategy
- [ ] VPS setup scripts (Ubuntu 24.04 LTS)
- [ ] Django 5.2 + MariaDB 11.4 + django-q2 setup
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Linting (ruff + black + mypy)
- [ ] Test framework (pytest + factory_boy)
- [ ] Initial folder structure
- [ ] Base layout templates (login, dashboard, navigation)
- [ ] Base HTMX + Alpine + Bootstrap integration
- [ ] Documentation site (mkdocs or similar)

**Team**: 1 senior + 1 mid dev

### Phase 1: GL + Master Data (8 tuần)

**Mục tiêu**: Lõi kế toán có thể chạy.

**Deliverables**:
- [ ] Module `core`: Company model, multi-tenant middleware
- [ ] Module `identity`: User, Role, Permission, JWT auth
- [ ] Module `system`: Fiscal year, parameters, voucher book
- [ ] Module `master_data`:
  - Chart of accounts (TT133 default)
  - Currency, exchange rate
  - Cost center
  - Bank account
- [ ] Module `ledger`:
  - AccountingVoucher + VoucherLine
  - VoucherPostingService
  - AccountOpeningBalance
  - AccountPeriodBalance
  - ClosingTemplate + PeriodClosingService
  - YearEndCarryForwardService
- [ ] Màn hình voucher list + form (HTMX)
- [ ] Sổ cái (S03b-DN)
- [ ] Bảng cân đối tài khoản (S06-DN)
- [ ] Audit log

**Team**: 2 dev + 1 QA

**Demo milestone**: Có thể tạo phiếu kế toán, ghi sổ, xem sổ cái và BCĐTK.

### Phase 2: Core Business (8 tuần)

**Mục tiêu**: Mua - Bán - Kho - Tiền đầy đủ.

**Deliverables**:
- [ ] Module `treasury`:
  - Cash voucher (thu/chi)
  - Bank transaction
  - Advance payment
  - Loan agreement
  - Sổ quỹ tiền mặt, sổ TGNH
- [ ] Module `sales`:
  - Customer master
  - Sales invoice + lines
  - AR aging
  - Real-time customer balance
- [ ] Module `purchasing`:
  - Vendor master
  - Purchase invoice
  - AP aging
- [ ] Module `inventory`:
  - Product master
  - Warehouse
  - Stock voucher (receipt/issue/transfer)
  - Stock card, stock ledger
  - Cost calculation (3 methods)
- [ ] Master-detail grid component reusable
- [ ] Form chung tu reusable (multi-tab, dynamic lines)

**Team**: 3 dev + 1 QA

**Demo milestone**: Vòng lặp mua → nhập kho → bán → xuất kho → thu tiền → chi tiền.

### Phase 3: Assets & Costing (6 tuần)

**Mục tiêu**: TSCĐ, CCDC, giá thành.

**Deliverables**:
- [ ] Module `assets`:
  - Fixed asset master
  - Asset category (type/group/subgroup)
  - Asset transaction (increase/decrease/transfer)
  - Depreciation calculation
  - Báo cáo 06-TSCĐ
- [ ] Module CCDC (subset of assets với is_tool=True)
- [ ] Module `costing`:
  - Workshop
  - Product cost period
  - Cost calculation ( giản đơn )
  - Báo cáo giá thành

**Team**: 2 dev

### Phase 4: HR & Payroll (6 tuần)

**Mục tiêu**: Quản lý nhân sự, chấm công, tính lương.

**Deliverables**:
- [ ] Module `hr`:
  - Employee (35+ master data tables)
  - Labor contract
  - Work history
  - Insurance
  - Reward/discipline
- [ ] Module `payroll`:
  - Shift, standard workday, public holiday
  - Attendance (manual + time clock sync)
  - Leave, overtime
  - Payroll calculation (gross → net)
  - BHXH/BHYT/BHTN calculation
  - PIT calculation

**Team**: 2 dev

### Phase 5: Financial & Tax Reports (4 tuần)

**Mục tiêu**: BCTC đầy đủ + thuế GTGT.

**Deliverables**:
- [ ] Module `reporting`:
  - Trial balance (S06-DN)
  - Balance sheet (B01a-DN)
  - P&L (B02a-DN)
  - Cash flow direct (B03a-DN)
  - Cash flow indirect (B03a-DN)
  - PDF export (WeasyPrint)
  - Excel export (openpyxl)
- [ ] Module `tax`:
  - VAT return (01/GTGT)
  - Output VAT listing (01-1/GTGT)
  - Input VAT listing (01-2/GTGT)
  - XML export for e-tax portal

**Team**: 2 dev + 1 kế toán domain expert

### Phase 6: Polish & Go-Live (4 tuần)

**Mục tiêu**: Production-ready.

**Deliverables**:
- [ ] Performance optimization
- [ ] End-to-end testing
- [ ] Documentation (user manual)
- [ ] Training materials
- [ ] Backup strategy
- [ ] Monitoring & alerting
- [ ] Security audit
- [ ] Pilot deployment
- [ ] Bug fixes
- [ ] Production go-live

**Lưu ý**: Phase 6 chỉ triển khai **Modern UI** (mặc định) đầy đủ. Layout packs khác (Classic, Mobile, Portal) ở Phase 7+.

**Team**: full team

### Phase 7: Multi-UI — Classic Layout (2 tháng, sau go-live)

**Mục tiêu**: Thêm layout pack Classic cho user quen MISA/Bravo/SIS cũ.

**Deliverables**:
- [ ] App `apps/ui_classic` với URL namespace riêng `/classic/*`
- [ ] Template directory `templates/classic/`
- [ ] Top navigation đầy đủ, dense grids
- [ ] Layout switcher component
- [ ] User layout preference (per-user, per-company)
- [ ] Cross-layout tests (route consistency)

**Team**: 1-2 dev + 1 kế toán顾问 cho UX

### Phase 8: Multi-UI — Mobile PWA (2-3 tháng)

**Mục tiêu**: Mobile-first PWA cho truy cập nhanh trên điện thoại.

**Deliverables**:
- [ ] App `apps/ui_mobile` với `/mobile/*`
- [ ] Bottom tab navigation
- [ ] PWA (service worker, manifest, offline-first)
- [ ] Touch-optimized forms
- [ ] Push notifications (cho duyệt chứng từ)

**Team**: 2 dev

### Phase 9: Multi-UI — Customer Portal (2 tháng)

**Mục tiêu**: Portal cho khách hàng/nhà cung cấp xem công nợ và hóa đơn.

**Deliverables**:
- [ ] App `apps/ui_portal` với `/portal/*`
- [ ] OTP login cho customer/vendor (không cần account nội bộ)
- [ ] View-only: công nợ, hóa đơn, lịch sử thanh toán
- [ ] Download PDF hóa đơn
- [ ] Online payment integration (VietQR, VNPay)

**Team**: 2 dev

## 3. Resource planning

### 3.1. Team size đề xuất

| Vai trò | Số lượng | Phase nào |
|---------|---------|-----------|
| Tech Lead / Architect | 1 | All phases |
| Senior Backend Dev | 2 | All phases |
| Mid Backend Dev | 2 | Phase 1+ |
| Frontend Dev (HTMX/Templates) | 1 | Phase 1+ |
| QA Engineer | 1 | Phase 1+ |
| DevOps (part-time) | 1 | Phase 0, 6 |
| Domain Expert (Kế toán) | 1 | Phase 5, 6 |
| Project Manager | 1 | All phases |

**Tổng**: 6-10 người trong ~9-10 tháng

### 3.2. Cost estimate (very rough)

| Phase | Person-months | Cost (VND) @ 30M/pm |
|-------|--------------|---------------------|
| 0: Foundation | 8 | 240M |
| 1: GL + Master | 24 | 720M |
| 2: Core BIZ | 24 | 720M |
| 3: Assets | 12 | 360M |
| 4: HR/Payroll | 12 | 360M |
| 5: Reports | 8 | 240M |
| 6: Polish | 16 | 480M |
| **Tổng** | **104 pm** | **~3.1 tỷ VND** |

Plus:
- Infrastructure (~30M/tháng × 10 tháng = 300M)
- Software licenses (~100M)
- Misc (~200M)

**Tổng cộng**: ~3.7 tỷ VND (~150K USD)

## 4. Risk management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Scope creep | Cao | Cao | MVP strict, change request process |
| Dev rời team | Trung bình | Cao | Documentation, knowledge sharing |
| Tech debt tích tụ | Cao | Trung bình | Refactor time trong mỗi phase |
| Performance issues | Trung bình | Cao | Load test early, profiling |
| Domain knowledge thiếu | Cao | Trung bình | Domain expert tư vấn, training |
| Vietnamese accounting regulation change | Thấp | Cao | Theo dõi văn bản mới, update |

## 5. Definition of Done (DoD)

Mỗi feature được coi là done khi:

1. ✅ Code đã review (1+ approver)
2. ✅ Unit tests pass (>80% coverage)
3. ✅ Integration tests pass
4. ✅ Documentation updated (API docs, user manual)
5. ✅ Migration tested on staging
6. ✅ Performance tested (nếu applicable)
7. ✅ Security review (nếu applicable)
8. ✅ Deployed to staging
9. ✅ QA verified
10. ✅ Product owner accepted

## 6. Stakeholders

- **Product Owner**: Đại diện khách hàng / kế toán trưởng
- **Tech Lead**: Quyết định kỹ thuật
- **Scrum Master**: Quản lý Agile process
- **Domain Expert**: Kế toán trưởng tư vấn nghiệp vụ
- **Dev Team**: Triển khai

## 7. Câu hỏi cần trả lời trước khi bắt đầu

1. **Multi-tenant hay single-tenant?** (đề xuất multi-tenant)
2. **Cloud hay on-premise?** (đề xuất cloud + option on-prem)
3. **SaaS hay licensed?** (đề xuất SaaS cho SME)
4. **Mobile app có cần ngay không?** (đề xuất Phase 7+)
5. **Hỗ trợ TT200 ngay từ đầu hay Phase sau?** (đề xuất Phase sau)
6. **Tích hợp HĐĐT ngay hay Phase sau?** (đề xuất Phase 2+, BKAV first)

---

**Tiếp theo**: [02. Tech Stack](./02-tech-stack.md)
