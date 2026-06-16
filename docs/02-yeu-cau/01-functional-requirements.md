# 01. Yêu cầu chức năng (Functional Requirements)

> Danh sách yêu cầu chức năng chi tiết theo module.

## Quy ước

| Ký hiệu | Ý nghĩa |
|---------|---------|
| FR-XX-YY | Functional Requirement: Module XX, số YY |
| **Ưu tiên**: P0 = critical, P1 = high, P2 = medium, P3 = low |

## 1. Module Identity & Core

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-CORE-01 | Hệ thống hỗ trợ **multi-tenant**: mỗi tenant là 1 company, dữ liệu cách ly hoàn toàn | P0 |
| FR-CORE-02 | User có thể đăng nhập vào nhiều company, chuyển đổi company bằng dropdown | P0 |
| FR-CORE-03 | Mỗi company có năm tài chính độc lập, có thể khóa kỳ | P0 |
| FR-CORE-04 | Hệ thống phải ghi audit log mọi thao tác create/update/delete | P0 |
| FR-CORE-05 | Soft delete cho entity đã được post | P1 |
| FR-CORE-06 | Hỗ trợ 2 ngôn ngữ: Tiếng Việt (mặc định), Tiếng Anh | P2 |

## 2. Module Identity

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-IDX-01 | Đăng nhập bằng username/email + password | P0 |
| FR-IDX-02 | Hỗ trợ 2FA TOTP | P1 |
| FR-IDX-03 | Password policy: tối thiểu 8 ký tự, có hoa + thường + số | P0 |
| FR-IDX-04 | Lock account sau 5 lần sai liên tiếp, unlock bởi admin | P0 |
| FR-IDX-05 | Quản lý vai trò (role) và phân quyền chi tiết (permission) | P0 |
| FR-IDX-06 | User có thể đổi password, reset password qua email | P0 |
| FR-IDX-07 | Hỗ trợ SSO (Google, Microsoft) | P3 |

## 3. Module Master Data

### 3.1. Hệ thống tài khoản

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-COA-01 | Có sẵn hệ thống tài khoản TT133 (~120 TK) | P0 |
| FR-COA-02 | Có sẵn hệ thống tài khoản TT200 (~300 TK) | P1 |
| FR-COA-03 | Cho phép thêm TK chi tiết cấp 3, 4, 5 | P0 |
| FR-COA-04 | Cho phép đánh dấu "cấp số" (account_level) | P0 |
| FR-COA-05 | Cho phép cấu hình: TK có object_code? cost_center? project? | P0 |
| FR-COA-06 | Hierarchical tree view | P1 |
| FR-COA-07 | Export/import Excel | P1 |

### 3.2. Khách hàng / NCC / Sản phẩm / Kho

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-MD-01 | CRUD customer với: code, name, tax_code, address, payment_terms, credit_limit | P0 |
| FR-MD-02 | CRUD vendor với fields tương tự | P0 |
| FR-MD-03 | CRUD product với: code, name, unit, type, gl_account | P0 |
| FR-MD-04 | CRUD warehouse | P0 |
| FR-MD-05 | Search + filter với pagination | P0 |
| FR-MD-06 | Import/export Excel | P1 |
| FR-MD-07 | Validate MST bằng checksum | P1 |
| FR-MD-08 | Auto-suggest khi nhập (datalist) | P2 |

## 4. Module Ledger (Kế toán tổng hợp)

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-GL-01 | Tạo/sửa/xóa phiếu kế toán (accounting_voucher) với multi-line | P0 |
| FR-GL-02 | Mỗi voucher có status: 0=draft, 1=subsidiary, 2=ledger, 3=locked | P0 |
| FR-GL-03 | Validation: tổng nợ = tổng có (sai số < 1 VND) | P0 |
| FR-GL-04 | Validation: TK phải tồn tại và active | P0 |
| FR-GL-05 | Validation: nếu TK yêu cầu object_code, object_code phải tồn tại | P0 |
| FR-GL-06 | Validation: ngày chứng từ trong fiscal year đang mở | P0 |
| FR-GL-07 | Multi-currency: lưu cả Nợ/Có NT và VND | P0 |
| FR-GL-08 | Auto-number voucher_no theo voucher_book | P0 |
| FR-GL-09 | Tính số dư đầu kỳ (cho TK, khách hàng, hóa đơn) | P0 |
| FR-GL-10 | Post voucher → cập nhật account_period_balance | P0 |
| FR-GL-11 | Unpost voucher → đảo ngược update balance | P0 |
| FR-GL-12 | Khóa kỳ: không cho sửa voucher trong kỳ đã khóa | P0 |
| FR-GL-13 | Định nghĩa template kết chuyển cuối kỳ | P0 |
| FR-GL-14 | Thực thi kết chuyển cuối kỳ tự động | P0 |
| FR-GL-15 | Phân bổ chi phí cuối kỳ (142, 242) | P0 |
| FR-GL-16 | Chuyển số dư năm sang năm sau | P0 |
| FR-GL-17 | Reversal voucher (đảo chứng từ đã ghi sổ) | P1 |
| FR-GL-18 | Tự động đánh lại số chứng từ | P1 |
| FR-GL-19 | Hỗ trợ cả 2 hình thức: Nhật ký chung & Chứng từ ghi sổ | P0 |
| FR-GL-20 | Sổ kế toán: NKC, sổ cái, sổ chi tiết TK (mẫu TT133/TT200) | P0 |

## 5. Module Treasury (Vốn bằng tiền)

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-CASH-01 | Phiếu thu/chi tiền mặt + ngân hàng | P0 |
| FR-CASH-02 | Thanh toán tạm ứng | P0 |
| FR-CASH-03 | Quản lý khế ước vay | P1 |
| FR-CASH-04 | Phân bổ tiền thu/chi cho nhiều hóa đơn/hợp đồng | P1 |
| FR-CASH-05 | Sổ quỹ tiền mặt (S07-DN) | P0 |
| FR-CASH-06 | Sổ TGNH (S08-DN) | P0 |
| FR-CASH-07 | Sổ chi tiết quỹ tiền mặt (S07a-DN) | P0 |
| FR-CASH-08 | Import sao kê ngân hàng | P2 |
| FR-CASH-09 | Multi-currency cho TK ngoại tệ | P1 |

## 6. Module Sales

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-SALE-01 | CRUD hóa đơn bán hàng | P0 |
| FR-SALE-02 | CRUD hóa đơn dịch vụ | P0 |
| FR-SALE-03 | CRUD hóa đơn xuất khẩu | P1 |
| FR-SALE-04 | Hóa đơn có nhiều dòng chi tiết (line items) | P0 |
| FR-SALE-05 | Tự tính subtotal, discount, VAT, total | P0 |
| FR-SALE-06 | Hỗ trợ VAT: 0%, 5%, 8%, 10%, không chịu thuế | P0 |
| FR-SALE-07 | Theo dõi công nợ khách hàng (TK 131) | P0 |
| FR-SALE-08 | Tính số dư tức thời của khách hàng (real-time) | P0 |
| FR-SALE-09 | AR aging (0-30, 31-60, 61-90, >90 ngày) | P1 |
| FR-SALE-10 | Hóa đơn thay thế/điều chỉnh | P1 |
| FR-SALE-11 | Sổ chi tiết bán hàng (S35-DN) | P0 |
| FR-SALE-12 | Sổ chi tiết công nợ KH (S31-DN) | P0 |
| FR-SALE-13 | Tích hợp BKAV eInvoice (phát hành HĐĐT) | P1 |
| FR-SALE-14 | Pull hóa đơn đầu vào từ Tổng cục Thuế | P1 |

## 7. Module Purchasing

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-PUR-01 | CRUD phiếu nhập mua hàng | P0 |
| FR-PUR-02 | CRUD phiếu nhập dịch vụ | P0 |
| FR-PUR-03 | CRUD phiếu nhập khẩu | P1 |
| FR-PUR-04 | CRUD nhập mua xuất thẳng | P2 |
| FR-PUR-05 | Quản lý chi phí mua hàng + phân bổ | P0 |
| FR-PUR-06 | Theo dõi công nợ NCC (TK 331) | P0 |
| FR-PUR-07 | AP aging | P1 |
| FR-PUR-08 | Sổ chi tiết công nợ NCC | P0 |

## 8. Module Inventory

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-INV-01 | Phiếu nhập/xuất/điều chuyển kho | P0 |
| FR-INV-02 | Theo dõi tồn kho theo product + warehouse + lot | P0 |
| FR-INV-03 | 3 phương pháp tính giá: TB tháng, TB di động, FIFO | P0 |
| FR-INV-04 | Tồn kho đầu kỳ + kết chuyển | P0 |
| FR-INV-05 | Thẻ kho (S10-DN) | P0 |
| FR-INV-06 | Báo cáo tổng hợp NXT | P0 |
| FR-INV-07 | Quản lý theo lô + hạn sử dụng | P1 |
| FR-INV-08 | Quy đổi đơn vị tính | P1 |
| FR-INV-09 | Validation: không xuất khi tồn không đủ (trừ TB tháng) | P0 |
| FR-INV-10 | Multi-warehouse | P0 |

## 9. Module Fixed Assets

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-FA-01 | CRUD tài sản cố định | P0 |
| FR-FA-02 | Tăng/giảm/điều chuyển TSCĐ | P0 |
| FR-FA-03 | 3 PP khấu hao: đường thẳng, d balancing, theo sản lượng | P0 |
| FR-FA-04 | Tính khấu hao định kỳ hàng tháng | P0 |
| FR-FA-05 | Phân bổ KH cho nhiều bộ phận sử dụng | P1 |
| FR-FA-06 | Báo cáo 06-TSCĐ | P0 |
| FR-FA-07 | Báo cáo tăng/giảm TSCĐ | P0 |
| FR-FA-08 | CCDC: tương tự TSCĐ nhưng cho TK 142, 242 | P1 |

## 10. Module Costing

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-COST-01 | Quản lý phân xưởng | P1 |
| FR-COST-02 | Tính giá thành giản đơn | P1 |
| FR-COST-03 | Tập hợp chi phí: NLK, NC, SXC | P1 |
| FR-COST-04 | Theo dõi dở dang đầu/cuối kỳ | P1 |
| FR-COST-05 | Hệ số sản phẩm (cho nhiều sp cùng px) | P2 |

## 11. Module HR

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-HR-01 | CRUD hồ sơ nhân viên (~50 fields) | P0 |
| FR-HR-02 | Quản lý quan hệ gia đình, người phụ thuộc | P0 |
| FR-HR-03 | Quản lý hợp đồng thử việc, HĐLĐ, phụ lục | P0 |
| FR-HR-04 | Quá trình công tác | P0 |
| FR-HR-05 | Theo dõi BHXH, BHYT, BHTN | P0 |
| FR-HR-06 | Quản lý khen thưởng, kỷ luật | P0 |
| FR-HR-07 | Nghỉ phép, nghỉ thai sản, nuôi con < 12 tháng | P0 |
| FR-HR-08 | Cấp phát CCDC cho NV | P1 |
| FR-HR-09 | Báo cáo tăng/giảm lao động | P1 |
| FR-HR-10 | ~35 danh mục từ điển HR | P0 |

## 12. Module Payroll

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-PAY-01 | Định nghĩa ca làm việc | P0 |
| FR-PAY-02 | Lịch nghỉ trong năm, ngày công chuẩn | P0 |
| FR-PAY-03 | Chấm công (manual + import từ máy chấm công) | P0 |
| FR-PAY-04 | Đăng ký ca làm việc cho NV | P0 |
| FR-PAY-05 | Quản lý nghỉ phép + định mức | P0 |
| FR-PAY-06 | Đăng ký tăng ca/làm thêm | P0 |
| FR-PAY-07 | Tính lương (gross → net) | P1 |
| FR-PAY-08 | Tính BHXH (24% tổng, 17.5% DN, 10.5% NV) | P1 |
| FR-PAY-09 | Tính thuế TNCN (theo biểu lũy tiến) | P1 |
| FR-PAY-10 | Báo cáo chấm công tổng hợp | P0 |

## 13. Module Financial Reports

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-RPT-01 | Bảng cân đối tài khoản (S06-DN) | P0 |
| FR-RPT-02 | BC tình hình tài chính (B01a-DN) | P0 |
| FR-RPT-03 | BC KQ HĐKD (B02a-DN) | P0 |
| FR-RPT-04 | BC dòng tiền trực tiếp (B03a-DN) | P0 |
| FR-RPT-05 | BC dòng tiền gián tiếp (B03a-DN) | P1 |
| FR-RPT-06 | Thuyết minh BCTC | P1 |
| FR-RPT-07 | Báo cáo quản trị (dashboard) | P2 |
| FR-RPT-08 | Export PDF, Excel | P0 |
| FR-RPT-09 | Drill-down từ report → voucher gốc | P1 |
| FR-RPT-10 | So sánh nhiều kỳ | P1 |

## 14. Module Tax Reports

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-TAX-01 | Tờ khai thuế GTGT 01/GTGT theo TT80 | P0 |
| FR-TAX-02 | Bảng kê đầu ra 01-1/GTGT | P0 |
| FR-TAX-03 | Bảng kê đầu vào 01-2/GTGT | P0 |
| FR-TAX-04 | Tự động tính [22], [29], [40]-[45] | P0 |
| FR-TAX-05 | Xuất XML cho nộp thuế điện tử | P1 |
| FR-TAX-06 | Quản lý số dư VAT chuyển kỳ sau | P0 |
| FR-TAX-07 | Kê khai theo tháng hoặc quý tùy doanh thu | P1 |

## 15. Module System

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-SYS-01 | CRUD user + role + permission | P0 |
| FR-SYS-02 | Cấu hình tham số hệ thống | P0 |
| FR-SYS-03 | Quản lý voucher_book (dải số CT) | P0 |
| FR-SYS-04 | Định nghĩa năm tài chính | P0 |
| FR-SYS-05 | Khóa/mở khóa kỳ | P0 |
| FR-SYS-06 | Audit log viewer | P0 |
| FR-SYS-07 | Backup/restore | P1 |
| FR-SYS-08 | Quản lý trạng thái chứng từ | P1 |

## 16. Cross-cutting Requirements

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-X-01 | Tất cả list view hỗ trợ search + filter + sort + pagination | P0 |
| FR-X-02 | Tất cả form có validation client + server | P0 |
| FR-X-03 | Master-detail grid reusable component | P0 |
| FR-X-04 | Form voucher dynamic lines (add/remove row) | P0 |
| FR-X-05 | HTMX: cập nhật inline, không reload page | P0 |
| FR-X-06 | Toast notifications cho thành công/lỗi | P0 |
| FR-X-07 | Confirmation dialog cho action nguy hiểm (delete, lock) | P0 |
| FR-X-08 | Keyboard shortcuts (Ctrl+S save, Ctrl+N new, ...) | P2 |
| FR-X-09 | Print preview cho mọi chứng từ, sổ, báo cáo | P0 |
| FR-X-10 | Responsive (mobile-friendly cơ bản) | P2 |

## 17. Multi-UI & Branding (Đa giao diện song song)

> Chi tiết: [07-mau-giao-dien/05-multi-ui-architecture.md](../07-mau-giao-dien/05-multi-ui-architecture.md) và [07-mau-giao-dien/06-ux-variants-architecture.md](../07-mau-giao-dien/06-ux-variants-architecture.md)

| ID | Yêu cầu | Ưu tiên |
|----|---------|---------|
| FR-UI-01 | Hệ thống hỗ trợ ≥2 layout packs chạy song song qua URL riêng (`/modern/`, `/classic/`, `/mobile/`) | P0 |
| FR-UI-02 | Mỗi layout pack có URL namespace riêng và Django app riêng (`apps/ui_<layout>/`) | P0 |
| FR-UI-03 | Layout switcher component hiển thị ở mọi page, click để đổi UI | P0 |
| FR-UI-04 | Khi đổi layout, giữ nguyên context nghiệp vụ (cùng voucher, cùng filter) | P1 |
| FR-UI-05 | User có thể đặt preferred layout trong profile (per-user, per-company) | P0 |
| FR-UI-06 | Company có thể đặt default_layout cho user mới của company đó | P0 |
| FR-UI-07 | Mỗi company có brand riêng: logo (light + dark), primary color, accent color, favicon | P0 |
| FR-UI-08 | Hỗ trợ logo light + dark variant (cho sidebar tối) | P1 |
| FR-UI-09 | Hide white-label branding (ẩn "Powered by PMKetoan") — configurable per company | P1 |
| FR-UI-10 | Custom CSS field cho tenant (advanced, có validation) | P2 |
| FR-UI-11 | Custom domain: `accounting.acme.com` auto-trỏ tới ACME company | P2 |
| FR-UI-12 | Permission riêng cho từng layout (`ui.modern.access`, `ui.classic.access`, ...) | P1 |
| FR-UI-13 | Layout packs cùng dùng chung services và models (DRY — View + Template khác, Service + Model giống nhau) | P0 |
| FR-UI-14 | Test cross-layout: mỗi route cốt lõi phải tồn tại trong mọi layout pack | P1 |
| FR-UI-15 | Layout packs Phase 1: Modern (mặc định) + Classic | P0 |
| FR-UI-16 | Layout packs Phase 2+: Mobile (PWA), Customer Portal | P1 |
| FR-UI-17 | Hệ thống phân tách UX thành 3 chiều: Layout × Interaction Style × Workflow | P0 |
| FR-UI-18 | Hỗ trợ ≥3 interaction styles: **Guided** (wizard cho người mới), **Standard** (form đầy đủ), **Quick** (minimal) | P0 |
| FR-UI-19 | Hỗ trợ **Bulk** style: paste Excel, preview, validate, bulk create | P0 |
| FR-UI-20 | Plugin registry cho phép đăng ký UX variant mới mà không sửa core code (`InteractionStyleRegistry`, `WorkflowRegistry`) | P0 |
| FR-UI-21 | Smart UX defaults theo user role (kế toán → Standard, sales → Guided, ...) | P1 |
| FR-UI-22 | UX switcher UI ở top bar cho phép đổi Interaction Style + Workflow nhanh | P0 |
| FR-UI-23 | User preference lưu UX choice (per user, per layout, per operation) | P0 |
| FR-UI-24 | Onboarding flow cho user mới (welcome modal, tour wizard, first-week nudges) | P1 |
| FR-UI-25 | Guided style phải có: progress bar, tooltip, validation inline, smart defaults | P0 |
| FR-UI-26 | Quick style phải có: type-ahead search, Enter-to-next, save & new | P0 |
| FR-UI-27 | From-photo workflow (OCR) cho phép chụp ảnh hóa đơn → auto-fill form | P2 |
| FR-UI-28 | From-import workflow cho phép upload Excel/CSV nhiều dòng | P0 |
| FR-UI-29 | Voucher templates: user lưu + dùng lại được (From-template workflow) | P0 |
| FR-UI-30 | Mỗi operation có URL riêng theo style: `/modern/invoices/new/guided/`, `/modern/invoices/new/quick/` | P0 |
| FR-UI-31 | Test cross-UX: mỗi operation phải work với mọi supported style | P1 |

---

**Tiếp theo**: [02. Yêu cầu phi chức năng](./02-non-functional-requirements.md)
