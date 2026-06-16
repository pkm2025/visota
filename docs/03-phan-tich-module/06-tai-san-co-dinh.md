# 06. Module Tài sản cố định (Fixed Assets)

> Quản lý toàn vòng đời TSCĐ: tăng, giảm, điều chuyển, khấu hao, thanh lý.

## 1. Mục đích nghiệp vụ

- Quản lý TSCĐ hữu hình (211), vô hình (213), thuê tài chính (212)
- Tự động tính khấu hao theo các phương pháp:
  - Đường thẳng (Straight-line) — mặc định
  - Số dọa giảm dần có điều chỉnh (Declining balance)
  - Khấu hao theo sản lượng (Units of production)
- Phân bổ khấu hao cho các bộ phận sử dụng (cost center)
- Sinh bút toán chi phí khấu hao định kỳ: N641/642/635 / C214
- Cung cấp báo cáo tăng/giảm/khấu hao theo TT133 mẫu 06-TSCĐ

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chức năng | Mô tả |
|----------|------|
| Cập nhật tài sản | Khai báo TSCĐ mới (tăng) |
| Khai báo thay đổi TSCĐ | Thay đổi thông tin (giá, thời gian, bp sd) |
| Điều chuyển | Chuyển TSCĐ giữa các bộ phận |
| Sản lượng | Cập nhật sản lượng (cho pp theo sản lượng) |
| Tính khấu hao | Tính KH định kỳ |
| Điều chỉnh khấu hao | Điều chỉnh do sai sót hoặc thay đổi |
| Khai báo hệ số phân bổ | Hệ số phân bổ KH cho nhiều BP |
| Tính khấu hao chi tiết | Tính theo từng tài sản |
| Tạo bút toán chi phí khấu hao | Sinh voucher GL |

### 2.2. Báo cáo

| Báo cáo | Mô tả |
|---------|------|
| Bảng tính khấu hao TSCĐ (06-TSCĐ) | Mẫu chuẩn Bộ Tài chính |
| Bảng tính khấu hao TSCĐ - chi tiết | Theo từng TS |
| Bảng tính khấu hao TSCĐ theo bpsd | Theo bộ phận |
| Bảng tổng hợp khấu hao TSCĐ | Tổng theo loại/bp |
| Bảng tổng hợp khấu hao - theo 2 chỉ tiêu | Theo 2 phân tích |
| Bảng kê phân bổ khấu hao TSCĐ | Phân bổ cho bp |
| Bảng kê TSCĐ tăng trong kỳ | Tăng trong kỳ |
| Bảng kê TSCĐ giảm trong kỳ | Giảm trong kỳ |
| Báo cáo tổng hợp tăng giảm TSCĐ | Tổng hợp |
| Bảng cân đối phát sinh TSCĐ | BCĐPS cho 211, 214 |

### 2.3. Danh mục từ điển

| Danh mục | Trường chính |
|----------|-------------|
| Bộ phận sử dụng TSCĐ | code, name, gl_account_expense |
| Lý do tăng giảm | reason_code, type (increase/decrease), description |
| Nguồn vốn | source_code (vốn tự có, vay, vốn đ.switch), description |
| Loại tài sản | type_code, name (hữu hình, vô hình, ...) |
| Nhóm tài sản | group_code, name, depreciation_rate (mặc định) |
| Phân nhóm tài sản | subgroup_code, name, parent_group |

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình tăng TSCĐ

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Mua/XDCB/    │ → │ Cập nhật TS  │ → │ Bắt đầu tính │ → │ Hạch toán:   │
│ Nhận GG      │    | (khai báo)  │    | khấu hao    │    | N211 / C241  |
└──────────────┘    └──────────────┘    └──────────────┘    | hoặc C111,  |
                                                              | C331...    |
                                                              └──────────────┘
```

### 3.2. Quy trình khấu hao định kỳ

```
1. Chạy hàng tháng:
   - Lọc TSCĐ đang khấu hao (status='active', start_date ≤ today ≤ end_date)
   - Tính KH tháng = nguyên giá × tỷ lệ KH năm / 12
   - Lưu vào `asset_depreciation`

2. Phân bổ cho bộ phận:
   - Nếu TS dùng chung nhiều bp → phân bổ theo hệ số
   - Sinh bút toán chi phí cho từng bp

3. Sinh voucher GL:
   N641 (bp bán hàng) / C2141
   N642 (bp quản lý) / C2141
   N621 (bp sx) / C2141
   N635 (bp TC) / C2141
```

### 3.3. Phương pháp khấu hao

#### Đường thẳng

```
KH_năm = (Nguyên giá - GT dự kiến thanh lý) / Số năm KH
KH_tháng = KH_năm / 12
```

#### Số dư giảm dần có điều chỉnh

```
Nửa đầu thời gian KH:
KH_năm = Giá trị còn lại × tỷ lệ KH × hệ số điều chỉnh (1.5, 2.0, 2.5)
Nửa sau: chuyển sang đường thẳng
```

#### Theo sản lượng

```
KH_năm = (Nguyên giá - GT dự kiến thanh lý) × (Sản lượng năm / Tổng sản lượng dự kiến)
```

### 3.4. Giảm TSCĐ

Nguyên nhân: thanh lý, nhượng bán, mất mát, hư hỏng.

```
1. Ngừng tính khấu hao
2. Hạch toán:
   - Ghi giảm:
     N214 (hao mòn lũy kế)        : đã KH lũy kế
     N811 (chi phí khác)          : giá trị còn lại
     C211 (nguyên giá)            : nguyên giá
   
   - Nếu nhượng bán có lãi:
     N111, N131 (tiền/HTKH)       : số thu
     C711 (thu nhập khác)         : doanh thu thanh lý
     N33311 (VAT output)          : VAT (nếu có)
```

## 4. Entity relationship

```
┌────────────────┐    ┌──────────────────────┐
│ FixedAsset     │ 1 *│ AssetDepreciation    │
│ (Tài sản)      │───→│ (Khấu hao kỳ)        │
└────────────────┘    └──────────────────────┘
        │
        │ 1
        ↓ *
┌────────────────────────┐
│ AssetTransaction       │
│ (Tăng/giảm/điều chuyển)│
└────────────────────────┘

┌──────────────────┐    ┌──────────────────────┐
│ AssetUsingDept   │ 1 *│ AssetAllocationRule  │
└──────────────────┘───→│ (Hệ số phân bổ)     │
                       └──────────────────────┘
```

## 5. Đặc tả bảng chính

**`fixed_asset`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| asset_code | VARCHAR(50) | Mã TS |
| asset_name | VARCHAR(255) | |
| asset_type_id | BIGINT FK | |
| asset_group_id | BIGINT FK | |
| using_dept_id | BIGINT FK | |
| capital_source_id | BIGINT FK | Nguồn vốn |
| gl_account | VARCHAR(20) | TK 2111, 2112, 213... |
| depreciation_account | VARCHAR(20) | TK 2141, 2142, 2143 |
| expense_account | VARCHAR(20) | TK 641, 642, 635... |
| original_cost | DECIMAL(20,4) | Nguyên giá |
| currency_code | CHAR(3) | |
| depreciation_method | ENUM | straight_line, declining_balance, units_of_production |
| depreciation_rate | DECIMAL(8,4) | % năm |
| useful_life_months | INT | Số tháng sử dụng |
| start_date | DATE | Ngày bắt đầu tính KH |
| end_date | DATE | Ngày hết KH (dự kiến) |
| salvage_value | DECIMAL(20,4) | GT dự kiến thanh lý |
| accumulated_depreciation | DECIMAL(20,4) | KH lũy kế |
| net_book_value | DECIMAL(20,4) | GT còn lại |
| status | ENUM | draft, active, fully_depreciated, disposed |
| production_capacity | DECIMAL(18,4) | Tổng SL dự kiến (cho uom method) |

**`asset_depreciation`** (Lịch sử KH kỳ):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| asset_id | BIGINT FK | |
| period | CHAR(7) | 'YYYY-MM' |
| depreciation_amount | DECIMAL(20,4) | KH trong kỳ |
| accumulated_depreciation_end | DECIMAL(20,4) | Lũy kế cuối kỳ |
| net_book_value_end | DECIMAL(20,4) | NBV cuối kỳ |
| gl_voucher_id | BIGINT FK | |
| posted_at | DATETIME | |

**`asset_transaction`** (Tăng/giảm/điều chuyển):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| transaction_no | VARCHAR(50) | |
| transaction_date | DATE | |
| transaction_type | ENUM | increase, decrease, transfer, revaluation, change_info |
| asset_id | BIGINT FK | |
| reason_id | BIGINT FK | Lý do |
| amount_change | DECIMAL(20,4) | Thay đổi nguyên giá (nếu có) |
| new_dept_id | BIGINT FK | Cho transfer |
| new_useful_life | INT | Thay đổi thời gian KH |
| new_rate | DECIMAL(8,4) | |
| gl_voucher_id | BIGINT FK | |
| description | TEXT | |

**`asset_allocation_rule`** (Phân bổ cho nhiều bp):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| asset_id | BIGINT FK | |
| using_dept_id | BIGINT FK | |
| allocation_coefficient | DECIMAL(8,4) | Hệ số |
| gl_account_expense | VARCHAR(20) | |

## 6. Use cases

### UC-19: Khai báo TSCĐ mới

1. TSCĐ → Cập nhật số liệu → Cập nhật tài sản → Thêm mới
2. Nhập:
   - Mã TS, tên TS
   - Loại TS, nhóm TS
   - BP sử dụng, nguồn vốn
   - Nguyên giá, NT
   - PP khấu hao, tỷ lệ KH, số năm sử dụng
   - Ngày bắt đầu tính KH
   - GT dự kiến thanh lý
3. Lưu → hạch toán tăng TS: N211 / C241 (hoặc C111/C331)
4. TS có status='active', sẵn sàng tính KH

### UC-20: Tính khấu hao hàng tháng

1. TSCĐ → Cập nhật số liệu → Tính khấu hao
2. Chọn kỳ (tháng)
3. Hệ thống:
   - Lọc TSCĐ đang active
   - Tính KH từng TS theo pp
   - Phân bổ cho bp (nếu có allocation_rule)
4. Tạo `asset_depreciation` records
5. Tạo voucher GL: N641/642/635 / C2141

### UC-21: Thanh lý TSCĐ

1. TSCĐ → Khai báo thay đổi TSCĐ → Thanh lý
2. Chọn TS, nhập lý do, ngày thanh lý, giá thu về
3. Hệ thống:
   - Ngừng tính KH từ ngày thanh lý
   - Tính KH thêm đến ngày thanh lý (nếu chưa)
   - Hạch toán giảm TS:
     N214 (hao mòn lũy kế)
     N811 (chi phí khác) = NBV
     C211 (nguyên giá)
   - Nếu có thu tiền: N111 / C711 + N33311

### UC-22: Điều chuyển TSCĐ giữa các BP

1. TSCĐ → Điều chuyển → Thêm mới
2. Chọn TS, BP mới, ngày điều chuyển
3. Hệ thống:
   - Cập nhật asset.using_dept_id
   - Hạch toán (chỉ gl_account_expense thay đổi từ kỳ sau):
     Đảo ngược phần KH còn lại của kỳ chuyển
     Sinh voucher mới với gl_account_expense của BP mới
   - Lưu asset_transaction với type='transfer'

## 7. Báo cáo 06-TSCĐ

```
BẢNG TÍNH KHẤU HAO TSCĐ
Đơn vị: ………  Kỳ: 06/2026

STT | Tên TS | Nguyên giá | Hao mòn lũy kế đến đầu kỳ | Giá trị còn lại đầu kỳ | KH trong kỳ | Hao mòn lũy kế đến cuối kỳ | Giá trị còn lại cuối kỳ
----|---------|------------|-------------------------|----------------------|-------------|-----------------------------|---------------------
1   | Xe Toyota | 1.500.000.000 | 600.000.000 | 900.000.000 | 25.000.000 | 625.000.000 | 875.000.000
2   | Máy CNC   | 2.000.000.000 | 400.000.000 | 1.600.000.000 | 33.333.333 | 433.333.333 | 1.566.666.667
...
    | CỘNG     |             |             |             | 58.333.333 |             |
```

## 8. Validation rules

- Nguyên giá > 0
- Ngày bắt đầu KH ≤ ngày kết thúc KH
- Tỷ lệ KH > 0 và ≤ 100 (nếu theo %)
- Khi thanh lý: ngày thanh lý ≥ ngày bắt đầu tính KH
- Khi điều chuyển: BP mới phải khác BP cũ

## 9. Phân quyền

- `fa.asset.view`, `.create`, `.edit`
- `fa.transaction.increase`, `.decrease`, `.transfer`
- `fa.depreciation.calculate`, `.adjust`
- `fa.report.view`

---

**Tiếp theo**: [07. Công cụ dụng cụ](./07-cong-cu-dung-cu.md)
