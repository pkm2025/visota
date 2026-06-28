# PMKetoan — Hệ thống tài liệu vận hành

> **Bộ tài liệu vận hành** cho PMKetoan ERP — hướng dẫn sử dụng, quản trị,
> kỹ thuật, và quy trình vận hành thực tế.

## 📚 Mục lục

### 👤 Hướng dẫn sử dụng (User Guide)

Tài liệu cho người dùng cuối — kế toán viên, sales, purchaser, HR, PM.

| # | Tài liệu | Đối tượng |
|---|----------|-----------|
| 00 | [Bắt đầu — đăng nhập, điều hướng, dashboard](user-guide/00-getting-started.md) | Tất cả |
| 01 | [Kế toán tổng hợp — phiếu, sổ cái, kết chuyển](user-guide/01-ledger.md) | Kế toán viên |
| 02 | [Bán hàng & Công nợ phải thu](user-guide/02-sales.md) | Sales, kế toán |
| 03 | [Mua hàng & Công nợ phải trả](user-guide/03-purchasing.md) | Purchaser, kế toán |
| 04 | [Kho & Nhập-xuất-tồn](user-guide/04-inventory.md) | Thủ kho, purchaser |
| 05 | [Tài sản cố định & Khấu hao](user-guide/05-assets.md) | Kế toán TSCĐ |
| 06 | [Nhân sự & Tính lương](user-guide/06-hr-payroll.md) | HR, kế toán lương |
| 07 | [Hợp đồng & Biên bản](user-guide/07-contracts.md) | Sales, pháp chế |
| 08 | [CRM — Lead/Opportunity/Ticket](user-guide/08-crm.md) | Sales, marketing |
| 09 | [Quản lý dự án](user-guide/09-projects.md) | Project Manager |
| 10 | [Hóa đơn điện tử (TT78/2021)](user-guide/10-einvoice.md) | Kế toán, sales |
| 11 | [Phê duyệt & Workflow](user-guide/11-approvals.md) | Kế toán trưởng |
| 12 | [Ngân hàng & Đối soát](user-guide/12-banking.md) | Kế toán quỹ |
| 13 | [Bảo lãnh & Vay vốn](user-guide/13-guarantees-loans.md) | Kế toán, tài chính |
| 14 | [Đấu thầu (Luật 23/2023)](user-guide/14-bidding.md) | Sales, mối thầu |
| 15 | [Ngân sách & Dòng tiền](user-guide/15-budget.md) | CFO, kế toán trưởng |
| 16 | [Định giá ngoại tệ](user-guide/16-fx.md) | Kế toán |
| 17 | [Thông báo & Email](user-guide/17-notifications.md) | Tất cả |

### 🔧 Hướng dẫn quản trị (Admin Guide)

| # | Tài liệu | Đối tượng |
|---|----------|-----------|
| A1 | [Người dùng, vai trò, phân quyền](admin-guide/01-users-roles.md) | Superuser |
| A2 | [Quản lý công ty (multi-tenant)](admin-guide/02-companies.md) | Superuser |
| A3 | [Danh mục hệ thống (HTTK, sản phẩm, đơn vị)](admin-guide/03-master-data.md) | Admin |
| A4 | [Cấu hình thuế & TT133](admin-guide/04-tax-config.md) | Kế toán trưởng |
| A5 | [Backup & Restore](admin-guide/05-backup-restore.md) | Sysadmin |
| A6 | [Email & SMTP config](admin-guide/06-email.md) | Sysadmin |

### 🛠 Kiến trúc kỹ thuật (Technical)

| # | Tài liệu | Đối tượng |
|---|----------|-----------|
| T1 | [Tổng quan kiến trúc](technical/01-architecture.md) | Developer, Architect |
| T2 | [Tech stack & dependencies](technical/02-tech-stack.md) | Developer |
| T3 | [Mô hình dữ liệu & ERD](technical/03-data-model.md) | Developer, DBA |
| T4 | [REST API](technical/04-api.md) | Developer, Integrator |
| T5 | [Bảo mật & phân quyền](technical/05-security.md) | Architect, Security |
| T6 | [Deployment & DevOps](technical/06-deployment.md) | DevOps, Sysadmin |
| T7 | [Testing](technical/07-testing.md) | QA, Developer |

### 📋 Runbook (Quy trình vận hành)

| # | Tài liệu | Tần suất |
|---|----------|-----------|
| R1 | [Chốt sổ cuối tháng](runbook/01-monthly-close.md) | Hàng tháng |
| R2 | [Chốt sổ cuối năm & BCTC](runbook/02-yearly-close.md) | Hàng năm |
| R3 | [Kê khai & nộp thuế GTGT](runbook/03-vat-filing.md) | Hàng tháng |
| R4 | [Kê khai & nộp thuế TNCN](runbook/04-pit-filing.md) | Hàng tháng |
| R5 | [Quy trình phát hành HĐĐT](runbook/05-einvoice-flow.md) | Hàng ngày |
| R6 | [Tính lương & nộp BHXH](runbook/06-payroll-bhxh-flow.md) | Hàng tháng |
| R7 | [Khôi phục sự cố](runbook/07-troubleshooting.md) | Khi cần |
| R8 | [Deploy lên VPS AlmaLinux 10](runbook/deploy-vps.md) | Lần đầu + khi đổi server |

### 🔄 Workflow nghiệp vụ

| # | Tài liệu | Phạm vi |
|---|----------|---------|
| W1 | [Procure-to-Pay (P2P) — mua đến trả](workflows/01-procure-to-pay.md) | End-to-end |
| W2 | [Order-to-Cash (O2C) — đặt đến thu](workflows/02-order-to-cash.md) | End-to-end |
| W3 | [Lead-to-Project — lead đến dự án](workflows/03-lead-to-project.md) | CRM → Project |
| W4 | [Record-to-Report (R2R) — bút toán đến BCTC](workflows/04-record-to-report.md) | End-to-end |

## 🚀 Bắt đầu nhanh

**Lần đầu dùng**:
1. Đọc [00-getting-started](user-guide/00-getting-started.md)
2. Quản trị: [A1-users-roles](admin-guide/01-users-roles.md)
3. Cấu hình: [A4-tax-config](admin-guide/04-tax-config.md)

**Vận hành hàng tháng**:
- [R1-monthly-close](runbook/01-monthly-close.md)
- [R3-vat-filing](runbook/03-vat-filing.md)

**Lập trình/tích hợp**:
- [T4-api](technical/04-api.md)
- [T3-data-model](technical/03-data-model.md)

## ℹ️ Thông tin hệ thống

| Hạng mục | Giá trị |
|---|---|
| **Phiên bản** | v3.0.0 |
| **Stack** | Django 5.2 LTS + django-ninja + HTMX 2.x + Alpine 3.x + MariaDB 11.4 |
| **Apps** | 31 Django apps |
| **Module permissions** | 25 |
| **System roles** | 8 |
| **URL endpoints** | ~120 |
| **Tests** | 359 passing |
| **Tuân thủ pháp lý** | TT133/2016, TT200/2014, TT78/2021, Luật Kế toán 2015, Luật Đấu thầu 23/2023 |
