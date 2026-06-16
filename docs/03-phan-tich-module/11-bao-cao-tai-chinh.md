# 11. Module Báo cáo tài chính (Financial Statements)

> BCTC theo TT133/TT200: BCĐTK, B01-DN, B02-DN, B03-DN.

## 1. Mục đích nghiệp vụ

- Cung cấp **báo cáo tài chính (BCTC)** theo quy định của Bộ Tài chính
- Áp dụng theo 2 chế độ:
  - **TT133/2016** (doanh nghiệp nhỏ và vừa): B01a-DN, B02a-DN, B03a-DN
  - **TT200/2014** (doanh nghiệp lớn): B01-DN, B02-DN, B03-DN
- Phục vụ:
  - Quản trị nội bộ
  - Báo cáo cho cổ đông, nhà đầu tư
  - Báo cáo cho cơ quan thuế, thống kê
  - Báo cáo cho ngân hàng (vay vốn)

## 2. Báo cáo chi tiết

### 2.1. Bảng cân đối tài khoản (Trial Balance)

- **Mẫu**: S06-DN (TT133), F01-DNN (TT200 simplified)
- **Mục đích**: Kiểm tra cân đối N=C sau ghi sổ
- **Cấu trúc**:
  ```
  TK | Tên TK | Số dư đầu |          | Phát sinh |          | Số dư cuối |          |
     |        | Nợ        | Có       | Nợ        | Có       | Nợ         | Có       |
  ```

### 2.2. Báo cáo tình hình tài chính (Balance Sheet)

- **Mẫu TT133**: B01a-DN
- **Mẫu TT200**: B01-DN
- **Cấu trúc**:
  ```
  TÀI SẢN
    A. TÀI SẢN NGẮN HẠN
      I. Tiền và các khoản tương đương tiền
        1. Tiền (110, 111, 112, 113)
      II. Đầu tư tài chính ngắn hạn
      III. Các khoản phải thu ngắn hạn
      IV. Hàng tồn kho
      V. Tài sản ngắn hạn khác
    B. TÀI SẢN DÀI HẠN
      ...

  NGUỒN VỐN
    C. NỢ PHẢI TRẢ
      I. Nợ ngắn hạn
      II. Nợ dài hạn
    D. VỐN CHỦ SỞ HỮU
      I. Vốn chủ sở hữu
      II. Nguồn kinh phí và quỹ khác
  ```

### 2.3. Báo cáo kết quả SXKD (P&L)

- **Mẫu TT133**: B02a-DN
- **Mẫu TT200**: B02-DN
- **Cấu trúc**:
  ```
  1. Doanh thu (511)
  2. Các khoản giảm trừ doanh thu (521, 531, 532)
  3. Doanh thu thuần (1-2)
  4. Giá vốn hàng bán (632)
  5. Lợi nhuận gộp (3-4)
  6. Doanh thu hoạt động tài chính (515)
  7. Chi phí tài chính (635)
  8. Chi phí bán hàng (641)
  9. Chi phí quản lý DN (642)
  10. Lợi nhuận từ HĐKD = 5+6-7-8-9
  11. Thu nhập khác (711)
  12. Chi phí khác (811)
  13. Lợi nhuận khác (11-12)
  14. Tổng lợi nhuận trước thuế (10+13)
  15. TNDN (821)
  16. Lợi nhuận sau thuế (14-15)
  ```

### 2.4. Báo cáo dòng tiền (Cash Flow)

- **Mẫu TT133**: B03a-DN
- **Mẫu TT200**: B03-DN
- Hai phương pháp:
  - **Trực tiếp** (Direct): từ sales receipts - payments
  - **Gián tiếp** (Indirect): từ LNST + điều chỉnh

**Trực tiếp**:
```
I. Dòng tiền từ HĐKD
  1. Tiền thu từ KH, người mua
  2. Tiền trả cho NCC, người bán
  3. Tiền thu khác từ HĐKD
  4. Tiền chi khác cho HĐKD
  => Dòng tiền ròng từ HĐKD
II. Dòng tiền từ HĐĐT
  ...
III. Dòng tiền từ HĐTC
  ...
```

**Gián tiếp**:
```
I. Dòng tiền từ HĐKD (điều chỉnh từ LNST)
  - Lợi nhuận trước thuế
  - (+) Khấu hao TSCĐ
  - (+/-) Tăng/giảm dự phải thu
  - (+/-) Tăng/giảm tồn kho
  - (+/-) Tăng/giảm phải trả
  ...
```

## 3. Ma trận mapping TK → BCTC (TT133)

| Chỉ tiêu | Tài khoản Nợ | Tài khoản Có | Cách tính |
|---------|------------|------------|----------|
| Tiền | 111, 112, 113 | | Số dư Nợ |
| Đầu tư TC ngắn hạn | 121, 128 | | Số dư Nợ |
| Phải thu KH | 131 | 129 | N-C |
| Trả trước cho NSB | 1388 | | N |
| Tồn kho | 151, 152, 153, 156, 155, 157 | 229 | N-C |
| TSCĐ | 211, 213 | 214 | N-C |
| Nợ phải trả người bán | 331 | | C |
| Vốn ĐT của CSH | 411 | | C |
| Doanh thu | | 511 | Ps C |
| Giá vốn | 632 | | Ps N |
| Chi phí bán hàng | 641 | | Ps N |
| Chi phí QLDN | 642 | | Ps N |
| Chi phí TC | 635 | | Ps N |
| Thu nhập khác | | 711 | Ps C |
| Chi phí khác | 811 | | Ps N |
| Chi phí TNDN | 821, 8212 | 8211, 921 | N-C |

## 4. Entity (report definition)

Do BCTC có cấu trúc cố định theo chế độ kế toán, ta không cần bảng phức tạp. Đề xuất:

**`report_definition`** (cấu hình BCTC):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(50) | 'B01-DN', 'B02-DN' |
| name | VARCHAR(255) | |
| accounting_regime | ENUM | tt133, tt200 |
| template_json | JSON | Định nghĩa cấu trúc + công thức |

`template_json` chứa danh sách các dòng:
```json
{
  "rows": [
    {
      "code": "I",
      "label": "Tiền và các khoản tương đương tiền",
      "formula": "=110+111+112+113",
      "is_header": true
    },
    {
      "code": "1",
      "label": "Tiền mặt",
      "account_pattern": "111*",
      "balance_type": "debit"
    },
    ...
  ]
}
```

**`report_run`** (lịch sử chạy BCTC):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| report_code | VARCHAR(50) | |
| fiscal_year | SMALLINT | |
| from_period | TINYINT | |
| to_period | TINYINT | |
| generated_at | DATETIME | |
| generated_by | BIGINT FK | |
| parameters_json | JSON | |
| output_url | VARCHAR(500) | PDF/Excel |
| snapshot_json | JSON | Snapshot số liệu |

## 5. Use cases

### UC-35: Lập BCĐTK tháng

1. BCTC → Bảng cân đối tài khoản
2. Chọn kỳ (tháng/quý/năm), từ ngày, đến ngày
3. Hệ thống:
   - Lấy số dư đầu (từ account_opening_balance)
   - Tính phát sinh trong kỳ (từ voucher_line)
   - Tính số dư cuối
4. Hiển thị theo cấu trúc, cho phép drill-down đến voucher
5. Xuất Excel/PDF theo mẫu S06-DN

### UC-36: Lập B01-DN (BCTC)

1. BCTC → Báo cáo tình hình tài chính
2. Chọn kỳ (năm + ngày lập BCTC)
3. Hệ thống:
   - Tính số dư cuối kỳ của các TK
   - Áp dụng template B01-DN (TT200) hoặc B01a-DN (TT133)
   - Tính từng chỉ tiêu theo công thức
4. Xuất theo mẫu quy định
5. (Tùy chọn) Đối chiếu với năm trước

### UC-37: Lập B03-DN (Lưu chuyển tiền tệ)

1. BCTC → BC dòng tiền theo PP trực tiếp hoặc gián tiếp
2. Hệ thống:
   - **Trực tiếp**: phân tích các bút toán thu/chi trên TK 111, 112 theo voucher_type
   - **Gián tiếp**: từ LNST (B02-DN) + điều chỉnh
3. Xuất theo mẫu

## 6. Validation rules

- Tổng TÀI SẢN = Tổng NGUỒN VỐN (trên B01-DN)
- LNST trên B02-DN phải khớp với kết quả chuyển số dư TK 421 cuối kỳ
- Tiền đầu kỳ + LCTT ròng = Tiền cuối kỳ (trên B03-DN)

## 7. Phân quyền

- `report.trial_balance.view`, `.export`
- `report.balance_sheet.view`, `.export`
- `report.pnl.view`, `.export`
- `report.cash_flow.view`, `.export`
- `report.full_set.generate` (sinh bộ BCTC đầy đủ)

---

**Tiếp theo**: [12. Báo cáo thuế](./12-bao-cao-thue.md)
