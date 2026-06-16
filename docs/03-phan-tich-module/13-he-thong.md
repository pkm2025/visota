# 13. Module Hệ thống (System Administration)

> Quản trị người dùng, phân quyền, tham số cấu hình, năm tài chính.

## 1. Mục đích nghiệp vụ

- Quản lý **người sử dụng** (users) và phân quyền
- Cấu hình **tham số hệ thống** (system parameters)
- Quản lý **quyển chứng từ** (voucher books / number series)
- Định nghĩa **trạng thái chứng từ** (voucher statuses)
- Thiết lập **năm tài chính** (fiscal year)
- Theo dõi **truy cập của NSD** (audit log)
- Quản lý **đơn vị** (companies / tenants)

## 2. Cấu trúc module

### 2.1. Người dùng

| Chức năng | Mô tả |
|----------|------|
| Người sử dụng | CRUD user |
| Tham số tùy chọn | System configuration |
| Màn hình chứng từ | Định nghĩa voucher screens |
| Danh mục quyền chứng từ | Voucher book / number series |
| Trạng thái chứng từ | Voucher status enum |
| Thống kê truy cập của NSD | Audit log |
| Khai báo năm tài chính | Fiscal year |

### 2.2. Danh mục

- Danh mục đơn vị (companies)

## 3. Người dùng & phân quyền

### 3.1. Mô hình phân quyền 3 lớp

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│ User         │ * *│ Role         │ * *│ Permission       │
└──────────────┘───→│ (Vai trò)    │───→│ (Quyền cụ thể)   │
                    └──────────────┘    └──────────────────┘
```

### 3.2. Quyền theo mô hình ABAC/RBAC kết hợp

Format quyền: `<module>.<entity>.<action>` với scopes:

Ví dụ:
- `gl.voucher.view` — Xem voucher GL
- `gl.voucher.create` — Tạo mới
- `gl.voucher.edit` — Sửa (chỉ status ≤ 1)
- `gl.voucher.delete` — Xóa (chỉ status = 0)
- `gl.voucher.post` — Đăng sổ (status=2)
- `gl.voucher.approve` — Duyệt
- `gl.voucher.lock` — Khóa (status=3)
- `gl.voucher.unlock` — Mở khóa

### 3.3. Cấu trúc user

Mỗi user có:
- Thông tin đăng nhập: username, password, 2FA
- Thông tin cá nhân: full_name, email, phone
- Status: active, locked, suspended
- Roles: list of role_id
- Company access: list of company_id với role cụ thể
- Default company
- Last login, last IP

## 4. Quyển chứng từ (voucher book)

Quản lý **dải số chứng từ** cho từng loại nghiệp vụ:

```
Quyển "Hóa đơn bán hàng - 06/2026":
  - voucher_type: sales_invoice
  - prefix: 'BC'
  - year: 2026
  - month: 6
  - starting_no: 0001
  - ending_no: 9999
  - current_no: 0047
```

Mỗi chứng từ mới được cấp số từ voucher_book tương ứng.

## 5. Trạng thái chứng từ (voucher status)

```
0 - Lưu tạm (draft, không ghi sổ)
1 - Đã ghi sổ phụ (posted to subsidiary ledger)
2 - Đã ghi sổ cái (posted to general ledger) — DEFAULT
3 - Đã khóa (locked, không sửa được)
```

Plus các status nghiệp vụ riêng:
- `cancelled` — Đã hủy
- `reversed` — Đã đảo (reversal voucher)

## 6. Năm tài chính (fiscal year)

```
┌─────────────────────────────────────────┐
│ Năm tài chính 2026                      │
│  - Start: 01/01/2026                    │
│  - End: 31/12/2026                      │
│  - Periods: 12 tháng                    │
│  - Status: open                         │
│  - Locked periods: [1, 2, 3, 4, 5]      │
│  - Carry-forward from: 2025 (closed)    │
└─────────────────────────────────────────┘
```

## 7. Tham số hệ thống

Bảng `system_parameter` lưu các config:

| Param code | Mô tả | Ví dụ |
|-----------|------|------|
| `accounting_regime` | Chế độ kế toán | tt133, tt200 |
| `default_currency` | NT mặc định | VND |
| `fiscal_year_start_month` | Tháng bắt đầu năm TC | 1 |
| `vat_default_rate` | VAT mặc định | 10 |
| `voucher_auto_number` | Tự động đánh số | true |
| `decimal_places` | Số chữ số thập phân | 2 (VND), 4 (foreign) |
| `rounding_mode` | PP làm tròn | half_up, half_even |
| `date_format` | Định dạng ngày | dd-MM-yyyy |
| `negative_red` | Hiển thị âm màu đỏ | true |
| `multi_currency` | Cho phép đa NT | true |
| `allow_negative_stock` | Cho phép tồn âm | false (mặc định) |
| `email_notification` | Email thông báo | true |
| `smtp_server`, `smtp_port`, ... | Email config | |

## 8. Audit log

`user_access_log` ghi lại mọi hoạt động của user:

| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| user_id | BIGINT FK | |
| company_id | BIGINT FK | |
| access_time | DATETIME | |
| ip_address | VARCHAR(50) | |
| user_agent | TEXT | |
| module | VARCHAR(50) | gl, sales, ... |
| entity_type | VARCHAR(50) | voucher, customer, ... |
| entity_id | BIGINT | |
| action | ENUM | view, create, update, delete, post, lock |
| old_values | JSON | |
| new_values | JSON | |
| request_url | VARCHAR(500) | |
| request_method | VARCHAR(10) | GET, POST, PUT, DELETE |

## 9. Đặc tả bảng chính

**`user`** (Người sử dụng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| username | VARCHAR(50) UNIQUE | |
| email | VARCHAR(255) UNIQUE | |
| full_name | VARCHAR(255) | |
| phone | VARCHAR(20) | |
| password_hash | VARCHAR(255) | |
| is_active | BOOL | |
| is_superuser | BOOL | |
| is_staff | BOOL | |
| two_factor_enabled | BOOL | |
| two_factor_secret | VARCHAR(255) | |
| last_login_at | DATETIME | |
| last_login_ip | VARCHAR(50) | |
| failed_login_count | INT | |
| locked_until | DATETIME | |
| created_at, updated_at | audit | |

**`role`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | nullable (global role) |
| code | VARCHAR(50) | admin, accountant, ... |
| name | VARCHAR(255) | |
| description | TEXT | |
| is_system | BOOL | role hệ thống không xóa |

**`permission`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(100) UNIQUE | 'gl.voucher.create' |
| module | VARCHAR(50) | |
| name | VARCHAR(255) | |
| description | TEXT | |

**`role_permission`**:
| Cột | Kiểu | Note |
|-----|------|------|
| role_id | BIGINT FK | |
| permission_id | BIGINT FK | |
| scope_json | JSON | Phạm vi (per company, per department) |

**`user_company_role`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| user_id | BIGINT FK | |
| company_id | BIGINT FK | |
| role_id | BIGINT FK | |
| is_default | BOOL | |
| valid_from | DATE | |
| valid_to | DATE | |

**`voucher_book`** (Danh mục quyền chứng từ):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| voucher_type | VARCHAR(50) | sales_invoice, gl_voucher, ... |
| prefix | VARCHAR(20) | 'BC', 'PT', 'PC' |
| fiscal_year | SMALLINT | |
| period | TINYINT | nullable |
| starting_no | INT | |
| ending_no | INT | |
| current_no | INT | Số tiếp theo |
| is_active | BOOL | |

**`voucher_status`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | TINYINT | 0, 1, 2, 3 |
| name | VARCHAR(100) | 'Draft', 'Posted', 'Locked' |
| description | TEXT | |
| allow_edit | BOOL | |
| allow_delete | BOOL | |

**`fiscal_year`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| fiscal_year | SMALLINT | 2026 |
| start_date | DATE | |
| end_date | DATE | |
| status | ENUM | open, closing, closed |
| locked_periods | JSON | [1, 2, 3, 4, 5] |
| carry_forward_to | SMALLINT | nullable (next year) |

**`system_parameter`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | nullable (global) |
| param_code | VARCHAR(100) | |
| param_value | TEXT | |
| data_type | ENUM | string, int, decimal, bool, json |
| description | TEXT | |

**`company`** (Danh mục đơn vị):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(20) | |
| name | VARCHAR(255) | |
| tax_code | VARCHAR(20) | MST |
| address | TEXT | |
| phone | VARCHAR(20) | |
| email | VARCHAR(255) | |
| legal_representative | VARCHAR(255) | |
| chief_accountant | VARCHAR(255) | |
| accounting_regime | ENUM | tt133, tt200 |
| default_currency | CHAR(3) | VND |
| fiscal_year_start_month | TINYINT | |
| is_active | BOOL | |

## 10. Use cases

### UC-41: Tạo người dùng mới

1. Hệ thống → Người sử dụng → Thêm mới
2. Nhập:
   - Username (unique)
   - Email (unique)
   - Họ tên
   - Mật khẩu (hoặc gửi email reset)
3. Gán role cho từng company:
   - Company A: Kế toán viên
   - Company B: Kế toán trưởng
4. Set default company
5. Lưu → user status='active'

### UC-42: Mở năm tài chính mới

1. Hệ thống → Khai báo năm tài chính → Thêm mới
2. Nhập:
   - Năm: 2026
   - Ngày bắt đầu: 01/01/2026
   - Ngày kết thúc: 31/12/2026
3. Lưu
4. (Cuối năm 2025) Mở "Chuyển số dư" → carry-forward

### UC-43: Cấu hình quyền chứng từ

1. Hệ thống → Danh mục quyền chứng từ → Thêm mới
2. Chọn voucher_type (vd: sales_invoice)
3. Nhập prefix, năm, kỳ, starting_no, ending_no
4. Lưu → hệ thống auto increment current_no khi có chứng từ mới

### UC-44: Khóa kỳ kế toán

1. Hệ thống → Khai báo năm tài chính
2. Edit fiscal year 2026
3. Add period=6 vào `locked_periods`
4. Save → từ giờ không cho sửa chứng từ tháng 6 (trừ khi unlock)

## 11. Validation rules

- Username và email phải unique
- Không xóa được role hệ thống (admin, accountant_default)
- Voucher book: starting_no ≤ current_no ≤ ending_no
- Fiscal year: start_date < end_date, không trùng năm với FY khác cùng company

## 12. Phân quyền

- `system.user.view`, `.create`, `.edit`, `.delete`, `.reset_password`
- `system.role.view`, `.create`, `.edit`, `.assign_permission`
- `system.company.view`, `.create`, `.edit`
- `system.parameter.view`, `.edit`
- `system.fiscal_year.view`, `.create`, `.lock_period`
- `system.voucher_book.view`, `.create`, `.edit`
- `system.audit_log.view`

---

[Tiếp theo: Mô hình dữ liệu →](../04-mo-hinh-du-lieu/01-erd-tong-quan.md)
