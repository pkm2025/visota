# 03. Module Bán hàng (Sales)

> Quản lý hóa đơn bán hàng/dịch vụ/xuất khẩu, công nợ khách hàng, hóa đơn điện tử.

## 1. Mục đích nghiệp vụ

- Lập hóa đơn bán hàng (hàng hóa), dịch vụ, xuất khẩu
- Theo dõi công nợ khách hàng (TK 131)
- Tạo và đồng bộ hóa đơn điện tử (HĐĐT) với BKAV
- Tính số dư tức thời của khách hàng (real-time AR balance)
- Cung cấp dữ liệu cho tờ khai thuế GTGT đầu ra (mẫu 01-1/GTGT)

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chứng từ | Mô tả |
|----------|------|
| Hóa đơn bán hàng | Bán hàng hóa (TK 156, 157 → 632) |
| Hóa đơn bán dịch vụ | Cung cấp dịch vụ (TK 511) |
| Hóa đơn xuất khẩu | Xuất khẩu (TK 511, không có thuế GTGT đầu ra nếu xuất khẩu) |
| Tính số dư tức thời của khách hàng | Real-time customer balance query |

### 2.2. Báo cáo bán hàng

| Báo cáo | Mô tả |
|---------|------|
| Sổ chi tiết công nợ của một khách hàng | AR aging theo khách |
| Bảng cân đối phát sinh công nợ của một tài khoản | Trial balance cho 131 |
| Sổ chi tiết bán hàng (S35-DN, S17-DNN) | Sales journal |
| Bảng số dư công nợ (đầu kỳ/cuối kỳ) | AR balance snapshot |
| Báo cáo tổng hợp bán hàng | Sales summary |

### 2.3. Báo cáo công nợ

| Báo cáo | Mô tả |
|---------|------|
| Sổ chi tiết t/t của khách hàng (S31-DN, S12-DNN) | Settlement details |

### 2.4. Hóa đơn điện tử

| Chức năng | Mô tả |
|----------|------|
| Khai báo hóa đơn điện tử BKAV | Cấu hình kết nối BKAV |
| Cập nhật số hóa đơn | Đồng bộ số HĐĐT từ BKAV |

### 2.5. Danh mục từ điển

| Danh mục | Trường chính |
|----------|-------------|
| Khách hàng | code, name, tax_code, address, phone, payment_terms, credit_limit |
| Nhóm khách hàng | group_code, name, parent_group_id |
| Giá bán | product_id, customer_group_id, price, effective_date, currency |
| Nhân viên bán hàng | code, name, commission_rate |
| Thuế suất GTGT bán ra | tax_code, rate (0%, 5%, 8%, 10%), tax_type |
| Nhóm thuế suất GTGT đầu ra | group_code, default_rate |

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình bán hàng chuẩn

```
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ Đơn hàng   │→ │ Xuất kho   │→ │ Lập hóa đơn│→ │ Ghi nhận  │→ │ Thu tiền  │
│ (order)    │  │ (5.x)      │  │ bán hàng  │  | DT (511)  │  | (2.x)     │
└────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘
                                     ↓                ↓
                              ┌────────────┐  ┌────────────┐
                              | HĐĐT BKAV  │  | Công nợ   │
                              | (TT78/TT32)│  | (131)     │
                              └────────────┘  └────────────┘
```

### 3.2. Hạch toán chuẩn cho hóa đơn bán hàng

```
Bán hàng hóa cho khách, giá chưa VAT 100tr, VAT 10%, giá vốn 70tr:

(1) Ghi nhận doanh thu:
    N131 (công nợ KH)     : 110.000.000
    C5111 (DT bán hàng)   : 100.000.000
    C33311 (VAT output)   :  10.000.000

(2) Ghi nhận giá vốn:
    N632 (giá vốn)        :  70.000.000
    C156 (hàng hóa)       :  70.000.000
```

### 3.3. Quy trình thu tiền và phân bổ

Khi một khoản thu được phân bổ cho nhiều hóa đơn:

```
1. Khách thanh toán 50tr cho 3 hóa đơn
2. Lập phiếu thu: N111/C131 = 50tr
3. Phân bổ tiền thu cho các HĐ:
   - HĐ 001: 20tr
   - HĐ 002: 15tr
   - HĐ 003: 15tr
4. Mỗi HĐ được cập nhật paid_amount
```

## 4. Entity relationship

```
┌──────────────┐    ┌────────────────────┐
│ Customer     │ 1 *│ SalesInvoice       │
└──────────────┘───┐│ (Hóa đơn bán hàng) │
       ↑          │└────────────────────┘
       │          │         │ 1
       │          │         ↓ *
┌──────┴──────┐   │  ┌─────────────────┐
│CustomerGroup│   │  │SalesInvoiceLine │
└─────────────┘   │  └─────────────────┘
                  │
                  │  ┌─────────────────┐
                  └─→│ InvoicePayment  │
                     │ (Thanh toán)    │
                     └─────────────────┘

┌──────────────┐       ┌──────────────────┐
│EInvoiceConfig│ 1   * │ EInvoice         │
│ (BKAV config)│──────│ (HĐĐT bản)       │
└──────────────┘       └──────────────────┘
                              ↓ 1
                       ┌──────────────────────┐
                       │SalesInvoice          │
                       │ (mapping sang hệ thống)│
                       └──────────────────────┘

┌──────────────┐       ┌──────────────────┐
│ SalesStaff   │ 1   * │ Commission       │
└──────────────┘──────│ (Hoa hồng)       │
                       └──────────────────┘
```

## 5. Đặc tả bảng chính

**`customer`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| code | VARCHAR(50) | Mã khách |
| name | VARCHAR(255) | Tên |
| name_en | VARCHAR(255) | |
| tax_code | VARCHAR(20) | MST |
| address | TEXT | Địa chỉ |
| phone | VARCHAR(50) | |
| email | VARCHAR(255) | |
| customer_group_id | BIGINT FK | |
| sales_staff_id | BIGINT FK | NV bán hàng phụ trách |
| payment_terms | VARCHAR(100) | Điều khoản thanh toán |
| credit_limit | DECIMAL(20,4) | Hạn mức tín dụng |
| currency_code | CHAR(3) | NT mặc định |
| default_tax_rate | DECIMAL(6,4) | |
| gl_account_receivable | VARCHAR(20) | TK 131xxxx |
| is_active | BOOL | |

**`sales_invoice`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| invoice_no | VARCHAR(50) | Số hóa đơn |
| invoice_date | DATE | |
| invoice_type | ENUM | goods, service, export, other |
| customer_id | BIGINT FK | |
| sales_staff_id | BIGINT FK | |
| contract_no | VARCHAR(50) | Số HĐ |
| delivery_note_no | VARCHAR(50) | Số phiếu xuất kho |
| currency_code | CHAR(3) | |
| exchange_rate | DECIMAL(18,6) | |
| subtotal | DECIMAL(20,4) | Tổng trước VAT |
| vat_amount | DECIMAL(20,4) | VAT |
| total_amount | DECIMAL(20,4) | Tổng cộng VAT |
| total_vnd | DECIMAL(20,4) | Quy VND |
| payment_status | ENUM | unpaid, partial, paid |
| paid_amount | DECIMAL(20,4) | Đã thanh toán |
| einvoice_id | BIGINT FK | Liên kết HĐĐT |
| gl_voucher_id | BIGINT FK | Voucher kế toán |
| status | TINYINT | 0/1/2/3 |

**`sales_invoice_line`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| invoice_id | BIGINT FK | |
| line_no | INT | |
| product_id | BIGINT FK | Hàng hóa/dịch vụ |
| description | TEXT | |
| quantity | DECIMAL(18,4) | |
| unit_id | VARCHAR(20) | Đơn vị tính |
| unit_price | DECIMAL(20,4) | Đơn giá |
| discount_rate | DECIMAL(6,4) | % chiết khấu |
| discount_amount | DECIMAL(20,4) | |
| amount_before_vat | DECIMAL(20,4) | |
| vat_rate | DECIMAL(6,4) | 0/5/8/10% |
| vat_amount | DECIMAL(20,4) | |
| amount | DECIMAL(20,4) | Sau VAT |
| cost_account | VARCHAR(20) | N632 |
| revenue_account | VARCHAR(20) | C5111 |
| inventory_account | VARCHAR(20) | C156 |

**`einvoice`** (Hóa đơn điện tử):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| einvoice_no | VARCHAR(50) | Số HĐĐT |
| serial_no | VARCHAR(20) | Ký hiệu (AA/24E...) |
| template_code | VARCHAR(20) | Mã mẫu |
| issue_date | DATETIME | Ngày phát hành |
| buyer_name | VARCHAR(255) | |
| buyer_tax_code | VARCHAR(20) | |
| amount | DECIMAL(20,4) | |
| vat_amount | DECIMAL(20,4) | |
| total_amount | DECIMAL(20,4) | |
| einvoice_status | ENUM | pending, issued, cancelled, replaced, adjusted |
| provider | ENUM | bkav, viettel, mobifone, etc. |
| xml_data | LONGTEXT | XML raw |
| pdf_url | VARCHAR(500) | |
| related_invoice_id | BIGINT FK | Hóa đơn gốc (nếu thay thế/điều chỉnh) |

**`invoice_payment`** (Thanh toán hóa đơn):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| invoice_id | BIGINT FK | |
| cash_voucher_id | BIGINT FK | Phiếu thu |
| amount | DECIMAL(20,4) | |
| payment_date | DATE | |

## 6. Use cases

### UC-07: Lập hóa đơn bán hàng

1. Vào Bán hàng → Cập nhật số liệu → Hóa đơn bán hàng → Thêm mới
2. Nhập:
   - Số hóa đơn (auto)
   - Ngày hóa đơn
   - Khách hàng (chọn từ danh mục)
   - NV bán hàng
   - Số HĐ, Số phiếu xuất kho (nếu có)
3. Tab "Chi tiết":
   - Chọn hàng hóa/dịch vụ
   - Nhập số lượng, đơn giá
   - Hệ thống tự tính: subtotal, VAT, total
4. Tab "Hạch toán":
   - DT: N131 / C511
   - Giá vốn: N632 / C156
   - VAT: (đã tính cùng DT)
5. Lưu → tạo voucher sang GL
6. (Tùy chọn) Phát hành HĐĐT BKAV → cập nhật einvoice_no

### UC-08: Hóa đơn thay thế / điều chỉnh

Khi cần xuất hóa đơn thay thế hoặc điều chỉnh:

1. Tìm hóa đơn gốc → chọn "Điều chỉnh" hoặc "Thay thế"
2. Nhập lý do, thông tin mới
3. Hệ thống tạo hóa đơn mới với `related_invoice_id` = hóa đơn gốc
4. HĐĐT mới có trạng thái "adjusted" hoặc "replaced"
5. Bút toán đảo hoặc bổ sung tương ứng

### UC-09: Khai báo hóa đơn điện tử BKAV

1. Vào Bán hàng → Hóa đơn điện tử → Khai báo hóa đơn điện tử BKAV
2. Nhập:
   - Mã doanh nghiệp trên BKAV
   - Username, password
   - Ký hiệu mẫu hóa đơn (AA/24E...)
   - Số bắt đầu, số kết thúc
3. Test kết nối
4. Lưu

### UC-10: Tính số dư tức thời của khách hàng

```
Input: customer_code, date
Output:
  - Opening balance (đầu kỳ)
  - Phát sinh tăng (hóa đơn mới)
  - Phát sinh giảm (đã thanh toán)
  - Closing balance (dư nợ hiện tại)
  - Aging (0-30, 31-60, 61-90, >90)
```

## 7. Sổ chi tiết bán hàng (S35-DN, S17-DNN)

```
SỔ CHI TIẾT BÁN HÀNG
TK: 5111   Khách hàng: Tất cả
Tháng: 06/2026

Chứng từ | Diễn giải | TK ĐƯ | Ps nợ | Ps có
---------|-----------|-------|-------|-------
01/06 BC001 | Bán cho KH A | 131 |  | 110.000.000
05/06 BC002 | Bán cho KH B | 131 |  | 55.000.000
...
       Cộng phát sinh      |     |  | 550.000.000
       Dư cuối kỳ          |     |  | 550.000.000
```

## 8. Quy tắc tính thuế GTGT

- **0%**: hàng xuất khẩu, dịch vụ xuất khẩu, vận tải quốc tế, hàng luật định
- **5%**: lương thực, thiết bị y tế, sách, báo, ...
- **8%** (giai đoạn giảm thuế): một số HHDV theo nghị quyết Chính phủ
- **10%**: mặc định
- **Không chịu thuế**: một số nghiệp vụ đặc thù (tiền lãi nội bộ, ...)
- **Hóa đơn xuất khẩu**: VAT=0, nhưng vẫn kê khai vào bảng kê đầu ra

Hệ thống cần bảng `vat_rate` với các trường: rate, effective_date, description, scope.

## 9. Validation rules

- Số lượng hóa đơn > 0
- Đơn giá ≥ 0
- Tổng tiền thanh toán ≤ (total - paid_amount)
- Khách hàng phải có tax_code nếu xuất HĐĐT (trừ trường hợp khách mua lẻ)
- VAT rate phải thuộc {0, 5, 8, 10, -KT (không chịu thuế)}

## 10. Phân quyền

- `sales.invoice.view`, `.create`, `.edit`, `.delete`
- `sales.invoice.post`, `.cancel`
- `sales.einvoice.issue` (phát hành HĐĐT)
- `sales.einvoice.adjust` (điều chỉnh)
- `sales.customer.view`, `.create`, `.edit`
- `sales.report.view` (xem báo cáo)

---

**Tiếp theo**: [04. Mua hàng](./04-mua-hang.md)
