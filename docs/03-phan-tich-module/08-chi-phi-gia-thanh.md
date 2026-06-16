# 08. Module Chi phí, giá thành (Costing)

> Module phụ "Giá thành giản đơn" — tính giá thành theo phương pháp giản đơn (process costing).

## 1. Mục đích nghiệp vụ

- Tập hợp chi phí sản xuất (CP NVL, CP NHCT, CP SXC)
- Phân bổ chi phí dở dang đầu kỳ + chi phí phát sinh → chi phí dở dang cuối kỳ + giá thành sản phẩm hoàn thành
- Tính giá thành theo **phương pháp giản đơn** (single output hoặc equivalent units)
- Theo dõi chi phí theo phân xưởng

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chức năng | Mô tả |
|----------|------|
| Tính giá thành | Tính giá thành định kỳ |
| Hệ số sản phẩm | Hệ số quy đổi sản phẩm (nếu có nhiều loại sp cùng px) |

### 2.2. Số dư đầu

- Số dư ban đầu các phân xưởng
- Dở dang cuối kỳ các phân xưởng
- Kết chuyển số dư phân xưởng sang năm sau

### 2.3. Báo cáo giá thành

- Bảng giá thành sản phẩm
- Bảng cân đối phát sinh phân xưởng

### 2.4. Danh mục

- Phân xưởng
- Danh mục TK theo dõi số dư phân xưởng

## 3. Quy trình nghiệp vụ

### 3.1. Tập hợp chi phí sản xuất

Trong kỳ, các chi phí được tập hợp qua các bút toán:
- NLK trực tiếp: N621 (CP NVL) / C152, C153
- Nhân công trực tiếp: N622 (CP NC) / C111, C334
- SXC chung: N627 (CP SXC) / C111, C331, C214 (KH TSCĐ sx), C242 (PB CCDC)

### 3.2. Tính giá thành giản đơn

```
Giá thành 1 sp = (CP dở dang đầu kỳ + CP phát sinh - CP dở dang cuối kỳ) / Số lượng hoàn thành

CP dở dang cuối kỳ tính theo % hoàn thành (chi phí NVL 100%, NC 70%, SXC 60%...)
```

### 3.3. Kết chuyển chi phí

```
1. Kết chuyển CP NLK:
   N154 (sp hoàn thành) / C621

2. Kết chuyển CP NC:
   N154 / C622

3. Phân bổ và kết chuyển CP SXC:
   N154 / C627

4. Nhập kho thành phẩm:
   N155 / C154

5. Khi xuất bán:
   N632 / C155
```

## 4. Đặc tả bảng chính

**`workshop`** (Phân xưởng):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(20) | |
| name | VARCHAR(255) | |
| cost_account | VARCHAR(20) | TK 621/622/627 |
| wip_account | VARCHAR(20) | TK 154 |
| finished_account | VARCHAR(20) | TK 155 |
| manager_id | BIGINT FK | |

**`product_cost_period`** (Bảng tính giá thành kỳ):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| workshop_id | BIGINT FK | |
| product_id | BIGINT FK | |
| period | CHAR(7) | 'YYYY-MM' |
| opening_wip_material | DECIMAL(20,4) | |
| opening_wip_labor | DECIMAL(20,4) | |
| opening_wip_overhead | DECIMAL(20,4) | |
| incurred_material | DECIMAL(20,4) | |
| incurred_labor | DECIMAL(20,4) | |
| incurred_overhead | DECIMAL(20,4) | |
| closing_wip_material | DECIMAL(20,4) | |
| closing_wip_labor | DECIMAL(20,4) | |
| closing_wip_overhead | DECIMAL(20,4) | |
| completed_quantity | DECIMAL(18,4) | SL hoàn thành |
| unit_cost | DECIMAL(20,4) | Đơn giá thành |
| total_cost | DECIMAL(20,4) | Tổng giá thành |

**`product_coefficient`** (Hệ số sản phẩm):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| workshop_id | BIGINT FK | |
| product_id | BIGINT FK | |
| coefficient | DECIMAL(10,4) | Hệ số quy đổi |

## 5. Use cases

### UC-25: Tính giá thành tháng

1. CP, giá thành → Tính giá thành
2. Chọn kỳ, phân xưởng, sản phẩm
3. Hệ thống:
   - Lấy số dư đầu kỳ (dở dang đầu)
   - Lấy chi phí phát sinh (từ voucher GL, TK 621/622/627)
   - Nhập số lượng hoàn thành
   - Nhập % hoàn thành của dở dang cuối kỳ
   - Tính đơn giá = (DD đầu + PS - DD cuối) / SL HT
4. Sinh voucher kết chuyển: N154 / C621, C622, C627
5. Sinh voucher nhập kho: N155 / C154

### UC-26: Khai báo hệ số sản phẩm

1. CP, giá thành → Hệ số sản phẩm
2. Chọn phân xưởng
3. Nhập hệ số cho từng sản phẩm (ví dụ: sp A = 1, sp B = 1.5, sp C = 0.8)
4. Hệ thống dùng hệ số để phân bổ tổng chi phí

## 6. Báo cáo giá thành sản phẩm

```
BẢNG GIÁ THÀNH SẢN PHẨM
Phân xưởng: ………  Kỳ: 06/2026
Sản phẩm: SP001

Hạng mục | Dở dang đầu kỳ | Phát sinh trong kỳ | Dở dang cuối kỳ | Hoàn thành
---------|----------------|-------------------|----------------|-----------
CP NVL   | 10.000.000 | 50.000.000 | 5.000.000 | 55.000.000
CP NC    | 5.000.000  | 20.000.000 | 3.000.000 | 22.000.000
CP SXC   | 8.000.000  | 30.000.000 | 4.000.000 | 34.000.000
Tổng     | 23.000.000 | 100.000.000 | 12.000.000 | 111.000.000

Số lượng HT: 1000 sp
Đơn giá: 111.000đ/sp
```

## 7. Validation rules

- Số lượng hoàn thành ≥ 0
- Tổng chi phí = DD đầu + ps - DD cuối (sai số < 1 VND)
- Hệ số sản phẩm > 0

## 8. Phân quyền

- `costing.workshop.view`, `.create`, `.edit`
- `costing.coefficient.view`, `.edit`
- `costing.calculate` (chạy tính giá)
- `costing.opening_balance.edit`

---

**Tiếp theo**: [09. Quản lý nhân sự](./09-quan-ly-nhan-su.md)
