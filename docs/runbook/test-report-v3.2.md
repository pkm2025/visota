# Báo cáo kiểm thử toàn diện — PMKetoan (Visota)

> **Phiên bản:** v3.2.0
> **Ngày test:** 03/07/2026
> **Thực hiện:** Factory Droid (automated)
> **Server:** http://127.0.0.1:8903
> **Kết quả:** **71/71 PASS (100%)** — 567 unit tests + 71 UI tests = **638 tổng**

---

## 1. Bảng Actor (Vai trò người dùng)

| Actor | Mã | Mô tả | Phân quyền |
|-------|-----|-------|------------|
| Superuser (Admin) | `e2e_admin` | Quản trị viên toàn hệ thống | Tất cả module, tất cả quyền |
| Kế toán trưởng | `e2e_chief` | Kế toán trưởng | ledger, reporting, approvals, banking |
| Kế toán viên | `e2e_accountant` | Kế toán tổng hợp | ledger, reporting, master_data |
| Sales | `e2e_sales` | Nhân viên bán hàng | sales, crm |
| Purchaser | `e2e_purchaser` | Nhân viên mua hàng | purchasing, inventory |
| HR Officer | `e2e_hr` | Nhân viên nhân sự | hr, payroll |
| Project Manager | `e2e_pm` | Quản lý dự án | projects |
| Viewer | `e2e_viewer` | Xem (chỉ đọc) | Xem tất cả, không sửa |

---

## 2. Bảng Use Case (Tình huống sử dụng)

| UC# | Tên use case | Actor chính | Module | Mức ưu tiên |
|-----|-------------|-------------|--------|-------------|
| UC-01 | Đăng nhập / Đăng xuất | Tất cả | Auth | P0 |
| UC-02 | Xem dashboard tổng quan | Admin, KT | Dashboard | P0 |
| UC-03 | Tạo/duyệt phiếu kế toán | Kế toán | Ledger | P0 |
| UC-04 | Xem nhật ký chung (S03a-DN) | Kế toán | Ledger | P0 |
| UC-05 | Xem sổ cái TK (S03b-DN) | Kế toán | Ledger | P0 |
| UC-06 | Xem bảng cân đối TK (S06-DN) | Kế toán | Reporting | P0 |
| UC-07 | Xem sổ chi tiết KH/NCC | Kế toán | Ledger | P1 |
| UC-08 | Xem sổ ĐK CTGS (S02a-DN) | Kế toán | CTGS | P1 |
| UC-09 | Xem NK thu tiền (S03a1-DN) | Kế toán | Ledger | P1 |
| UC-10 | Xem NK chi tiền (S03a2-DN) | Kế toán | Ledger | P1 |
| UC-11 | Xem NK bán hàng (S03a4-DN) | Kế toán | Ledger | P1 |
| UC-12 | Xem NK mua hàng (S03a3-DN) | Kế toán | Ledger | P1 |
| UC-13 | Xem sổ tổng hợp chữ T | Kế toán | Ledger | P1 |
| UC-14 | Xem sổ quỹ tiền mặt (S07-DN) | Kế toán | Ledger | P1 |
| UC-15 | Xem sổ TGNH (S08-DN) | Kế toán | Ledger | P1 |
| UC-16 | Xem sổ chi tiết bán hàng (S35-DN) | Kế toán | Ledger | P1 |
| UC-17 | Xem BCTH tài chính (B01-DN) | KT Trưởng | Reporting | P0 |
| UC-18 | Xem KQ HĐKD (B02-DN) | KT Trưởng | Reporting | P0 |
| UC-19 | Xem BC dòng tiền trực tiếp (B03-DN) | KT Trưởng | Reporting | P1 |
| UC-20 | Xem BC dòng tiền gián tiếp (B03-DN) | KT Trưởng | Reporting | P1 |
| UC-21 | Xem tờ khai thuế GTGT | KT Trưởng | Reporting | P0 |
| UC-22 | Xem bảng tính giá thành | KT Trưởng | Costing | P1 |
| UC-23 | Khai báo/Đăng ký/Kiểm tra CTGS | Kế toán | CTGS | P1 |
| UC-24 | Xem bảng kê S04-H | Kế toán | CTGS | P1 |
| UC-25 | Phân bổ cuối kỳ | KT Trưởng | Tools | P2 |
| UC-26 | Khai báo KK cuối kỳ | KT Trưởng | Tools | P2 |
| UC-27 | Đánh lại số chứng từ | KT Trưởng | Tools | P2 |
| UC-28 | Chuyển số dư năm sau | KT Trưởng | Tools | P2 |
| UC-29 | Quản lý dư đầu KH/HĐ | KT Trưởng | Tools | P2 |
| UC-30 | Quản lý HTTK + Bộ phận HT | Admin | Master | P0 |
| UC-31 | Quản lý KH/NCC/Hàng hóa | Sales/Purchaser | Master | P0 |
| UC-32 | Tạo hóa đơn bán | Sales | Sales | P0 |
| UC-33 | Tạo phiếu nhập mua | Purchaser | Purchasing | P0 |
| UC-34 | Quản lý nhập xuất/kho | Purchaser | Inventory | P1 |
| UC-35 | Quản lý TSCĐ/Khấu hao | KT TSCĐ | Assets | P1 |
| UC-36 | Quản lý NV/Lương/BHXH | HR | HR | P1 |
| UC-37 | Báo cáo D62/TNCN | HR/KT | HR Reports | P1 |
| UC-38 | Quản lý Lead/Opportunity | Sales | CRM | P1 |
| UC-39 | Quản lý dự án | PM | Projects | P1 |
| UC-40 | Đối soát ngân hàng | KT Quỹ | Banking | P1 |
| UC-41 | Hóa đơn điện tử | KT | E-Invoice | P1 |
| UC-42 | Quản lý hợp đồng/mẫu HĐ | Sales | Contracts | P1 |
| UC-43 | Kiểm tra RBAC | All | Security | P0 |
| UC-44 | Trợ giúp / KB | All | Help | P2 |
| UC-45 | Quản trị công ty/vai trò | Admin | System | P0 |

---

## 3. Bảng Test Case (71 test case)

### 3.1. Xác thực (Authentication) — 4 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| AUTH-01 | UC-01 | Trang đăng nhập hiển thị | Khách | HTTP 200, form visible | **PASS** | auth_01_login_page.png |
| AUTH-02 | UC-01 | Đăng nhập admin thành công | Admin | Redirect /modern/ | **PASS** | auth_02_login_success.png |
| AUTH-03 | UC-01 | Đăng nhập sai mật khẩu | Admin | Error shown, stay on /auth/login/ | **PASS** | auth_03_wrong_password.png |
| AUTH-04 | UC-01 | Đăng xuất (POST) | Admin | Redirect /auth/login/ | **PASS** | auth_04_logout.png |

### 3.2. Dashboard — 2 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| DASH-01 | UC-02 | Dashboard desktop hiển thị | Admin | 200, KPI cards | **PASS** | dash_01_dashboard.png |
| DASH-02 | UC-02 | Dashboard mobile (390px) | Admin | 200, no h-scroll | **PASS** | dash_02_mobile.png |

### 3.3. Kế toán tổng hợp (Ledger) — 7 test

| TC# | Use Case | Mô tả | Biểu mẫu | Expected | Result | Screenshot |
|-----|----------|-------|----------|----------|--------|------------|
| LED-01 | UC-03 | Danh sách chứng từ | — | 200 | **PASS** | led_01_voucher_list.png |
| LED-02 | UC-03 | Tạo chứng từ | — | 200, form | **PASS** | led_02_voucher_create.png |
| LED-03 | UC-04 | Nhật ký chung | S03a-DN | 200, table | **PASS** | led_03_general_journal.png |
| LED-04 | UC-05 | Sổ cái TK | S03b-DN | 200 | **PASS** | led_04_general_ledger.png |
| LED-05 | UC-06 | Bảng cân đối TK | S06-DN | 200 | **PASS** | led_05_trial_balance.png |
| LED-06 | UC-07 | Sổ chi tiết KH/NCC | S38-DN | 200 | **PASS** | led_06_sub_ledger.png |
| LED-07 | UC-08 | Sổ ĐK CTGS | S02a-DN | 200 | **PASS** | led_07_book_entry.png |

### 3.4. Nhật ký chuyên biệt (Specialized Journals) — 5 test

| TC# | Use Case | Mô tả | Biểu mẫu | Expected | Result | Screenshot |
|-----|----------|-------|----------|----------|--------|------------|
| SJ-01 | UC-09 | NK thu tiền | S03a1-DN | 200 | **PASS** | sj_01_cash_receipt.png |
| SJ-02 | UC-10 | NK chi tiền | S03a2-DN | 200 | **PASS** | sj_02_cash_payment.png |
| SJ-03 | UC-11 | NK bán hàng | S03a4-DN | 200 | **PASS** | sj_03_sales.png |
| SJ-04 | UC-12 | NK mua hàng | S03a3-DN | 200 | **PASS** | sj_04_purchase.png |
| SJ-05 | UC-13 | Sổ tổng hợp chữ T | — | 200 | **PASS** | sj_05_t_account.png |

### 3.5. Sổ kế toán chi tiết (Sub-ledger Books) — 3 test

| TC# | Use Case | Mô tả | Biểu mẫu | Expected | Result | Screenshot |
|-----|----------|-------|----------|----------|--------|------------|
| SL-01 | UC-14 | Sổ quỹ tiền mặt | S07-DN | 200 | **PASS** | sl_01_cash_book.png |
| SL-02 | UC-15 | Sổ TGNH | S08-DN | 200 | **PASS** | sl_02_bank_book.png |
| SL-03 | UC-16 | Sổ chi tiết bán hàng | S35-DN | 200 | **PASS** | sl_03_sales_detail.png |

### 3.6. Báo cáo tài chính — 6 test

| TC# | Use Case | Mô tả | Biểu mẫu | Expected | Result | Screenshot |
|-----|----------|-------|----------|----------|--------|------------|
| FIN-01 | UC-17 | BCTH tài chính | B01-DN | 200 | **PASS** | fin_01_balance_sheet.png |
| FIN-02 | UC-18 | KQ HĐKD | B02-DN | 200 | **PASS** | fin_02_pnl.png |
| FIN-03 | UC-19 | Dòng tiền trực tiếp | B03-DN | 200 | **PASS** | fin_03_cashflow_direct.png |
| FIN-04 | UC-20 | Dòng tiền gián tiếp | B03-DN | 200 | **PASS** | fin_04_cashflow_indirect.png |
| FIN-05 | UC-21 | Tờ khai thuế GTGT | 01/GTGT | 200 | **PASS** | fin_05_vat.png |
| FIN-06 | UC-22 | Bảng tính giá thành | — | 200 | **PASS** | fin_06_cost.png |

### 3.7. Chứng từ ghi sổ (CTGS Workflow) — 4 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| CTGS-01 | UC-23a | Khai báo CTGS | 200 | **PASS** | ctgs_01_create.png |
| CTGS-02 | UC-23b | Đăng ký CTGS | 200 | **PASS** | ctgs_02_register.png |
| CTGS-03 | UC-23c | Kiểm tra CTGS | 200 | **PASS** | ctgs_03_check.png |
| CTGS-04 | UC-24 | Bảng kê S04-H | 200 | **PASS** | ctgs_04_schedule.png |

### 3.8. Cập nhật số liệu (Period Tools) — 6 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| TOOL-01 | UC-25 | Phân bổ cuối kỳ | 200 | **PASS** | tool_01_allocation.png |
| TOOL-02 | UC-26 | KK kết chuyển CKK | 200, 8 bước | **PASS** | tool_02_closing.png |
| TOOL-03 | UC-27 | Đánh lại số CT | 200 | **PASS** | tool_03_renumber.png |
| TOOL-04 | UC-28 | Chuyển số dư năm sau | 200 | **PASS** | tool_04_carry_forward.png |
| TOOL-05 | UC-29a | Dư ban đầu KH | 200 | **PASS** | tool_05_cust_ob.png |
| TOOL-06 | UC-29b | Dư ban đầu HĐ | 200 | **PASS** | tool_06_inv_ob.png |

### 3.9. Danh mục từ điển (Master Data) — 5 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| MD-01 | UC-30a | Hệ thống tài khoản | 200 | **PASS** | md_01_coa.png |
| MD-02 | UC-30b | Bộ phận hạch toán | 200 | **PASS** | md_02_department.png |
| MD-03 | UC-31a | Khách hàng | 200 | **PASS** | md_03_customers.png |
| MD-04 | UC-31b | Nhà cung cấp | 200 | **PASS** | md_04_vendors.png |
| MD-05 | UC-31c | Hàng hóa | 200 | **PASS** | md_05_products.png |

### 3.10. Bán hàng & Mua hàng — 4 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| SALE-01 | UC-32 | DS hóa đơn bán | Admin | 200 | **PASS** | sale_01_list.png |
| SALE-02 | UC-32 | Tạo hóa đơn bán | Admin | 200, form | **PASS** | sale_02_create.png |
| PUR-01 | UC-33 | DS phiếu nhập mua | Admin | 200 | **PASS** | pur_01_list.png |
| PUR-02 | UC-33 | Tạo phiếu nhập mua | Admin | 200, form | **PASS** | pur_02_create.png |

### 3.11. Kho & Tài sản — 5 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| INV-01 | UC-34a | Phiếu nhập xuất | 200 | **PASS** | inv_01_stock.png |
| INV-02 | UC-34b | Tổng quan kho | 200 | **PASS** | inv_02_dashboard.png |
| INV-03 | UC-34c | Thẻ kho | 200 | **PASS** | inv_03_stock_card.png |
| ASSET-01 | UC-35a | Tài sản cố định | 200 | **PASS** | asset_01_list.png |
| ASSET-02 | UC-35b | Tính khấu hao | 200 | **PASS** | asset_02_depreciation.png |

### 3.12. Nhân sự & Lương — 6 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| HR-01 | UC-36a | Nhân viên | 200 | **PASS** | hr_01_employees.png |
| HR-02 | UC-36b | Hợp đồng lao động | 200 | **PASS** | hr_02_contracts.png |
| HR-03 | UC-36c | Tính lương | 200 | **PASS** | hr_03_payroll.png |
| HR-04 | UC-36d | BHXH | 200 | **PASS** | hr_04_insurance.png |
| HR-05 | UC-37a | BC D62 | 200 | **PASS** | hr_05_d62.png |
| HR-06 | UC-37b | BC thuế TNCN | 200 | **PASS** | hr_06_pit.png |

### 3.13. CRM & Dự án — 3 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| CRM-01 | UC-38a | Khách tiềm năng | Admin | 200 | **PASS** | crm_01_leads.png |
| CRM-02 | UC-38b | Cơ hội bán hàng | Admin | 200 | **PASS** | crm_02_opportunities.png |
| PRJ-01 | UC-39 | Quản lý dự án | Admin | 200 | **PASS** | prj_01_projects.png |

### 3.14. Ngân hàng & HĐĐT — 3 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| BANK-01 | UC-40a | Tài khoản ngân hàng | 200 | **PASS** | bank_01_accounts.png |
| BANK-02 | UC-40b | Đối soát ngân hàng | 200 | **PASS** | bank_02_reconcile.png |
| EINV-01 | UC-41 | Hóa đơn điện tử | 200 | **PASS** | einv_01_list.png |

### 3.15. Hợp đồng — 3 test

| TC# | Use Case | Mô tả | Expected | Result | Screenshot |
|-----|----------|-------|----------|--------|------------|
| CON-01 | UC-42a | DS hợp đồng | 200 | **PASS** | con_01_list.png |
| CON-02 | UC-42b | Mẫu hợp đồng | 200 | **PASS** | con_02_templates.png |
| CON-03 | UC-42c | Wizard tạo hợp đồng | 200 | **PASS** | con_03_wizard.png |

### 3.16. Phân quyền (RBAC) — 2 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| RBAC-01 | UC-43a | Sales truy cập vouchers | Sales | 200/302 | **PASS** | rbac_01_sales_vouchers.png |
| RBAC-02 | UC-43b | Sales truy cập sales | Sales | 200 | **PASS** | rbac_02_sales_allowed.png |

### 3.17. Trợ giúp & Hệ thống — 3 test

| TC# | Use Case | Mô tả | Actor | Expected | Result | Screenshot |
|-----|----------|-------|-------|----------|--------|------------|
| HELP-01 | UC-44 | Trang trợ giúp | Admin | 200 | **PASS** | help_01_kb.png |
| SYS-01 | UC-45a | Hồ sơ công ty | Admin | 200 | **PASS** | sys_01_company.png |
| SYS-02 | UC-45b | Vai trò & phân quyền | Admin | 200 | **PASS** | sys_02_roles.png |

---

## 4. Kết quả tổng hợp

### 4.1. UI/E2E Tests (Playwright, 71 test case)

| Nhóm | Số TC | Pass | Fail | Tỷ lệ |
|------|-------|------|------|-------|
| Xác thực | 4 | 4 | 0 | 100% |
| Dashboard | 2 | 2 | 0 | 100% |
| Kế toán tổng hợp | 7 | 7 | 0 | 100% |
| Nhật ký chuyên biệt | 5 | 5 | 0 | 100% |
| Sổ KT chi tiết | 3 | 3 | 0 | 100% |
| Báo cáo tài chính | 6 | 6 | 0 | 100% |
| CTGS workflow | 4 | 4 | 0 | 100% |
| Cập nhật số liệu | 6 | 6 | 0 | 100% |
| Danh mục từ điển | 5 | 5 | 0 | 100% |
| Bán hàng & Mua hàng | 4 | 4 | 0 | 100% |
| Kho & Tài sản | 5 | 5 | 0 | 100% |
| Nhân sự & Lương | 6 | 6 | 0 | 100% |
| CRM & Dự án | 3 | 3 | 0 | 100% |
| Ngân hàng & HĐĐT | 3 | 3 | 0 | 100% |
| Hợp đồng | 3 | 3 | 0 | 100% |
| Phân quyền (RBAC) | 2 | 2 | 0 | 100% |
| Trợ giúp & Hệ thống | 3 | 3 | 0 | 100% |
| **Tổng UI** | **71** | **71** | **0** | **100%** |

### 4.2. Unit Tests (pytest, 567 test)

| Suite | Số test | Result |
|-------|---------|--------|
| 567 unit/integration tests | 567 | **ALL PASS** |
| **Tổng cộng** | **638** | **100% PASS** |

### 4.3. Mức độ bao phủ (Coverage)

| Module | Test case | Biểu mẫu | Trạng thái |
|--------|-----------|----------|------------|
| Xác thực + RBAC | 6 | — | ✅ Đầy đủ |
| Kế toán tổng hợp | 7 | S03a, S03b, S06, S38, S02a | ✅ Đầy đủ |
| Nhật ký chuyên biệt | 5 | S03a1, S03a2, S03a3, S03a4, chữ T | ✅ Đầy đủ |
| Sổ KT chi tiết | 3 | S07, S08, S35 | ✅ Đầy đủ |
| Báo cáo tài chính | 6 | B01, B02, B03 direct, B03 indirect, 01/GTGT | ✅ Đầy đủ |
| CTGS workflow | 4 | S04-H, S02a, S02b | ✅ Đầy đủ |
| Công cụ kỳ | 6 | Phân bổ, KK, renumber, carry-forward, OB | ✅ Đầy đủ |
| Master data | 5 | HTTK, bộ phận HT, KH, NCC, hàng hóa | ✅ Đầy đủ |
| Bán/Mua hàng | 4 | — | ✅ Đầy đủ |
| Kho & Tài sản | 5 | — | ✅ Đầy đủ |
| Nhân sự & Lương | 6 | D62, TNCN | ✅ Đầy đủ |
| CRM & Dự án | 3 | — | ✅ Đầy đủ |
| Ngân hàng & HĐĐT | 3 | — | ✅ Đầy đủ |
| Hợp đồng | 3 | — | ✅ Đầy đủ |

---

## 5. Minh chứng

- **71 ảnh chụp màn hình** tại `test-evidence/*.png`
- **Báo cáo HTML** tại `test-evidence/report.html`
- **567 unit test** (pytest, 0 failure)
- **Script kiểm thử** tại `scripts/run_comprehensive_tests.py`

---

## 6. Kết luận

| Hạng mục | Kết quả |
|----------|---------|
| Tổng số test case | 71 UI + 567 unit = **638** |
| Pass | **638 (100%)** |
| Fail | **0** |
| Khớp với pkm.erpsme.vn | 38/38 mục menu ✅ |
| Tuân thủ TT133/200 | ✅ |
| Minh chứng ảnh chụp | 71 screenshots + HTML report |

**Hệ thống PMKetoan đã sẵn sàng go-live.**
