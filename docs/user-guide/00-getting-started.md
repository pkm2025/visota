# 00 — Bắt đầu sử dụng

> Hướng dẫn đăng nhập, điều hướng, các thao tác cơ bản cho mọi user.

## 1. Đăng nhập

### URL truy cập

| Môi trường | URL |
|------------|-----|
| Production | `https://erp.pkm.vn/` |
| Staging | `https://staging.pkm.vn/` |
| Dev nội bộ | `http://pmk-intranet:8903/` |

### Thông tin đăng nhập

Tài khoản do quản trị viên công ty cấp. Mỗi user có:
- **Username** (duy nhất trong hệ thống)
- **Password** (≥ 8 ký tự, có chữ hoa + chữ thường + số)
- **Họ tên đầy đủ** (hiển thị ở góc phải)
- **Avatar** (tùy chọn)

### Quên mật khẩu

Liên hệ quản trị viên qua email `admin@pkm.vn` hoặc Slack `#erp-support`.

### Khóa tài khoản

Sau 5 lần sai liên tiếp, tài khoản bị Axes khóa 30 phút. Liên hệ admin để reset sớm qua:

```bash
python manage.py axes_reset username
```

## 2. Giao diện chính

Sau khi đăng nhập, bạn thấy:

```
┌─────────────────────────────────────────────────────────────┐
│ [☰] [🔍] [PKM Logo]            [🔔 3] [⚙] [👤 username ▾]   │
├──────────┬──────────────────────────────────────────────────┤
│ Trang chủ │                                                  │
│          │                                                  │
│ Cập nhật  │                                                  │
│ số liệu   │              Nội dung chính                       │
│  - Phiếu  │                                                  │
│  - Thu/Chi│                                                  │
│  - Kết CK │                                                  │
│          │                                                  │
│ Nghiệp vụ │                                                  │
│  - KH     │                                                  │
│  - NCC    │                                                  │
│  - Hàng   │                                                  │
│  ...      │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### 2.1 Thanh trên (Topbar)

| Icon | Chức năng |
|------|-----------|
| ☰ | Toggle sidebar trái (ẩn/hiện menu) |
| 🔍 | Tìm kiếm toàn văn (phiếu, hợp đồng, khách hàng...) |
| 🔔 | Thông báo — số đỏ là unread, bấm để xem dropdown |
| ⚙ | Cài đặt cá nhân |
| 👤 | Menu người dùng — xem quyền, đăng xuất |

### 2.2 Sidebar trái

Tổ chức thành các section có thể collapse:
- **Trang chủ** — dashboard KPI
- **Cập nhật số liệu** — kế toán tổng hợp, thu/chi, ngân hàng
- **Nghiệp vụ** — bán/mua/kho/hợp đồng/đấu thầu
- **CRM** — lead/opportunity/ticket
- **Dự án** — quản lý dự án
- **Tài sản** — TSCĐ + khấu hao
- **Nhân sự** — NV + HĐLĐ + BHXH + lương
- **Sổ sách** — nhật ký chung, sổ cái
- **Báo cáo & Thuế** — BCTC + B02 + VAT + HĐĐT + ngân sách + FX
- **Danh mục** — HTTK
- **Hệ thống** — phê duyệt, thông báo, vai trò

> **Lưu ý**: Bạn chỉ thấy các mục mà vai trò của bạn được cấp quyền. Xem
> [quyền của tôi](/modern/me/permissions/) để biết chi tiết.

### 2.3 Sidebar phải (Context panel)

Hiển thị ngữ cảnh liên quan:
- **Bút toán liên quan** — khi đang xem phiếu/hợp đồng
- **Quy định pháp luật** — link đến TT133, Luật KT 2015
- **Thông tin nhanh** — số liệu tóm tắt

Toggle ẩn/hiện bằng nút ☰ bên phải.

## 3. Điều hướng

### Breadcrumb

Mỗi trang có breadcrumb ở đầu cho biết đường dẫn:

```
Trang chủ › Nghiệp vụ › Hợp đồng › HĐSEC001
```

Bấm vào link để đi nhanh.

### Tabs

Khi bạn vào một trang mới, hệ thống tạo tab mới ở trên cùng. Đóng từng tab
bấm `×`. Tab được lưu trong session — F5 sẽ không mất.

### Back

- Nút ← trên trang detail để quay lại list
- Hoặc bấm vào breadcrumb

## 4. Dashboard

Trang chủ mặc định là `/modern/`. Hiển thị:

- **KPI ngày hôm nay**: số chứng từ, công nợ KH, công nợ NCC, tồn kho
- **Chứng từ gần đây**: 10 phiếu mới nhất, bấm để xem detail
- **Thông tin nhanh**: tổng chứng từ, đã ghi sổ, lưu tạm
- **Nút tạo nhanh**: tạo phiếu kế toán mới

## 5. Các thao tác chung

### 5.1 Tạo mới

Mỗi list page có nút **"+ Thêm [entity]"** ở góc phải. Bấm để mở form tạo.

### 5.2 Tìm kiếm

- List page: ô search ở trên cùng — tìm theo số/name
- Toàn hệ thống: ô search ở topbar
- Có thể kết hợp filter (loại, trạng thái, ngày)

### 5.3 Export

Nút **"Xuất Excel"** ở list page — xuất danh sách đang hiển thị (kể cả sau khi
filter).

Một số trang có thêm export DOCX/PDF cho chứng từ.

### 5.4 Phân trang

List lớn có pagination ở cuối. Mặc định 25 dòng/trang, một số trang 50-100.

### 5.5 Upload tệp đính kèm

Hầu hết entity có mục "Tài liệu đính kèm" ở cuối. Drag-drop hoặc bấm
**"Tải lên"**. Hỗ trợ PDF, JPG, PNG, Excel. Max 10 MB/file.

## 6. Phím tắt

| Phím | Chức năng |
|------|-----------|
| `/` | Focus ô search topbar |
| `g` rồi `d` | Về dashboard |
| `g` rồi `v` | Vào voucher list |
| `g` rồi `s` | Vào sales invoice list |
| `?` | Hiện cheat sheet đầy đủ |
| `Esc` | Đóng modal |

## 7. Quyền của tôi

Vào `/modern/me/permissions/` để xem:
- Vai trò hiện tại tại công ty
- Danh sách module được phép truy cập
- Danh sách module bị từ chối (đỏ)

Nếu cần thêm quyền, liên hệ admin.

## 8. Khi truy cập bị từ chối

Nếu vào trang mà bị redirect `/no-access/`:

1. Kiểm tra [quyền của tôi](/modern/me/permissions/) — có module đó không
2. Nếu không có → liên hệ admin cấp quyền
3. Nếu có mà vẫn bị block → bug, báo `#erp-support`

## 9. Thông báo

Click vào 🔔 trên topbar để xem dropdown. Mỗi thông báo có:
- Loại (info/success/warning/approval)
- Tiêu đề + mô tả
- Link đến entity liên quan

Đọc tất cả: `/notifications/`. Đánh dấu đã đọc bằng nút tương ứng.

## 10. Đăng xuất

Menu người dùng (👤) → **Đăng xuất**. Hệ thống tự lưu trạng thái tab.

---

Tài liệu liên quan:
- [01-ledger](01-ledger.md) — Phiếu kế toán & sổ cái
- [A1-users-roles](../admin-guide/01-users-roles.md) — Quản trị user/role
