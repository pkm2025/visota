# 04. Module Mua hàng (Purchasing)

> Phiếu nhập mua hàng hóa/dịch vụ, nhập khẩu, công nợ nhà cung cấp, hóa đơn đầu vào từ Tổng cục Thuế.

## 1. Mục đích nghiệp vụ

- Lập phiếu nhập mua hàng, dịch vụ
- Hạch toán mua hàng trong nước, nhập khẩu
- Theo dõi công nợ nhà cung cấp (TK 331)
- Tính giá vốn hàng mua (bao gồm chi phí mua)
- Thu thập hóa đơn đầu vào từ cổng Tổng cục Thuế (HDDT)
- Cung cấp dữ liệu cho tờ khai thuế GTGT đầu vào (01-2/GTGT)

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chứng từ | TK chính | Mô tả |
|----------|---------|------|
| Phiếu nhập mua hàng | N156, N1331 / C331 | Mua hàng hóa trong nước |
| Phiếu nhập dịch vụ | N641, N642, N241 / C331 | Mua dịch vụ |
| Phiếu nhập khẩu | N156, N1332 / C331, C3333 | Nhập khẩu + thuế NK + thuế TTĐB |
| Nhập mua xuất thẳng | N632 / C331 | Mua về bán ngay, không nhập kho |
| Chi phí mua hàng | N156 (phân bổ) / C111, C112, C331 | Chi phí vận chuyển, bốc dỡ |
| Hóa đơn đầu vào từ TCT | – | Pull hóa đơn từ cổng thuế |

### 2.2. Báo cáo

| Báo cáo | Mô tả |
|---------|------|
| Tổng hợp hàng nhập mua | Purchase summary by vendor/product |
| BCĐPS công nợ của một tài khoản | Trial balance cho 331 |
| Sổ chi tiết công nợ của một nhà cung cấp | AP details |
| Bảng số dư công nợ (đầu kỳ/cuối kỳ) | AP balance snapshot |

### 2.3. Danh mục từ điển

| Danh mục | Trường chính |
|----------|-------------|
| Nhà cung cấp | code, name, tax_code, address, payment_terms, gl_account_payable |
| Nhóm nhà cung cấp | group_code, name |
| Thuế suất GTGT đầu vào | tax_code, rate (0%, 5%, 8%, 10%), tax_type |

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình mua hàng chuẩn

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Yêu cầu mua  │ → │ Đơn hàng    │ → │ Nhận hàng   │ → │ Lập phiếu   │
│ (requisition)│   │ (PO)        │   │ (GR)        │   │ nhập mua    │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                              ↓
                                              ┌──────────────────────────┐
                                              │ Hạch toán:               │
                                              │ N156, N1331 / C331       │
                                              │ + chi phí mua: N156/C112 │
                                              └──────────────────────────┘
                                                              ↓
                                              ┌──────────────────────────┐
                                              │ Thanh toán NCC:          │
                                              │ N331 / C112              │
                                              └──────────────────────────┘
```

### 3.2. Hạch toán các nghiệp vụ đặc biệt

**Mua hàng trong nước có VAT**:
```
N156 (hàng hóa): 100tr
N1331 (VAT deducted): 10tr
C331 (công nợ NCC): 110tr
```

**Nhập khẩu hàng hóa**:
```
N156 (theo trị giá NK tính bằng VND): 200tr
N1332 (VAT NK được khấu trừ): 20tr
C331 (công nợ NCC nước ngoài): 200tr (USD × tỷ giá)
C3333 (Thuế xuất nhập khẩu): 10tr
C3332 (Thuế TTĐB): 5tr (nếu có)
```

**Chi phí mua hàng (phân bổ)**:
```
N156 (chi phí phân bổ cho hàng mua) / C112
```

Phân bổ theo tiêu thức: số lượng, trọng lượng, giá trị.

**Nhập mua xuất thẳng (mua bán ngay không qua kho)**:
```
N632 (giá vốn) / C331
N131 (công nợ KH) / C511 + C33311
```

## 4. Entity relationship

```
┌──────────────┐       ┌────────────────────┐
│ Vendor       │ 1   * │ PurchaseInvoice    │
└──────────────┘───────┤ (Phiếu nhập mua)   │
       ↑                └────────────────────┘
       │                        │ 1
       │                        ↓ *
┌──────┴──────┐                ┌────────────────────┐
│VendorGroup  │                │ PurchaseInvoiceLine│
└─────────────┘                └────────────────────┘

┌──────────────┐       ┌──────────────────┐
│InputInvoice  │       │ PurchaseExpense  │
│(Hóa đơn TCT) │ 1──1→ │ (Chi phí mua)    │
└──────────────┘       └──────────────────┘
```

## 5. Đặc tả bảng chính

**`vendor`** (Nhà cung cấp):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| code | VARCHAR(50) | |
| name | VARCHAR(255) | |
| name_en | VARCHAR(255) | |
| tax_code | VARCHAR(20) | |
| address | TEXT | |
| phone, email | VARCHAR | |
| vendor_group_id | BIGINT FK | |
| payment_terms | VARCHAR(100) | |
| currency_code | CHAR(3) | |
| gl_account_payable | VARCHAR(20) | TK 331xxx |
| is_supplier | BOOL | Cung cấp hàng hóa |
| is_contractor | BOOL | Cung cấp dịch vụ |
| is_active | BOOL | |

**`purchase_invoice`** (Phiếu nhập mua):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| invoice_no | VARCHAR(50) | |
| invoice_date | DATE | |
| invoice_type | ENUM | goods, service, import, direct_issue |
| vendor_id | BIGINT FK | |
| po_no | VARCHAR(50) | Số đơn hàng |
| delivery_note_no | VARCHAR(50) | |
| currency_code | CHAR(3) | |
| exchange_rate | DECIMAL(18,6) | |
| subtotal | DECIMAL(20,4) | |
| vat_amount | DECIMAL(20,4) | |
| import_tax | DECIMAL(20,4) | Thuế NK (nhập khẩu) |
| excise_tax | DECIMAL(20,4) | Thuế TTĐB |
| total_amount | DECIMAL(20,4) | |
| total_vnd | DECIMAL(20,4) | |
| paid_amount | DECIMAL(20,4) | |
| warehouse_id | BIGINT FK | Kho nhập |
| einvoice_id | BIGINT FK | Hóa đơn đầu vào |
| gl_voucher_id | BIGINT FK | |
| status | TINYINT | |

**`purchase_invoice_line`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| invoice_id | BIGINT FK | |
| product_id | BIGINT FK | |
| description | TEXT | |
| quantity | DECIMAL(18,4) | |
| unit_id | VARCHAR(20) | |
| unit_price | DECIMAL(20,4) | |
| discount_rate | DECIMAL(6,4) | |
| discount_amount | DECIMAL(20,4) | |
| amount_before_vat | DECIMAL(20,4) | |
| vat_rate | DECIMAL(6,4) | |
| vat_amount | DECIMAL(20,4) | |
| amount | DECIMAL(20,4) | |
| inventory_account | VARCHAR(20) | N156 |
| vat_account | VARCHAR(20) | N1331 |

**`input_invoice`** (Hóa đơn đầu vào từ TCT):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| buyer_tax_code | VARCHAR(20) | MST của công ty mình |
| seller_tax_code | VARCHAR(20) | MST NSB |
| seller_name | VARCHAR(255) | |
| seller_address | TEXT | |
| invoice_no | VARCHAR(50) | Số HĐ |
| invoice_date | DATE | |
| template_code | VARCHAR(20) | Mẫu |
| serial_no | VARCHAR(20) | Ký hiệu |
| amount | DECIMAL(20,4) | |
| vat_rate | DECIMAL(6,4) | |
| vat_amount | DECIMAL(20,4) | |
| total_amount | DECIMAL(20,4) | |
| purchase_invoice_id | BIGINT FK | Match với phiếu nhập (nếu đã kê khai) |
| import_status | ENUM | pending, matched, excluded |
| xml_data | LONGTEXT | XML từ TCT |

**`purchase_expense`** (Chi phí mua hàng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| purchase_invoice_id | BIGINT FK | |
| expense_type | ENUM | freight, insurance, customs_fee, loading, other |
| amount | DECIMAL(20,4) | |
| currency_code | CHAR(3) | |
| allocation_method | ENUM | by_value, by_quantity, by_weight |
| gl_account | VARCHAR(20) | |

## 6. Use cases

### UC-11: Lập phiếu nhập mua hàng trong nước

1. Mua hàng → Cập nhật số liệu → Phiếu nhập mua hàng
2. Thêm mới:
   - Số phiếu, ngày
   - Nhà cung cấp
   - Kho nhập
3. Tab "Chi tiết":
   - Chọn hàng hóa, số lượng, đơn giá
   - Tự tính subtotal, VAT
4. Tab "Chi phí mua hàng" (optional):
   - Thêm chi phí vận chuyển, bốc dỡ
5. Tab "Hạch toán":
   - N156 / C331 (cho hàng)
   - N1331 / C331 (cho VAT)
   - N156 / C112 (cho chi phí mua, tự phân bổ)
6. Lưu → sinh voucher sang GL → cập nhật tồn kho (sang module Tồn kho)

### UC-12: Lập phiếu nhập khẩu

1. Mua hàng → Cập nhật số liệu → Phiếu nhập khẩu
2. Khác so với mua trong nước:
   - Có thêm các trường: tờ khai hải quan, số container, v.v.
   - Phải tính VAT NK, thuế NK, thuế TTĐB
   - Phải quy đổi ngoại tệ → VND theo tỷ giá
3. Hạch toán: N156, N1332 / C331, C3333, C3332

### UC-13: Pull hóa đơn từ Tổng cục Thuế

Tích hợp với API HDDT của Tổng cục Thuế để lấy danh sách hóa đơn đầu vào:

1. Vào Mua hàng → Hóa đơn đầu vào từ TCT
2. Chọn kỳ (tháng/quý)
3. Hệ thống gọi API TCT → trả về list hóa đơn
4. Người dùng xem từng hóa đơn:
   - Match với phiếu nhập (nếu đã nhập trước)
   - Hoặc tạo phiếu nhập mới từ hóa đơn
   - Hoặc đánh dấu "loại trừ" (không dùng)
5. Lưu vào `input_invoice`

### UC-14: Phân bổ chi phí mua hàng

1. Vào Mua hàng → Chi phí mua hàng
2. Chọn phiếu nhập mua cần phân bổ
3. Nhập chi phí + phương pháp phân bổ (by_value / by_quantity / by_weight)
4. Hệ thống tự phân bổ cho từng dòng hàng
5. Sinh bút toán: N156 / C112 (hoặc C331)

## 7. Sổ chi tiết công nợ NCC (S31-DN tương đương)

```
SỔ CHI TIẾT CÔNG NỢ NHÀ CUNG CẤP
TK: 331   NCC: Công ty ABC
Kỳ: 06/2026

Chứng từ | Diễn giải | TK ĐƯ | Ps nợ | Ps có
---------|-----------|-------|-------|-------
01/06 PN001 | Mua hàng | 156 | | 110.000.000
05/06 PT005 | Thanh toán | 112 | 110.000.000 |
...
Cộng phát sinh | | | 110.000.000 | 110.000.000
Dư cuối kỳ | | | 0 |
```

## 8. Validation rules

- Số lượng > 0
- Đơn giá ≥ 0
- VAT rate phải thuộc {0, 5, 8, 10, -KT}
- Nhập khẩu: tỷ giá > 0 nếu currency != VND
- Tổng tiền thanh toán ≤ (total - paid_amount)
- Chi phí mua: tổng phân bổ = tổng chi phí (sai số < 1 VND)

## 9. Phân quyền

- `purchase.invoice.view`, `.create`, `.edit`, `.delete`
- `purchase.invoice.post`
- `purchase.expense.allocate`
- `purchase.vendor.view`, `.create`, `.edit`
- `purchase.input_invoice.pull` (pull từ TCT)
- `purchase.input_invoice.match`

---

**Tiếp theo**: [05. Tồn kho](./05-ton-kho.md)
