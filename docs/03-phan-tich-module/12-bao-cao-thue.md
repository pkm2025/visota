# 12. Module Báo cáo thuế (Tax Reports)

> Tờ khai thuế GTGT 01/GTGT, bảng kê đầu ra/đầu vào.

## 1. Mục đích nghiệp vụ

- Lập **tờ khai thuế GTGT** mẫu 01/GTGT (ban hành kèm TT80/2021/TT-BTC)
- Lập bảng kê hóa đơn đầu ra (01-1/GTGT), đầu vào (01-2/GTGT)
- Theo dõi hóa đơn GTGT đầu ra/đầu vào
- Hỗ trợ kê khai theo kỳ: tháng (DT < 50 tỷ) hoặc quý (DT ≥ 50 tỷ)

## 2. Quy định pháp lý (Quan trọng)

### 2.1. Thông tư 80/2021/TT-BTC

- Ban hành ngày 04/10/2021
- Quy định mẫu tờ khai thuế mới
- Bao gồm phụ lục:
  - **Phụ lục I**: Tờ khai quyết toán thuế TNDN (03/TNDN)
  - **Phụ lục II**: Tờ khai thuế GTGT (01/GTGT) + các phụ lục 01-1/GTGT, 01-2/GTGT
  - **Phụ lục III**: Tờ khai thuế TNCN
- Là cơ sở pháp lý cho toàn bộ kê khai thuế GTGT của doanh nghiệp

### 2.2. Thông tư 78/2021 → Thông tư 32/2025 (Hóa đơn điện tử)

- TT78/2021 áp dụng từ 01/07/2022
- TT32/2025 thay thế từ 01/06/2025 — quy định mới về ủy nhiệm lập HĐĐT, quản lý dữ liệu
- Phần mềm kế toán phải hỗ trợ cả hai giai đoạn

## 3. Báo cáo chi tiết

### 3.1. Tờ khai thuế 01/GTGT TT80

```
Mẫu: 01/GTGT
(Ban hành kèm Thông tư số 80/2021/TT-BTC ngày 04/10/2021 của BTC)

TỜ KHAI THUẾ GTGT
[01] Tên người nộp thuế: ......................................
[02] Mã số thuế: ...............................................
[03] Địa chỉ trụ sở: ...........................................
[04] Quận/Huyện: ............. [05] Tỉnh/Thành phố: ........
[06] Điện thoại: .............. [07] Fax: ....................
[08] Email: ....................................................
[09] Loại tờ khai: ☐ Mới  ☐ Bổ sung lần: ....
[10] Kỳ tính thuế: Tháng ☐  Quý ☐  Năm ☐
     Từ ngày ........./...../.......  Đến ngày ........./...../.......
[11] Lần đầu: ☐  [12] Đầu năm: ☐
[13] Doanh thu: ............................................

I. Hàng hóa, dịch vụ chịu thuế GTGT:
  Chỉ tiêu [21] giá trị HH DV bán ra chịu thuế: .............
  Chỉ tiêu [22] thuế GTGT của HH DV bán ra: .............
  Chỉ tiêu [23] HH DV bán ra không chịu thuế: .............
  Chỉ tiêu [24] HH DV bán ra chịu thuế suất 0%: .............
  Chỉ tiêu [25] HH DV bán ra chịu thuế suất 5%: .............
  Chỉ tiêu [26] HH DV bán ra chịu thuế suất 8%: .............
  Chỉ tiêu [27] HH DV bán ra chịu thuế suất 10%: .............

II. Hàng hóa, dịch vụ mua vào:
  Chỉ tiêu [28] giá trị HH DV mua vào còn được khấu trừ: .....
  Chỉ tiêu [29] thuế GTGT mua vào được khấu trừ: .....

III. Thuế GTGT phải nộp:
  [40] Số thuế GTGT của HH DV bán ra (=[22]): .....
  [41] Số thuế GTGT được khấu trừ kỳ này: .....
  [42] Số thuế GTGT còn được khấu trừ từ kỳ trước chuyển sang: .....
  [43] Số thuế GTGT của HH DV bán ra trong kỳ kéo dài: .....
  [44] Số thuế GTGT còn được khấu trừ của HH DV mua vào trong kỳ kéo dài: .....
  [45] Số thuế GTGT phải nộp trong kỳ (=[40]-[41]-[42]): .....

IV. Thuế GTGT được hoàn:
  [50] Số thuế GTGT đề nghị hoàn: .....
  
V. Thuế GTGT chuyển kỳ sau:
  [60] Số thuế GTGT đề nghị chuyển kỳ sau: .....

VI. Số thuế GTGT hoãn mức từng năm:
  ...
```

### 3.2. Bảng kê đầu ra (01-1/GTGT)

```
Mẫu: 01-1/GTGT
(Ban hành kèm Thông tư số 80/2021/TT-BTC)

BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ BÁN RA
Kỳ tính thuế: Tháng/Quý .... năm ....

STT | Ký hiệu HĐ | Số HĐ | Ngày phát hành | Tên người mua | MST người mua | Tên HH DV | Giá trị chưa thuế | Thuế suất | Thuế GTGT
----|-------------|--------|----------------|---------------|--------------|-----------|-------------------|-----------|----------
1   | AA/24E      | 0001   | 05/06/2026     | Cty ABC       | 0101234567   | Hàng hóa  | 100.000.000       | 10%       | 10.000.000
...
    A. HHDV chịu thuế suất 0%
    B. HHDV chịu thuế suất 5%
    C. HHDV chịu thuế suất 8%
    D. HHDV chịu thuế suất 10%
    E. HHDV không chịu thuế GTGT

Tổng cộng giá trị: .....
Tổng cộng thuế GTGT: .....
```

### 3.3. Bảng kê đầu vào (01-2/GTGT)

Tương tự 01-1 nhưng cho HHDV mua vào, có thêm cột:
- Có hóa đơn KO khấu trừ (ghi chú)

### 3.4. Hóa đơn GTGT đầu ra/đầu vào

Trong SIS có riêng màn hình "Hóa đơn GTGT đầu ra" và "Hóa đơn GTGT đầu vào" — đây là các view tổng hợp của hóa đơn bán/mua vào đã hạch toán TK 133, 33311.

## 4. Cấu trúc module

### 4.1. Cập nhật số liệu

Không có cập nhật riêng — dữ liệu đến từ các module khác:
- Đầu ra: từ module Bán hàng (`sales_invoice`)
- Đầu vào: từ module Mua hàng (`purchase_invoice`, `input_invoice`)
- VAT output: từ voucher có TK 33311
- VAT input: từ voucher có TK 1331, 1332

### 4.2. Báo cáo

| Báo cáo | Mẫu | Tần suất |
|---------|-----|---------|
| Tờ khai thuế 01/GTGT TT80 | 01/GTGT | Tháng/Quý |
| Bảng kê đầu ra | 01-1/GTGT | Tháng/Quý |
| Bảng kê đầu vào | 01-2/GTGT | Tháng/Quý |
| Hóa đơn GTGT đầu ra | – | Real-time |
| Hóa đơn GTGT đầu vào | – | Real-time |

## 5. Use cases

### UC-38: Lập tờ khai 01/GTGT tháng

1. Báo cáo thuế → Tờ khai thuế 01/GTGT TT80
2. Chọn kỳ (tháng 06/2026)
3. Hệ thống:
   - **Bước 1**: Tính [21]-[27] từ bảng kê đầu ra
     - Lọc sales_invoice trong kỳ
     - Nhóm theo tax_rate, tính tổng
   - **Bước 2**: Tính [28]-[29] từ bảng kê đầu vào
     - Lọc purchase_invoice trong kỳ
     - Nhóm theo tax_rate, tính tổng
   - **Bước 3**: Tính [40]-[45]
     - [40] = [22] = tổng VAT output
     - [41] = [29] = tổng VAT input (nếu dương)
     - [45] = [40] - [41] - [42] (phải nộp)
   - **Bước 4**: Tính [42], [60] — số dư VAT chuyển kỳ sau
4. Hiển thị theo mẫu 01/GTGT
5. Xuất XML/Excel (theo định dạng TCT yêu cầu)

### UC-39: Lập bảng kê đầu ra (01-1/GTGT)

1. Báo cáo thuế → Bảng kê đầu ra
2. Chọn kỳ
3. Hệ thống:
   - Lấy tất cả sales_invoice có VAT > 0 trong kỳ
   - Sắp xếp theo tax_rate (0%, 5%, 8%, 10%, không chịu thuế)
   - Render theo mẫu 01-1/GTGT
4. Cho phép user đánh dấu "loại trừ" một số hóa đơn nếu cần

### UC-40: Xuất XML nộp thuế điện tử

Tích hợp với cổng nộp thuế điện tử (thuedientu.gdt.gov.vn):

1. Sau khi lập tờ khai 01/GTGT
2. Click "Xuất XML cho nộp thuế điện tử"
3. Hệ thống:
   - Tạo XML theo schema của TCT
   - Ký số bằng chứng thư số của công ty
   - Download file XML
4. User upload XML lên cổng nộp thuế

## 6. Đặc tả bảng

**`vat_return`** (Tờ khai GTGT):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| return_period | CHAR(7) | '2026-06' |
| return_type | ENUM | monthly, quarterly |
| vat_output_total | DECIMAL(20,4) | [22] |
| vat_input_total | DECIMAL(20,4) | [29] |
| vat_opening_credit | DECIMAL(20,4) | [42] - từ kỳ trước |
| vat_payable | DECIMAL(20,4) | [45] |
| vat_credit_carry_forward | DECIMAL(20,4) | [60] |
| detail_json | JSON | Chi tiết theo tax_rate |
| generated_at | DATETIME | |
| generated_by | BIGINT FK | |
| xml_file_path | VARCHAR(500) | |

**`vat_breakdown_by_rate`** (Phân tích VAT theo thuế suất):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| vat_return_id | BIGINT FK | |
| direction | ENUM | output, input |
| vat_rate | DECIMAL(6,4) | 0, 5, 8, 10, -1 (KT) |
| base_amount | DECIMAL(20,4) | Doanh thu / chi phí |
| vat_amount | DECIMAL(20,4) | VAT |

## 7. Validation rules

- Tổng [22] = [25]+[26]+[27]
- [45] = [40] - [41] - [42] (nếu dương); [60] = -[45] (nếu âm)
- Mỗi hóa đơn chỉ được kê khai 1 lần trong kỳ
- Hóa đơn đầu vào phải từ nhà cung cấp có MST hợp lệ (để TCT xác nhận)
- Ngày hóa đơn phải nằm trong kỳ kê khai (trừ HĐ điều chỉnh, HĐ thay thế)

## 8. Phân quyền

- `tax.return.view`, `.generate`
- `tax.return.export_xml`
- `tax.input_invoice.view`, `.match`
- `tax.report.view`

---

**Tiếp theo**: [13. Hệ thống](./13-he-thong.md)
