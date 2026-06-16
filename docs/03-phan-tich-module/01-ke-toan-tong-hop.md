# 01. Module Kế toán tổng hợp (General Ledger)

> Trục chính của toàn hệ thống. Mọi nghiệp vụ kế toán đều quy về tạo chứng từ + bút toán trên các tài khoản.

## 1. Mục đích nghiệp vụ

- Ghi nhận các nghiệp vụ kế toán phát sinh trong kỳ thông qua **phiếu kế toán** (vouchers)
- Cung cấp **hai hình thức ghi sổ**:
  - **Nhật ký chung** (mặc định, theo TT133 sample S03a-DN/DNN)
  - **Chứng từ ghi sổ** (cổ điển, theo TT133 sample S02a-DN/DNN)
- Thực hiện **kết chuyển cuối kỳ** (close-the-books): kết chuyển 5, 6, 7, 8, 9 → 911
- Khóa số liệu theo kỳ (lock-down)
- Cung cấp **số dư đầu kỳ** (opening balances) để bắt đầu dùng phần mềm từ một thời điểm bất kỳ
- **Chuyển số dư sang năm sau** (year-end carry-forward)

## 2. Phân tích UI quan sát được

### 2.1. Màn hình danh sách Phiếu kế toán

URL: `/glctpk1/wg_ct_01`

**Cấu trúc**:
- Toolbar: Xem, Thêm mới, Sửa, In, Xóa, Tìm kiếm, Nhập từ tệp, Xuất tệp
- Search box: full-text trên tất cả cột
- Grid master-detail:
  - **Grid trên** (voucher list) — 17 cột:
    1. Ngày c.từ (Voucher date)
    2. Số c.từ (Voucher number)
    3. Tổng ps n.tệ (Total foreign currency amount)
    4. Diễn giải chung (Common description)
    5. Mã n.tệ (Currency code)
    6. Tỷ giá (Exchange rate)
    7. Tổng ps VND (Total VND amount)
    8. Ngày lập c.từ (Voucher created date)
    9. Quyển c.từ (Voucher book / number series)
    10. Trạng thái (Status)
    11. Mã ĐVCS (Entity code)
    12. Ngày sửa / Giờ sửa / Người sửa (audit)
    13. Ngày tạo / Giờ tạo / Người tạo (audit)
  - **Grid dưới** (voucher lines) — 8 cột:
    1. Tk (Account)
    2. Mã khách (Customer/object code)
    3. Tên khách (Customer/object name)
    4. Ps nợ n.tệ (Debit foreign)
    5. Ps có n.tệ (Credit foreign)
    6. Diễn giải chi tiết (Line description)
    7. Ps nợ VND (Debit VND)
    8. Ps có VND (Credit VND)

### 2.2. Màn hình tạo/sửa Phiếu kế toán

**Các trường header**:
- Ngày sổ cái (General ledger posting date)
- Ngày lập ct (Voucher creation date)
- Trạng thái (Status — mặc định "2 - Ghi vào sổ cái")
- Mã sổ (Book code)
- Số chứng từ (Voucher number)
- Tỷ giá (Exchange rate — mặc định 1)
- Diễn giải (Description)
- Sửa tiền (Allow amount editing — checkbox)
- Mã n.tệ (Currency — mặc định VND)

**Grid detail** (các bút toán):
Mỗi dòng là một bút toán có: Tk, Mã khách (đối tượng), Ps nợ, Ps có, Diễn giải. Hệ thống tự cân đối nợ = có.

### 2.3. Sổ sách và báo cáo

| Tên | Mẫu TT133/TT200 | Loại |
|-----|----------------|------|
| Nhật ký chung | S03a-DN, DNN | Sổ tổng hợp |
| Sổ chi tiết tài khoản | S38-DN, S19-DNN | Sổ chi tiết |
| Sổ tổng hợp chữ T | – | Sổ phân tích |
| Sổ nhật ký thu tiền | S03a1-DN, DNN | Sổ phụ |
| Sổ nhật ký chi tiền | S03a2-DN, DNN | Sổ phụ |
| Sổ nhật ký bán hàng | S03a4-DN, DNN | Sổ phụ |
| Sổ nhật ký mua hàng | S03a3-DN, DNN | Sổ phụ |
| Sổ cái của một tài khoản | S03b-DN, DNN | Sổ cái |

Với hình thức CTGS:
| Tên | Mẫu |
|-----|-----|
| Khai báo chứng từ ghi sổ | – |
| Đăng ký chứng từ ghi sổ | – |
| Kiểm tra chứng từ ghi sổ | – |
| Bảng kê c.từ gốc cùng loại theo cột | S04-H |
| Chứng từ ghi sổ | S02a-DN, DNN |
| Sổ đăng ký chứng từ ghi sổ | S02b-DN, DNN |
| Sổ cái của một tài khoản | S02c1-DN, DNN |

## 3. Quy trình nghiệp vụ chính

### 3.1. Quy trình ghi sổ kế toán (Nhật ký chung)

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────────┐
│ Phát sinh    │ →  │ Lập phiếu       │ →  │ Kiểm tra     │ →  │ Ghi sổ cái   │
│ nghiệp vụ    │    | kế toán (voucher)|   | (cân đối N=C)|    | (Trạng thái=2)|
└──────────────┘    └─────────────────┘    └──────────────┘    └──────────────┘
                                                ↓                      ↓
                                          ┌────────────────────────────┐
                                          │ Cập nhật sổ quỹ, sổ cái,   │
                                          │ sổ chi tiết tk, công nợ   │
                                          └────────────────────────────┘
```

**Trạng thái chứng từ**:
- `0` — Lưu tạm (Draft, không ghi sổ)
- `1` — Đã ghi sổ phụ (Posted to subsidiary ledger only)
- `2` — Ghi vào sổ cái (Posted to general ledger — mặc định)
- `3` — Đã khóa (Locked, không sửa được)

### 3.2. Quy trình kết chuyển cuối kỳ

```
1. Khai báo kết chuyển (template):
   - TK doanh thu (511) → TK 911 (XĐKQ)
   - TK chi phí (632, 635, 641, 642, 811) → TK 911
   - TK 911 → TK 821 (TNDN) - nếu lãi
   - TK 821 → TK 911 - nếu lỗ

2. Kết chuyển cuối kỳ (execute):
   - Tính tổng phát sinh theo template
   - Tạo phiếu kế toán kết chuyển
   - Trạng thái = 2

3. Phân bổ cuối kỳ:
   - Phân bổ chi phí chờ phân bổ (142, 242)
   - Phân bổ theo bp, dự án, sản phẩm

4. Khóa số liệu:
   - Khóa tháng/quý/năm
   - Không cho sửa chứng từ trong kỳ đã khóa
```

### 3.3. Quy trình số dư đầu kỳ & chuyển năm

```
┌─────────────────────────────┐
│ Năm tài chính 2025          │
│  - Chứng từ thường xuyên    │
│  - Cuối năm: kết chuyển     │
│  - Khóa năm                 │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────────────┐
│ Chuyển số dư sang năm 2026         │
│  - Số dư đầu của các tài khoản     │
│    (BS accounts: 1, 2, 3, 4)       │
│  - Số dư khách hàng, hoá đơn       │
│  - Số dư tồn kho, TSCĐ, CCDC       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────┐
│ Năm tài chính 2026          │
│  - Số dư đầu được fill      │
│  - Chứng từ năm 2026...     │
└─────────────────────────────┘
```

## 4. Entity & relationship

```
┌────────────────────┐        ┌──────────────────────┐
│ AccountingVoucher  │ 1    * │ VoucherLine          │
│ (Phiếu kế toán)    │───────│ (Bút toán)           │
│ - voucher_no       │        │ - account            │
│ - voucher_date     │        │ - object_code        │
│ - book_code        │        │ - debit_fc           │
│ - currency         │        │ - credit_fc          │
│ - exchange_rate    │        │ - debit_vnd          │
│ - description      │        │ - credit_vnd         │
│ - status           │        │ - description        │
│ - posting_date     │        └──────────────────────┘
│ - period (month)   │
│ - fiscal_year      │
└────────────────────┘
```

### 4.1. Đặc tả bảng

**`accounting_voucher` (Chứng từ kế toán)**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | Auto-increment |
| company_id | BIGINT FK | Multi-tenant |
| fiscal_year | SMALLINT | 2026 |
| period | TINYINT | 1-12 |
| voucher_no | VARCHAR(50) | Số c.từ |
| voucher_date | DATE | Ngày c.từ |
| posting_date | DATE | Ngày sổ cái |
| book_code | VARCHAR(20) | Quyển c.từ |
| currency_code | CHAR(3) | Mã n.tệ |
| exchange_rate | DECIMAL(18,6) | Tỷ giá |
| total_fc | DECIMAL(20,4) | Tổng ps n.tệ |
| total_vnd | DECIMAL(20,4) | Tổng ps VND |
| description | TEXT | Diễn giải chung |
| status | TINYINT | 0/1/2/3 |
| source | VARCHAR(20) | 'manual', 'closing', 'depreciation', ... |
| voucher_type | VARCHAR(30) | 'journal', 'cash_receipt', 'sales_invoice', ... |
| created_at, created_by, updated_at, updated_by | audit | |

**`voucher_line` (Bút toán)**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| voucher_id | BIGINT FK | |
| line_no | INT | Số thứ tự dòng |
| account_code | VARCHAR(20) | Tk |
| object_type | ENUM | 'customer', 'vendor', 'employee', 'bank', 'other' |
| object_code | VARCHAR(50) | Mã khách/đối tượng |
| object_name | VARCHAR(255) | Tên khách (denormalized) |
| debit_fc | DECIMAL(20,4) | Ps nợ n.tệ |
| credit_fc | DECIMAL(20,4) | Ps có n.tệ |
| debit_vnd | DECIMAL(20,4) | Ps nợ VND |
| credit_vnd | DECIMAL(20,4) | Ps có VND |
| description | TEXT | Diễn giải chi tiết |
| cost_center_id | BIGINT FK | Bộ phận hạch toán |
| project_code | VARCHAR(50) | Mã dự án |
| contract_code | VARCHAR(50) | Mã hợp đồng |
| production_order_code | VARCHAR(50) | Mã cd sx |

**`closing_template` (Khai báo kết chuyển cuối kỳ)**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id, fiscal_year | | |
| name | VARCHAR(255) | "KC doanh thu", "KC chi phí"... |
| sequence | INT | Thứ tự thực hiện |
| credit_account_pattern | VARCHAR(100) | "511%" |
| debit_account | VARCHAR(20) | "911" |
| is_active | BOOL | |

**`account_opening_balance` (Số dư đầu của tài khoản)**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id, fiscal_year | | |
| account_code | VARCHAR(20) | |
| object_code | VARCHAR(50) | nullable, cho tk chi tiết |
| debit_opening | DECIMAL(20,4) | Nợ đầu kỳ |
| credit_opening | DECIMAL(20,4) | Có đầu kỳ |
| foreign_debit | DECIMAL(20,4) | |
| foreign_credit | DECIMAL(20,4) | |

## 5. Use cases chính

### UC-01: Lập phiếu kế toán thủ công

**Actor**: Kế toán viên
**Pre**: Đã có chart of accounts, fiscal year mở

1. Click "Thêm mới" trên màn Phiếu kế toán
2. Hệ thống điền mặc định:
   - Ngày sổ cái = Ngày lập = hôm nay
   - Trạng thái = "2 - Ghi vào sổ cái"
   - Mã n.tệ = VND, Tỷ giá = 1
3. Người dùng nhập:
   - Số chứng từ (hoặc auto)
   - Diễn giải chung
   - Tỷ giá (nếu ngoại tệ)
4. Thêm các dòng bút toán:
   - Chọn Tk
   - Chọn Mã khách (nếu tk có chi tiết)
   - Nhập Ps nợ hoặc Ps có
5. Hệ thống kiểm tra N = C (cho phép lưu tạm nếu lệch nhỏ)
6. Lưu → tạo `accounting_voucher` + N dòng `voucher_line`
7. Nếu status=2 → cập nhật `account_balance` (sổ cái) và `subsidiary_ledger` (sổ chi tiết)

**Validation rules**:
- Ngày lập c.từ nằm trong fiscal year đang mở
- Tk phải tồn tại trong `chart_of_accounts` và có `is_active=true`
- Nếu tk yêu cầu object_code (ví dụ 131), thì object_code phải tồn tại trong `customer`/`vendor`/...
- N = C (sai số < 1 VND)
- Không cho xóa voucher đã ở status=3 (locked)

### UC-02: Kết chuyển cuối kỳ tự động

**Actor**: Kế toán trưởng
**Pre**: Đã khóa số liệu các tháng trước

1. Mở "Khai báo kết chuyển cuối kỳ" → xem template
2. Mở "Kết chuyển cuối kỳ" → chọn kỳ (tháng/quý/năm)
3. Hệ thống đọc template, tính tổng phát sinh theo pattern
4. Sinh ra phiếu kế toán kết chuyển với source='closing'
5. Mở "Phân bổ cuối kỳ" → chọn các khoản chờ phân bổ (142, 242)
6. Hệ thống tạo phiếu kế toán phân bổ
7. Mở "Khóa số liệu" → chọn kỳ → khóa

### UC-03: Chuyển số dư sang năm sau

**Actor**: Kế toán trưởng (cuối năm)

1. Mở "Chuyển số dư tài khoản sang năm sau"
2. Chọn năm nguồn → năm đích (2025 → 2026)
3. Hệ thống kiểm tra:
   - Năm nguồn đã khóa (status=3)
   - Năm đích chưa có chứng từ (hoặc đã reset)
4. Copy:
   - `account_opening_balance` năm nguồn (cuối kỳ) → năm đích (đầu kỳ)
   - Số dư công nợ khách/NCC → năm đích
   - Số dư hoá đơn chưa thanh toán → năm đích
   - TSCĐ, CCDC, tồn kho → năm đích
5. Lưu lại log `year_end_carry_forward`

## 6. Phân quyền

| Quyền | Mô tả |
|------|------|
| `gl.voucher.view` | Xem danh sách voucher |
| `gl.voucher.create` | Tạo mới |
| `gl.voucher.edit` | Sửa (chỉ khi status=0 hoặc 1) |
| `gl.voucher.delete` | Xóa (chỉ khi status=0 hoặc 1, không phải chứng từ khóa) |
| `gl.voucher.post` | Đăng sổ (status=2) |
| `gl.voucher.unpost` | Bỏ đăng sổ (status=2→0) |
| `gl.closing.execute` | Kết chuyển cuối kỳ |
| `gl.closing.lock` | Khóa số liệu |
| `gl.year_end.carry_forward` | Chuyển số dư năm |

## 7. Tích hợp với module khác

| Module | Tích hợp |
|--------|---------|
| 2. Vốn bằng tiền | Phiếu thu/chi → sinh voucher với voucher_type='cash_receipt' / 'cash_payment' |
| 3. Bán hàng | Hóa đơn bán hàng → sinh voucher với voucher_type='sales_invoice' |
| 4. Mua hàng | Phiếu nhập mua → sinh voucher type='purchase_invoice' |
| 5. Tồn kho | Phiếu xuất kho → sinh voucher type='stock_issue' |
| 6. TSCĐ | Bút toán khấu hao → voucher type='depreciation' |
| 7. CCDC | Bút toán phân bổ → voucher type='allocation' |
| 8. Giá thành | Bút toán giá thành → voucher type='costing' |
| 10. Lương | Bút toán lương → voucher type='payroll' |
| 11. BCTC | Đọc voucher + balance để sinh B01-DN, B02-DN |
| 12. Thuế | Đọc voucher + hóa đơn để sinh tờ khai GTGT |

## 8. Mở rộng khi tái hiện

SIS không có, nhưng nên thêm:

1. **Reversal voucher**: voucher đảo ngược (để hủy chứng từ đã ghi sổ mà không xóa)
2. **Multi-currency revaluation**: đánh giá lại số dư ngoại tệ cuối kỳ (TK 413)
3. **Allocation by driver**: phân bổ chi phí theo driver động (doanh số, headcount, diện tích...)
4. **Budget vs actual**: so sánh ngân sách vs phát sinh thực tế
5. **Approval workflow**: duyệt nhiều cấp cho voucher lớn
6. **Sub-ledger reconciliation**: đối chiếu sổ cái vs sổ chi tiết cuối ngày

---

**Tiếp theo**: [02. Vốn bằng tiền](./02-von-bang-tien.md)
