# 01. Tổng quan hệ thống

## 1. Định nghĩa phần mềm

**SIS Accounting Online** là phần mềm kế toán doanh nghiệp dạng SaaS (Software as a Service) do **Công ty Cổ phần S.I.S Việt Nam** phát triển, lưu trữ và cung cấp dịch vụ trên nền web. Sản phẩm phục vụ chủ yếu các **doanh nghiệp nhỏ và vừa (SME) tại Việt Nam**, hoạt động theo **chế độ kế toán Thông tư 133/2016/TT-BTC** (và có thể cấu hình theo Thông tư 200).

Tên nội bộ quan sát được: `SISMACOL2026_TT133_PKM` → `SIS-M-Accounting-Online-năm2026-TT133-đơn vị PKM`.

## 2. Mục tiêu nghiệp vụ

Giải quyết bài toán kế toán toàn diện cho doanh nghiệp vừa và nhỏ:

1. **Ghi sổ kế toán** đầy đủ theo một trong hai hình thức:
   - Hình thức **Nhật ký chung** (mẫu S03a-DN/DNN) – mặc định, phổ biến
   - Hình thức **Chứng từ ghi sổ** (mẫu S02a-DN/DNN) – cổ điển, ít dùng
2. **Phục vụ các nghiệp vụ chuyên ngành**: vốn bằng tiền, bán hàng, mua hàng, tồn kho, TSCĐ, CCDC, chi phí/giá thành, nhân sự, tiền lương
3. **Báo cáo thuế**: tờ khai 01/GTGT theo Thông tư 80/2021, bảng kê đầu vào/đầu ra
4. **Báo cáo tài chính (BCTC)**: Bảng cân đối tài khoản, B01-DN (BCTH tài chính), B02-DN (KQKD), B03-DN (dòng tiền trực tiếp & gián tiếp)
5. **Hóa đơn điện tử**: tích hợp khai báo và đồng bộ với BKAV e-invoice (theo Thông tư 78 → đã được thay bằng TT32/2025)

## 3. Cấu trúc tổng thể

Hệ thống được tổ chức theo mô hình **"công ty + góc nhìn" (company + perspective)**. Người dùng đăng nhập vào một công ty cụ thể, sau đó có thể chuyển đổi qua lại giữa các **góc nhìn nghiệp vụ** khác nhau. Mỗi góc nhìn là một "phiên bản menu điều hướng" tùy theo chức năng người dùng muốn thao tác.

### 3.1. Mô hình đa công ty (multi-tenant)

- Một tài khoản người dùng có thể truy cập nhiều công ty
- Mỗi công ty có:
  - Tên, MST, địa chỉ, các tham số riêng
  - Năm tài chính độc lập
  - Hệ thống tài khoản kế toán riêng (mặc định theo TT133 hoặc TT200)
  - Số dư đầu kỳ và dữ liệu nghiệp vụ riêng

### 3.2. Góc nhìn (perspective)

Thanh ngang trên cùng của giao diện chứa một dropdown "Công ty" với 11 góc nhìn:

| # | Góc nhìn | Mô tả | Module ERP tương ứng |
|---|----------|-------|---------------------|
| 1 | **Tổng hợp** | Tổng quan kế toán, voucher kế toán, kết chuyển cuối kỳ, danh mục TK | General Ledger |
| 2 | **Vốn bằng tiền** | Thu/chi tiền mặt, ngân hàng, tạm ứng, khế ước vay | Treasury |
| 3 | **Bán hàng** | Hóa đơn bán hàng/dịch vụ/xuất khẩu, công nợ khách, hóa đơn điện tử | Sales/AR |
| 4 | **Mua hàng** | Phiếu nhập mua, nhập khẩu, công nợ nhà cung cấp | Purchasing/AP |
| 5 | **Tồn kho** | Nhập/xuất/điều chuyển kho, tính giá, thẻ kho | Inventory |
| 6 | **Tài sản cố định** | Tăng/giảm TSCĐ, khấu hao, điều chuyển | Fixed Assets |
| 7 | **Công cụ dụng cụ** | CCDC, phân bổ chi phí, báo cáo kiểm kê | Tools & Supplies |
| 8 | **Chi phí, giá thành** | Giá thành giản đơn, phân xưởng | Costing |
| 9 | **Quản lý nhân sự** | Hồ sơ nhân viên, hợp đồng lao động, công tác | HR |
| 10 | **Tiền lương** | Chấm công, ca làm việc, tăng ca | Payroll |
| 11 | **Hệ thống** | Người dùng, phân quyền, tham số hệ thống | System Admin |

Cùng một nghiệp vụ có thể được xem/nhập từ nhiều góc nhìn khác nhau (ví dụ: phiếu thu có thể truy cập từ "Tổng hợp" lẫn "Vốn bằng tiền"), nhưng dữ liệu ghi nhận là thống nhất.

### 3.3. Cây điều hướng trái (left navigation tree)

Khi chọn một góc nhìn, cây điều hướng trái hiển thị các nhóm chức năng theo cấu trúc 3 cấp:
- **Cấp 1**: nhóm nghiệp vụ lớn (ví dụ: "Cập nhật số liệu", "Báo cáo", "Danh mục từ điển")
- **Cấp 2**: chức năng cụ thể (ví dụ: "Phiếu kế toán", "Hóa đơn bán hàng")
- **Cấp 3**: mục con nếu có (ví dụ: "Số dư ban đầu các phân xưởng")

## 4. Đặc điểm kỹ thuật quan sát được

| Đặc điểm | Quan sát | Hàm ý |
|----------|---------|------|
| **URL pattern** | `/{module}/wg_{workgroup}` hoặc `/{module}/we_{workgroup}` | Routing theo workgroup, mỗi URL tương ứng một screen |
| **Phân trang** | Grid dùng dropdown 25/50/100 | Cần paging server-side |
| **Tìm kiếm** | Filter header ở mỗi cột + search box | Cần API hỗ trợ filter đa trường + full-text search |
| **Trạng thái chứng từ** | Có trường "Trạng thái" (mặc định "2 - Ghi vào sổ cái") | Workflow duyệt chứng từ (draft/posted/locked) |
| **Trạng thái audit** | Mỗi record có: Ngày sửa, Giờ sửa, Người sửa, Ngày tạo, Giờ tạo, Người tạo | Cần audit log + soft delete |
| **Đa tiền tệ** | Có Mã n.tệ, Tỷ giá, Ps nợ n.tệ, Ps có n.tệ, Ps nợ VND, Ps có VND | Cần double-entry song song nguyên tệ & VND |
| **Phân quyền** | Mục "Danh mục quyền chứng từ" trong Hệ thống | Permission theo voucher type |
| **Online reconnection** | Có thông báo "Attempting to reconnect" | Realtime/WebSocket signalR hoặc tương đương |

## 5. Phân loại người dùng

Dựa trên cấu trúc module và phân quyền, có thể xác định các vai trò người dùng chính:

| Vai trò | Truy cập chính | Quyền hạn |
|---------|---------------|----------|
| **Kế toán tổng hợp** | Tổng hợp, Báo cáo tài chính | Toàn quyền ghi sổ & báo cáo |
| **Kế toán công nợ** | Bán hàng, Mua hàng | Quản lý công nợ khách/hàng, hóa đơn |
| **Kế toán kho** | Tồn kho | Nhập/xuất kho, tính giá |
| **Kế toán TSCĐ** | Tài sản cố định, CCDC | Quản lý khấu hao, phân bổ |
| **Kế toán tiền lương** | Nhân sự, Tiền lương | Hồ sơ NV, chấm công, tính lương |
| **Thủ quỹ/Thủ quỹ ngân hàng** | Vốn bằng tiền | Phiếu thu/chi |
| **Kế toán trưởng** | Tất cả | Duyệt chứng từ, khóa số liệu |
| **Giám đốc** | Báo cáo quản trị, BCTC | Xem báo cáo, phân tích |
| **Admin hệ thống** | Hệ thống | Phân quyền, cấu hình |

## 6. Phạm vi tái hiện

Bộ tài liệu này tập trung tái hiện:

✅ **Trong phạm vi**:
- Toàn bộ 11 góc nhìn nghiệp vụ
- Hệ thống tài khoản theo TT133
- 2 hình thức ghi sổ: nhật ký chung + chứng từ ghi sổ
- Báo cáo thuế, BCTC, sổ kế toán chi tiết
- Hóa đơn điện tử (ở mức metadata, không làm partner với BKAV)
- Phân quyền và quản trị hệ thống

❌ **Ngoài phạm vi** (cần làm rõ với chủ đầu tư):
- Mobile app (chỉ tái hiện web responsive)
- Realtime collaboration (SignalR, websockets)
- Báo cáo quản trị đồ họa nâng cao (BI dashboard)
- Tích tích ngân hàng (EBanking API, Vietcombank, BIDV...)
- Khai báo XML hóa đơn điện tử với tổng cục thuế (chỉ làm UI + metadata)
- Migrator dữ liệu từ các phần mềm khác

## 7. Stack công nghệ đề xuất

| Lớp | Công nghệ | Lý do |
|-----|-----------|------|
| **Backend framework** | Django 5.2 LTS | ORM mạnh, admin built-in, mature, LTS |
| **API layer** | django-ninja | Django-native, type-safe, OpenAPI, async-ready |
| **Database** | MariaDB 11.4 LTS | Tương thích MySQL, GA, performant cho kế toán |
| **Frontend interactivity** | HTMX 2.x | SPA-like UX, server-rendered, ít JS |
| **Frontend reactivity** | Alpine.js 3.x | Reactive UI nhỏ gọn, kết hợp tốt với HTMX |
| **CSS framework** | Bootstrap 5.3 + CSS variables | UI nhanh, hỗ trợ multi-theme qua variables |
| **Grid component** | Tabulator | Thay thế DevExpress grid (của SIS) |
| **Task queue** | **django-q2** (broker = Django ORM) | Tính giá, kết chuyển cuối kỳ, xuất Excel/PDF |
| **Cache** | **Django DB cache** (MariaDB) | Cache report, session, rate-limit |
| **Multi-UI** | **Multi-URL layout packs** | `/modern/`, `/classic/`, `/mobile/`, `/portal/` chạy song song |
| **Branding** | Per-tenant CSS variables + logo | Mỗi company có brand riêng |
| **Full-text search** | MariaDB FULLTEXT hoặc Meilisearch | Tìm voucher, đối tượng |
| **PDF generation** | WeasyPrint hoặc ReportLab | Xuất BCTC, tờ khai theo mẫu |
| **Excel generation** | openpyxl | Xuất/import danh mục, chứng từ |
| **Authentication** | django-allauth hoặc django-axes | Login, 2FA, brute-force protection |

## 8. Đa giao diện (Multi-UI) & Đa luồng thao tác (UX Variants)

PMKetoan tách UX thành **3 chiều độc lập**, kết hợp tạo ra nhiều trải nghiệm:

### 8.1. Chiều 1 — Layout Packs (cấu trúc UI)

Nhiều layout packs chạy song song qua URL riêng, mỗi company có brand riêng:

- **Modern UI** (`/modern/*`) — sidebar trái, Bootstrap 5, HTMX (mặc định)
- **Classic UI** (`/classic/*`) — top nav, dense grid, giống MISA/Bravo/SIS cũ
- **Mobile UI** (`/mobile/*`) — PWA, bottom tab, touch-first
- **Portal UI** (`/portal/*`) — Customer/vendor portal (OTP login, xem công nợ)

### 8.2. Chiều 2 — Interaction Styles (cách thao tác)

Cùng operation có nhiều cách thực hiện, tối ưu theo user/tình huống:

- **Guided** — wizard từng bước, tooltip, smart defaults → cho **người mới**
- **Standard** — form đầy đủ với tất cả fields + keyboard shortcuts → cho **kế toán chuyên nghiệp** (mặc định)
- **Quick** — minimal fields, type-ahead, save & new → cho **nhập liệu nhanh**
- **Bulk** — paste Excel, preview, validate → cho **nhập nhiều cùng lúc**

URL riêng cho mỗi style: `/modern/invoices/new/guided/`, `/modern/invoices/new/quick/`, ...

### 8.3. Chiều 3 — Workflows (nguồn dữ liệu)

Nguồn dữ liệu đầu vào cho operation:

- **From-scratch** — nhập tay (mặc định)
- **From-template** — dùng voucher template có sẵn
- **From-photo** — chụp ảnh hóa đơn, OCR auto-fill
- **From-import** — upload Excel/CSV nhiều dòng
- **From-email** — inbox riêng auto-parse attachment PDF
- **From-API** — partner push qua API

### 8.4. Đặc điểm kiến trúc

- **Plugin registry pattern**: thêm UX variant mới = register 1 class, không sửa code hiện tại
- **Shared backend**: cùng models, services, API cho mọi tổ hợp UX
- **View + Template layer khác biệt**: mỗi layout pack × interaction style có template dir riêng
- **Branding per tenant**: mỗi company có logo, primary color, accent color, favicon, custom CSS, custom domain
- **Smart UX defaults**: tự suggest style theo user role (kế toán → Standard, sales → Guided)

Chi tiết:
- [07-mau-giao-dien/05-multi-ui-architecture.md](../07-mau-giao-dien/05-multi-ui-architecture.md) — Layout packs + Branding
- [07-mau-giao-dien/06-ux-variants-architecture.md](../07-mau-giao-dien/06-ux-variants-architecture.md) — Interaction styles + Workflows + Plugin registry

## 9. Điểm khác biệt quan trọng với SIS gốc

| Đặc điểm | SIS | Tái hiện |
|----------|-----|----------|
| Frontend framework | Blazor Server (.NET) | Django templates + HTMX + Alpine |
| Database | Có thể là SQL Server | MariaDB |
| Grid component | DevExpress | Tabulator |
| API | Web Service internal | django-ninja (OpenAPI) |
| Realtime | SignalR | HTMX/SSE (nếu cần) |
| **UI variants** | 1 layout duy nhất | **Đa layout (Modern + Classic + Mobile + Portal)** |
| **Branding** | 1 brand (SIS) | **Per-tenant branding** |

Sự thay đổi này không ảnh hưởng đến nghiệp vụ kế toán mà chỉ ảnh hưởng đến UX/tech-stack. Toàn bộ luồng nghiệp vụ và mô hình dữ liệu sẽ được bảo toàn.

---

**Tiếp theo**: [02. Phân tích người dùng & vai trò](./02-phan-tich-nguoi-dung.md)
