# 05. Module Tồn kho (Inventory)

> Nhập/xuất/điều chuyển kho, tính giá vốn hàng tồn, thẻ kho, tổng hợp NXT.

## 1. Mục đích nghiệp vụ

- Quản lý toàn bộ luồng hàng hóa, vật tư trong các kho
- Hỗ trợ nhiều **phương pháp tính giá xuất kho**:
  - Trung bình tháng (Weighted Average Monthly)
  - Trung bình di động theo ngày (Moving Average Daily)
  - Nhập trước xuất trước (FIFO)
- Theo dõi tồn kho theo: sản phẩm, kho, lô, hạn sử dụng, đối tượng
- Phục vụ hạch toán tự động:
  - Xuất bán: N632 / C156
  - Xuất sản xuất: N621, N622 / C152, C153, C156
  - Xuất đầu tư XDCB: N241 / C152, C156
- Cung cấp dữ liệu cho BCTC: TK 151, 152, 153, 155, 156, 157

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chứng từ | TK chính | Mô tả |
|----------|---------|------|
| Phiếu nhập kho | N152, N156 / C151, C331, C138... | Nhập từ mua, sản xuất, thuê ngoài, biếu tặng |
| Phiếu xuất kho | N621, N632, N241 / C152, C156 | Xuất bán, sản xuất, đầu tư |
| Phiếu xuất điều chuyển | N152 (kho đích) / C152 (kho nguồn) | Chuyển giữa các kho |

### 2.2. Giá tồn kho (Costing)

| Phương pháp | TT133 | Mô tả |
|-------------|-------|------|
| Trung bình tháng | Mặc định | Bình quân gia quyền cuối tháng |
| Trung bình di động theo ngày | Tùy chọn | Tính lại sau mỗi lần nhập |
| Nhập trước xuất trước (FIFO) | Tùy chọn | Xuất theo giá nhập cũ nhất |

### 2.3. Báo cáo

| Báo cáo | Mô tả |
|---------|------|
| Tổng hợp nhập xuất tồn | NXT theo sản phẩm, nhóm, kho |
| Thẻ kho (S10, 12-DN, S6, S8-DNN) | Stock card |

### 2.4. Tồn kho đầu kỳ

| Chức năng | Mô tả |
|----------|------|
| Vào số tồn kho ban đầu | Khai báo tồn đầu kỳ |
| Vào chi tiết tồn kho NTXT | Tồn chi tiết theo lô, NTXT |
| Kết chuyển số tồn kho sang năm sau | Carry-forward |
| Tính lại số tồn kho tức thời | Recalculate real-time stock |

### 2.5. Danh mục từ điển

| Danh mục | Trường chính |
|----------|-------------|
| Hàng hóa, vật tư | code, name, unit, product_type, gl_account_inv, gl_account_cogs |
| Nhóm hàng hóa, vật tư | group_code, name, parent_group_id |
| Danh mục quy đổi đvt | product_id, from_unit, to_unit, conversion_factor |
| Danh mục kho | code, name, type, manager, address |
| Danh mục lô | lot_code, product_id, lot_date, expiry_date, initial_quantity |

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình nhập kho

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Phiếu nhập   │ →  │ Tính giá    │ →  │ Cập nhật    │
│ kho          │    | nhập (nếu   │    | tồn kho    │
│              │    | chưa có)    │    | (theo lô)  │
└──────────────┘    └──────────────┘    └──────────────┘
       ↓                                       ↓
┌──────────────────────────┐    ┌──────────────────────┐
│ Sinh voucher:            │    │ Cập nhật stock_card │
│ N156 / C331 (mua)        │    │ + stock_ledger      │
│ hoặc N156 / C154 (sx)    │    │                      │
└──────────────────────────┘    └──────────────────────┘
```

### 3.2. Quy trình xuất kho

```
┌──────────────┐    ┌────────────────┐    ┌──────────────┐
│ Phiếu xuất   │ →  │ Tính giá xuất  │ →  │ Cập nhật    │
│ kho          │    | (theo pp tính) │    | tồn kho    │
└──────────────┘    └────────────────┘    └──────────────┘
                            ↓
              ┌─────────────────────────────┐
              │ - Trung bình tháng:         │
              │   (tổng giá trị / tổng SL) │
              │ - Trung bình di động:       │
              │   Tính lại sau mỗi nhập     │
              │ - FIFO:                     │
              │   Lấy từ lô nhập cũ nhất   │
              └─────────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │ Sinh voucher:               │
              │ N632 / C156 (xuất bán)      │
              │ N621 / C152 (sx CKC)        │
              │ N241 / C156 (đầu tư XDCB)   │
              └─────────────────────────────┘
```

### 3.3. Quy trình điều chuyển

```
Phiếu xuất điều chuyển:
1. Kho nguồn: C152 (giảm)
2. Kho đích: N152 (tăng)
3. Giá chuyển = giá vốn tại kho nguồn
4. Không phát sinh chênh lệch
```

## 4. Phương pháp tính giá xuất kho (chi tiết)

### 4.1. Trung bình tháng (default)

```
Tính vào cuối tháng:
GT_tb = (GT_tồn_đầu + GT_nhập_trong_tháng) / (SL_tồn_đầu + SL_nhập_trong_tháng)

Giá xuất = SL_xuất × GT_tb

Lưu ý: Tồn kho có thể âm tạm thời trong tháng, cuối tháng mới tính giá
```

### 4.2. Trung bình di động

```
Sau mỗi lần nhập, tính lại:

Sau lần nhập i:
GT_tb_i = (GT_tồn_hiện + GT_nhập_i) / (SL_tồn_hiện + SL_nhập_i)

Khi xuất:
Giá xuất = SL_xuất × GT_tb_hiện_tại

Cập nhật GT_tồn = GT_tồn - giá xuất
```

### 4.3. FIFO

```
Khi xuất:
1. Lấy từ lô nhập cũ nhất trước
2. Nếu lô hết → lô kế tiếp
3. Cứ cho đến khi đủ số lượng xuất

Ví dụ: Tồn gồm:
- Lô A: 100c × 10.000đ (nhập 01/06)
- Lô B: 50c × 12.000đ (nhập 10/06)

Xuất 120c → lấy 100c từ A + 20c từ B
Giá xuất = 100×10000 + 20×12000 = 1.240.000đ
```

## 5. Entity relationship

```
┌──────────────┐     ┌──────────────┐
│ Product      │ 1 * │ StockCard    │
└──────────────┘─────│ (Thẻ kho)   │
       ↑              └──────────────┘
       │                     │ 1
       │                     ↓ *
┌──────┴──────┐       ┌──────────────────┐
│ProductGroup │       │ StockLedger      │
└─────────────┘       │ (Mỗi dòng giao dịch)│
                      └──────────────────┘
                              ↑
                              │
┌──────────────┐       ┌──────┴─────────┐
│ Warehouse    │ 1   * │ StockVoucher   │
└──────────────┘───────┤ (Ph.nhập/xuất) │
                       └────────────────┘
                              │ 1
                              ↓ *
                       ┌──────────────────┐
                       │ StockVoucherLine │
                       └──────────────────┘
                              ↓
                       ┌──────────────────┐
                       │ StockLotMovement │
                       │ (FIFO tracking)  │
                       └──────────────────┘
```

## 6. Đặc tả bảng chính

**`product`** (Hàng hóa, vật tư):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| code | VARCHAR(50) | Mã |
| name | VARCHAR(500) | Tên |
| name_en | VARCHAR(500) | |
| product_type | ENUM | raw_material, semi_finished, finished, goods, supplies, tool |
| unit_id | VARCHAR(20) | ĐVT chính |
| group_id | BIGINT FK | |
| barcode | VARCHAR(50) | |
| weight | DECIMAL(18,4) | |
| volume | DECIMAL(18,4) | |
| cost_method | ENUM | weighted_avg, moving_avg, fifo |
| gl_account_inv | VARCHAR(20) | TK tồn kho (152, 156...) |
| gl_account_cogs | VARCHAR(20) | TK giá vốn (632) |
| gl_account_revenue | VARCHAR(20) | TK doanh thu (5111) |
| default_tax_rate | DECIMAL(6,4) | VAT mặc định |
| min_stock | DECIMAL(18,4) | Tồn tối thiểu |
| max_stock | DECIMAL(18,4) | Tồn tối đa |
| is_active | BOOL | |

**`warehouse`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(20) | |
| name | VARCHAR(255) | |
| type | ENUM | material, finished, transit, virtual |
| manager_id | BIGINT FK | NV phụ trách |
| address | TEXT | |
| gl_account | VARCHAR(20) | TK liên kết |

**`stock_voucher`** (Phiếu nhập/xuất kho):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| voucher_type | ENUM | receipt, issue, transfer |
| voucher_no | VARCHAR(50) | |
| voucher_date | DATE | |
| warehouse_id | BIGINT FK | Kho (kho đích cho receipt, nguồn cho issue) |
| to_warehouse_id | BIGINT FK | Cho transfer |
| related_voucher_id | BIGINT FK | Phiếu mua/bán/liên quan |
| reason | TEXT | |
| total_amount | DECIMAL(20,4) | Tổng giá trị |
| gl_voucher_id | BIGINT FK | |
| status | TINYINT | |

**`stock_voucher_line`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| voucher_id | BIGINT FK | |
| product_id | BIGINT FK | |
| lot_id | BIGINT FK | nullable |
| description | TEXT | |
| quantity | DECIMAL(18,4) | |
| unit_id | VARCHAR(20) | |
| unit_cost | DECIMAL(20,4) | Đơn giá |
| amount | DECIMAL(20,4) | |
| gl_account_inv | VARCHAR(20) | |
| gl_account_offset | VARCHAR(20) | TK đối ứng |

**`stock_lot`** (Lô hàng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| product_id | BIGINT FK | |
| lot_code | VARCHAR(50) | |
| lot_date | DATE | Ngày nhập lô |
| expiry_date | DATE | HSD |
| initial_quantity | DECIMAL(18,4) | |
| current_quantity | DECIMAL(18,4) | |

**`stock_card`** (Thẻ kho):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| product_id | BIGINT FK | |
| warehouse_id | BIGINT FK | |
| period | CHAR(7) | 'YYYY-MM' |
| opening_quantity | DECIMAL(18,4) | |
| opening_amount | DECIMAL(20,4) | |
| receipt_quantity | DECIMAL(18,4) | |
| receipt_amount | DECIMAL(20,4) | |
| issue_quantity | DECIMAL(18,4) | |
| issue_amount | DECIMAL(20,4) | |
| closing_quantity | DECIMAL(18,4) | |
| closing_amount | DECIMAL(20,4) | |
| avg_cost | DECIMAL(20,4) | Đơn giá bình quân |

**`stock_ledger`** (Sổ chi tiết tồn kho - FIFO tracking):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| product_id | BIGINT FK | |
| warehouse_id | BIGINT FK | |
| transaction_date | DATETIME | |
| transaction_type | ENUM | receipt, issue |
| lot_id | BIGINT FK | |
| quantity | DECIMAL(18,4) | + cho receipt, - cho issue |
| unit_cost | DECIMAL(20,4) | |
| amount | DECIMAL(20,4) | |
| related_voucher_id | BIGINT | |
| balance_quantity | DECIMAL(18,4) | Tồn sau giao dịch |
| balance_amount | DECIMAL(20,4) | |

## 7. Use cases

### UC-15: Lập phiếu nhập kho từ mua hàng

1. Khi phiếu nhập mua ở module Mua hàng được lưu:
   - Tự động sinh phiếu nhập kho ở module Tồn kho
   - Cập nhật stock_card, stock_ledger
2. Hoặc tạo thủ công:
   - Tồn kho → Cập nhật số liệu → Phiếu nhập kho
   - Chọn kho, product, quantity, unit_cost
3. Lưu → sinh voucher GL: N156 / C331 (mua), C154 (sx), v.v.

### UC-16: Xuất kho bán hàng

1. Tồn kho → Cập nhật số liệu → Phiếu xuất kho
2. Chọn kho, product, quantity, đối tượng sử dụng
3. Hệ thống tính giá xuất tự động theo cost_method
4. Sinh voucher: N632 / C156

### UC-17: Tính giá trung bình tháng

Trigger cuối tháng:

1. Tính tổng giá trị nhập + tồn đầu / tổng SL = đơn giá TB tháng
2. Cập nhật lại tất cả stock_ledger trong tháng với unit_cost TB
3. Cập nhật stock_card với avg_cost mới
4. Tính lại giá vốn của tất cả stock_voucher_type='issue' trong tháng
5. Điều chỉnh bút toán GL (nếu có chênh lệch)

### UC-18: Báo cáo thẻ kho

```
THẺ KHO
Sản phẩm: SP001 - Pin AA
Kho: KHO_HN   Tháng: 06/2026

Ngày   | CT   | Diễn giải   | TK ĐƯ | Nhập SL | Nhập TT | Xuất SL | Xuất TT | Tồn SL | Tồn TT
-------|------|-------------|-------|---------|---------|---------|---------|--------|------
01/06  |      | Tồn đầu     |       |         |         |         |         | 1000   | 10.000.000
05/06  | PN01 | Nhập từ NCC | 331   | 500     | 5.500.000|        |         | 1500   | 15.500.000
10/06  | PX01 | Xuất bán   | 632   |         |         | 200     | 2.066.667| 1300  | 13.433.333
...
       |      | Cộng PS    |       | 500     | 5.500.000| 200    | 2.066.667|
       |      | Tồn cuối   |       |         |         |         |         | 1300   | 13.433.333
       
Đơn giá bình quân: 10.333đ/c
```

## 8. Validation rules

- SL nhập > 0, SL xuất > 0
- Khi xuất:
  - SL xuất ≤ SL tồn hiện tại (trừ trung bình tháng cho phép tồn âm tạm thời)
  - Lô (FIFO) phải tồn tại và còn hàng
- Khi transfer: kho nguồn ≠ kho đích
- Hàng hóa phải có `is_active=true`
- Kho phải có type phù hợp (raw material kho không nhận finished goods)

## 9. Phân quyền

- `stock.voucher.view`, `.create`, `.edit`, `.delete`
- `stock.voucher.post`
- `stock.product.view`, `.create`, `.edit`
- `stock.warehouse.view`, `.create`, `.edit`
- `stock.cost.calculate` (chạy tính giá cuối kỳ)
- `stock.opening_balance.edit` (số dư đầu kỳ)
- `stock.year_end.carry_forward`

---

**Tiếp theo**: [06. Tài sản cố định](./06-tai-san-co-dinh.md)
