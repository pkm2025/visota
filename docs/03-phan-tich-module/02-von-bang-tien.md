# 02. Module Vốn bằng tiền (Treasury)

> Quản lý thu/chi tiền mặt, tiền gửi ngân hàng, tạm ứng, các khoản vay.

## 1. Mục đích nghiệp vụ

- Ghi nhận mọi luồng tiền ra/vào doanh nghiệp
- Hạch toán trên TK 111 (Tiền mặt), 112 (Tiền gửi ngân hàng), 113 (Tiền đang chuyển)
- Quản lý tạm ứng (141) và thanh toán tạm ứng
- Theo dõi khế ước vay (các khoản vay ngân hàng, đối tác)
- Hỗ trợ **đa tiền tệ** với đánh giá tự động theo tỷ giá

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chức năng | TK hạch toán chính | Mô tả |
|-----------|-------------------|------|
| Thu qua ngân hàng | N112 / C131, C511, C311... | Khách thanh toán chuyển khoản |
| Thu tiền mặt | N111 / C131, C511, C515... | Khách trả tiền mặt |
| Chi qua ngân hàng | N331, N156, N641... / C112 | Thanh toán NCC bằng chuyển khoản |
| Chi tiền mặt | N331, N142, N641... / C111 | Chi tiền mặt cho NSB/NCC |
| Thanh toán tạm ứng | N156, N641, N642... / C141 | Thanh toán tạm ứng đã cấp |
| Phân bổ tiền thu cho các HĐ | N131 / C511 (chi tiết HĐ) | Phân bổ 1 khoản thu cho nhiều HĐ |
| Phân bổ tiền trả cho HĐ | N331 (chi tiết HĐ) / C112, C111 | Phân bổ 1 khoản chi cho nhiều HĐ |

### 2.2. Cập nhật số dư

- **Số dư ban đầu của các khế ước** (Loan opening balances) — cho khế ước vay
- **Chuyển số dư khế ước sang năm sau** — carry-forward

### 2.3. Báo cáo tiền

| Báo cáo | Mẫu TT133/TT200 | Mục đích |
|---------|----------------|---------|
| Sổ quỹ tiền mặt | S07-DN, S04a-DNN | Sổ quỹ kế toán tổng hợp |
| Sổ kế toán chi tiết quỹ tiền mặt | S07a-DN, S04b-DNN | Sổ quỹ chi tiết theo NT |
| Sổ tiền gửi ngân hàng | S08-DN, S05-DNN | Sổ TGNH |

### 2.4. Danh mục từ điển

| Danh mục | Mô tả | Trường chính |
|----------|------|-------------|
| Danh mục ngoại tệ | USD, EUR, JPY... | currency_code, name, decimal_places |
| Danh mục khế ước vay | Khế ước vay ngân hàng | loan_no, bank_id, principal, interest_rate, start_date, end_date |
| Tài khoản ngân hàng | TK ngân hàng của công ty | bank_id, account_no, currency, gl_account |
| Danh mục tỷ giá | Tỷ giá theo ngày | currency, date, rate |

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình thu tiền mặt

```
┌──────────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────────┐
│ Khách trả    │ →  │ Lập phiếu  │ →  │ Duyệt (nếu  │ →  │ Ghi sổ quỹ  │
│ tiền mặt    │    │ thu TM    │    | cần)        │    │ + sổ cái    │
└──────────────┘    └────────────┘    └──────────────┘    └──────────────┘
                           ↓
                    ┌─────────────────────┐
                    │ Sinh voucher:       │
                    │ N111 / C131 (công nợ)│
                    │ hoặc N111 / C511 (doanh thu)│
                    └─────────────────────┘
```

### 3.2. Quy trình tạm ứng

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Cấp tạm ứng  │ →  │ NV thanh toán    │ →  │ Hoàn trả phần  │
│ N141 / C111  │    | chứng từ, hóa đơn│    | dư: N111/C141  │
│              │    │                  │    | Hoặc bổ sung:  │
│              │    │                  │    | N642/C141      │
└──────────────┘    └──────────────────┘    └─────────────────┘
```

### 3.3. Quy trình khế ước vay

```
1. Khai báo khế ước vay:
   - Số khế ước, ngân hàng, số tiền, lãi suất, kỳ hạn
   
2. Giải ngân:
   N112 / C311 (vay ngắn hạn) hoặc C341 (vay dài hạn)
   
3. Trả lãi định kỳ:
   N635 / C111 hoặc C112
   
4. Trả gốc:
   N311 hoặc N341 / C112
```

## 4. Entity relationship

```
┌─────────────────┐       ┌─────────────────┐
│ BankAccount     │ 1   * │ BankTransaction │
│ (TK ngân hàng)  │──────│ (Giao dịch bank) │
└─────────────────┘       └─────────────────┘
        │
        │
┌───────┴────────┐       ┌──────────────────┐
│ LoanAgreement   │ 1   * │ LoanTransaction │
│ (Khế ước vay)   │──────│ (Giao dịch vay)  │
└─────────────────┘       └──────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ CashVoucher     │ 1   * │ CashVoucherLine │
│ (Phiếu thu/chi) │──────│                 │
└─────────────────┘       └─────────────────┘
        │
        ↓ (post)
┌─────────────────┐
│ AccountingVoucher (GL module) │
└─────────────────┘

┌─────────────────┐
│ AdvancePayment  │
│ (Tạm ứng)       │
└─────────────────┘
        │ 1
        │
        ↓ *
┌─────────────────┐
│ AdvanceSettlement│
│ (Thanh toán TU) │
└─────────────────┘
```

## 5. Đặc tả bảng chính

**`bank_account`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| bank_id | VARCHAR(20) | Techcombank, VCB, BIDV... |
| bank_branch | VARCHAR(255) | |
| account_no | VARCHAR(50) | Số tài khoản |
| account_holder | VARCHAR(255) | Chủ TK |
| currency_code | CHAR(3) | |
| gl_account | VARCHAR(20) | 1121, 1122... |
| is_active | BOOL | |

**`loan_agreement`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| loan_no | VARCHAR(50) | Số khế ước |
| loan_type | ENUM | short_term, long_term |
| lender_type | ENUM | bank, partner, other |
| lender_id | VARCHAR(50) | Bank code hoặc partner code |
| principal | DECIMAL(20,4) | Nguyên gốc |
| currency_code | CHAR(3) | |
| interest_rate | DECIMAL(8,4) | % / năm |
| interest_rate_type | ENUM | fixed, floating |
| disbursement_date | DATE | Ngày giải ngân |
| maturity_date | DATE | Ngày đáo hạn |
| payment_schedule | JSON | Lịch trả nợ |
| status | ENUM | active, closed, overdue |

**`cash_voucher`** (phiếu thu/chi tiền mặt / ngân hàng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| voucher_type | ENUM | cash_receipt, cash_payment, bank_receipt, bank_payment |
| voucher_no | VARCHAR(50) | |
| voucher_date | DATE | |
| amount | DECIMAL(20,4) | Tổng tiền |
| currency_code | CHAR(3) | |
| exchange_rate | DECIMAL(18,6) | |
| amount_vnd | DECIMAL(20,4) | Quy VND |
| payer_payee | VARCHAR(255) | Người nộp/nhận |
| address | VARCHAR(500) | |
| reason | TEXT | Lý do |
| payment_method | ENUM | cash, transfer, check |
| bank_account_id | BIGINT FK | nullable |
| gl_voucher_id | BIGINT FK | Liên kết sang accounting_voucher |
| status | TINYINT | 0/1/2/3 |

**`advance_payment`** (Tạm ứng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| advance_no | VARCHAR(50) | Số tạm ứng |
| advance_date | DATE | |
| employee_id | BIGINT FK | Người được tạm ứng |
| amount | DECIMAL(20,4) | |
| currency_code | CHAR(3) | |
| purpose | TEXT | Mục đích |
| expected_settlement_date | DATE | |
| status | ENUM | open, partial, settled |
| settled_amount | DECIMAL(20,4) | Đã thanh toán |

**`advance_settlement`** (Thanh toán tạm ứng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| advance_id | BIGINT FK | |
| settlement_no | VARCHAR(50) | |
| settlement_date | DATE | |
| invoice_no | VARCHAR(50) | Số hóa đơn |
| invoice_date | DATE | |
| amount | DECIMAL(20,4) | |
| expense_account | VARCHAR(20) | TK chi phí |
| cost_center_id | BIGINT FK | |

## 6. Use cases

### UC-04: Lập phiếu thu tiền mặt

1. Vào Vốn bằng tiền → Cập nhật số liệu → Thu tiền mặt
2. Click "Thêm mới"
3. Nhập:
   - Số phiếu (auto hoặc manual)
   - Ngày lập
   - Người nộp tiền
   - Địa chỉ
   - Lý do
   - Số tiền (n.tệ + tỷ giá → VND)
4. Tab "Hạch toán":
   - Dòng N: TK 111
   - Dòng C: TK 131 (chọn khách hàng) hoặc 511 (doanh thu) hoặc 515...
5. Lưu → sinh voucher sang module Kế toán tổng hợp
6. Cập nhật `cash_book` (sổ quỹ)

### UC-05: Cấp tạm ứng cho nhân viên

1. Vào Vốn bằng tiền → Thanh toán tạm ứng → Thêm mới
2. Chọn NV (employee_id)
3. Nhập số tiền, mục đích, ngày dự kiến thanh toán
4. Hạch toán: N141 / C111
5. Lưu

### UC-06: Thanh toán tạm ứng

1. Vào Vốn bằng tiền → Thanh toán tạm ứng → Thêm thanh toán
2. Chọn tạm ứng cần thanh toán
3. Nhập số hóa đơn, ngày hóa đơn, số tiền, TK chi phí
4. Hạch toán: N642 (chi phí) / C141
5. Nếu số tiền < tạm ứng → hoàn trả: N111/C141
6. Nếu số tiền > tạm ứng → bổ sung thêm: N642/C111

## 7. Báo cáo chi tiết

### Sổ quỹ tiền mặt (S07-DN, S04a-DNN)

```
SỔ QUỸ TIỀN MẶT
Quỹ: ……  Đơn vị: ……
Tháng: 06/2026  Năm: 2026

Ngày | Số CT | Diễn giải | TK ĐƯ | Thu | Chi | Tồn
-----|-------|-----------|-------|-----|-----|----
01/06|       | Tồn đầu   |       |     |     |100.000.000
05/06| PT001 | Khách A trả | 131 | 50.000.000 | | 150.000.000
10/06| PC001 | Trả NCC B | 331 |   | 30.000.000 | 120.000.000
...
     |       | Cộng PS   |       | 50.000.000 | 30.000.000 |
     |       | Tồn cuối   |       |     |     | 120.000.000

Kế toán trưởng  Thủ quỹ  Kế toán
(Ký)             (Ký)     (Ký)
```

### Sổ tiền gửi ngân hàng (S08-DN, S05-DNN)

Tương tự nhưng cho từng TK ngân hàng (1121, 1122, 11211...), có thêm cột chi tiết theo từng TK ngân hàng.

## 8. Validation rules

- Số dư tiền mặt (111) không được âm vào cuối ngày (trừ khi cấu hình cho phép)
- Phiếu thu/chi phải cân đối N = C
- Khế ước vay: ngày giải ngân ≤ ngày đáo hạn
- Tạm ứng: số tiền đã thanh toán ≤ số tiền tạm ứng (cho 1 tạm ứng đơn lẻ)
- Đa tiền tệ: nếu currency_code='VND' thì exchange_rate=1

## 9. Phân quyền

- `cash.voucher.view`, `cash.voucher.create`, `cash.voucher.edit`, `cash.voucher.delete`
- `cash.voucher.approve` (duyệt)
- `cash.advance.view`, `cash.advance.create`, `cash.advance.settle`
- `loan.view`, `loan.create`, `loan.disbursement`, `loan.repayment`
- `bank.transaction.import` (import sao kê ngân hàng)

---

**Tiếp theo**: [03. Bán hàng](./03-ban-hang.md)
