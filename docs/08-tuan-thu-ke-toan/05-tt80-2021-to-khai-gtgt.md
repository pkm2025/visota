# 05. Tờ khai thuế GTGT 01/GTGT theo Thông tư 80/2021

> Mẫu tờ khai thuế GTGT và bảng kê hóa đơn đầu ra/đầu vào.

## 1. Thông tư 80/2021/TT-BTC

| Thông tin | Giá trị |
|----------|--------|
| Số văn bản | 80/2021/TT-BTC |
| Ngày ban hành | 04/10/2021 |
| Ngày hiệu lực | 01/01/2022 |
| Cơ quan | Bộ Tài chính |
| Nội dung | Ban hành mẫu tờ khai thuế |

## 2. Tờ khai 01/GTGT (Phụ lục II TT80)

### 2.1. Header

```
[01] Tên người nộp thuế: .............................................
[02] Mã số thuế: ....................................................
[03] Địa chỉ trụ sở: ................................................
[04] Quận/Huyện: ....................................................
[05] Tỉnh/Thành phố: ................................................
[06] Điện thoại: .....................................................
[07] Fax: ............................................................
[08] Email: ..........................................................
[09] Loại tờ khai: ☐ Mới   ☐ Bổ sung lần: ......
[10] Kỳ tính thuế: ☐ Tháng   ☐ Quý   ☐ Năm
     Từ ngày: ...... / ...... / ......
     Đến ngày: ...... / ...... / ......
[11] ☐ Lần đầu   [12] ☐ Đầu năm
[13] Doanh thu: .....................................................
```

### 2.2. Phần I - Hàng hóa dịch vụ chịu thuế GTGT

```
[21] Giá trị HH, DV bán ra chịu thuế GTGT: ..........................
[22] Thuế GTGT của HH, DV bán ra chịu thuế (24+25+26+27): ...........
[23] Giá trị HH, DV bán ra KHÔNG chịu thuế GTGT: ....................
[24] HH, DV chịu thuế suất 0%: ......................................
[25] HH, DV chịu thuế suất 5%: ......................................
[26] HH, DV chịu thuế suất 8%: ......................................
[27] HH, DV chịu thuế suất 10%: .....................................
```

### 2.3. Phần II - Hàng hóa dịch vụ mua vào

```
[28] Giá trị HH, DV mua vào còn được khấu trừ (31+32+33+34): .......
[29] Thuế GTGT của HH, DV mua vào được khấu trừ: ...................
[30] HH, DV mua vào không được khấu trừ: ...........................
[31] HH, DV mua vào chịu thuế suất 5%: ..............................
[32] HH, DV mua vào chịu thuế suất 8%: ..............................
[33] HH, DV mua vào chịu thuế suất 10%: .............................
[34] TST được khấu trừ năm trước chuyển sang: ......................
```

### 2.4. Phần III - Thuế GTGT phải nộp

```
[40] Số thuế GTGT của HH, DV bán ra (= [22]): ......................
[41] Số thuế GTGT được khấu trừ trong kỳ (= [29]): .................
[42] Số thuế GTGT được khấu trừ kỳ trước chuyển sang: .............
[43] Số thuế GTGT của HH, DV bán ra trong kỳ kéo dài: .............
[44] Số thuế GTGT còn được khấu trừ của HH, DV mua vào trong KD: ...
[45] Số thuế GTGT phải nộp trong kỳ ([40]-[41]-[42]): ..............
[46] Số thuế GTGT phải nộp của kỳ KD dài (> 3 tháng): ..............
```

### 2.5. Phần IV - Hoàn thuế

```
[50] Số thuế GTGT đề nghị hoàn: ....................................
```

### 2.6. Phần V - Chuyển kỳ sau

```
[60] Số thuế GTGT đề nghị chuyển kỳ sau: ...........................
```

## 3. Bảng kê đầu ra 01-1/GTGT

```
BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ BÁN RA

STT | Ký hiệu mẫu | Ký hiệu HĐ | Số HĐ | Ngày phát hành | Tên người mua | MST người mua | Loại HĐ | Tên HH-DV | Giá trị chưa thuế | Thuế suất | Tiền thuế GTGT
----|-------------|------------|-------|----------------|---------------|---------------|---------|-----------|-------------------|-----------|--------------
1   | 1C25TPE     | AA/25E     | 0001  | 05/06/2026     | Cty ABC       | 0101234567    | GTGT    | Hàng hóa  | 100.000.000       | 10%       | 10.000.000
2   | 1C25TPE     | AA/25E     | 0002  | 10/06/2026     | Cty XYZ       | 0307654321    | GTGT    | Dịch vụ   | 50.000.000        | 10%       | 5.000.000

TỔNG CỘN giá trị chưa thuế: ...
TỔNG CỘN thuế GTGT: ...

Phân loại theo thuế suất:
  Chịu thuế suất 0%: ...
  Chịu thuế suất 5%: ...
  Chịu thuế suất 8%: ...
  Chịu thuế suất 10%: ...
  Không chịu thuế GTGT: ...
```

## 4. Bảng kê đầu vào 01-2/GTGT

Tương tự 01-1 nhưng cho HHDV mua vào, có thêm cột:
- "Không được khấu trừ" (nếu có)
- "HĐ không hợp lệ"

## 5. Kỳ kê khai

### 5.1. Theo tháng

Áp dụng khi: doanh thu năm trước **< 50 tỷ VND** (theo Điều 12 TT80).

### 5.2. Theo quý

Áp dụng khi: doanh thu năm trước **≥ 50 tỷ VND**.

### 5.3. Hạn nộp

| Kỳ tính thuế | Hạn nộp |
|--------------|--------|
| Tháng | Ngày 20 của tháng sau |
| Quý | Ngày 30 hoặc 31 của tháng đầu quý sau |

## 6. Công thức tính

### 6.1. Thuế GTGT đầu ra

```python
vat_output = (
    sales_invoices
    .filter(in_period=period, has_vat=True)
    .aggregate(
        total_vat=Sum('vat_amount'),
        total_amount_before_vat=Sum('subtotal'),
    )
)
```

### 6.2. Thuế GTGT đầu vào được khấu trừ

```python
vat_input_credit = (
    purchase_invoices
    .filter(in_period=period, has_vat=True, is_credit=True)
    .aggregate(total_vat=Sum('vat_amount'))
)
```

**Điều kiện được khấu trừ**:
- Hóa đơn hợp lệ (đã phát hành HĐĐT hoặc HĐ giấy trước 01/07/2022)
- HHDV sử dụng cho SXKD chịu thuế GTGT
- Có chứng từ nộp thuế NK (cho HHNK)
- Đăng ký kịp thời (trong kỳ)

### 6.3. Thuế GTGT phải nộp

```python
def calculate_vat_payable(company, period):
    vat_output = get_vat_output(company, period)
    vat_input_credit = get_vat_input_credit(company, period)
    vat_opening_credit = get_opening_credit(company, period)  # từ kỳ trước
    
    vat_payable = vat_output - vat_input_credit - vat_opening_credit
    
    if vat_payable > 0:
        # Phải nộp
        return {'status': 'payable', 'amount': vat_payable, 'carry_forward': 0}
    else:
        # Được khấu trừ, chuyển kỳ sau hoặc hoàn thuế
        return {
            'status': 'credit',
            'amount': vat_output,
            'carry_forward': -vat_payable  # số âm
        }
```

## 7. XML cho nộp thuế điện tử

Cổng nộp thuế điện tử (thuedientu.gdt.gov.vn) chấp nhận XML theo schema:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<HKinhTe>
    <TTinChung>
        <TTinDVu>
            <maDVu>01</maDVu>
            <tenDVu>Tờ khai thuế GTGT</tenDVu>
            <pbanDVu>1.0.0</pbanDVu>
            <ttinNhaCCap> string </ttinNhaCCap>
        </TTinDVu>
        <TTinTKhaiThue>
            <TKhaiThue>
                <maTKhai>01</maTKhai>
                <tenTKhai>Tờ khai thuế GTGT</tenTKhai>
                <moTaBMieu/>
                <kyLapBC>06/2026</kyLapBC>
                <loaiKy>B</loaiKy>
            </TKhaiThue>
            <NNT>
                <mst>0101234567</mst>
                <tenNNT>Công ty ABC</tenNNT>
                <dchiNNT>Số 1 Đường A, Hà Nội</dchiNNT>
            </NNT>
            <DLyThue>...</DLyThue>
        </TTinTKhaiThue>
    </TTinChung>
    <CTieuTKhaiChinh>
        <HangHoaDVBanRa>
            <!-- Bảng kê đầu ra -->
        </HangHoaDVBanRa>
        <HangHoaDVMuaVao>
            <!-- Bảng kê đầu vào -->
        </HangHoaDVMuaVao>
        <ThueGTGTPHaiNop>
            <ct40>...</ct40>
            <ct41>...</ct41>
            <ct42>...</ct42>
            <ct45>...</ct45>
        </ThueGTGTPHaiNop>
    </CTieuTKhaiChinh>
</HKinhTe>
```

Phần mềm PMKetoan cần:
- Sinh XML theo schema trên
- Ký số (XML Signature)
- Export file .xml để user upload

## 8. Quy trình lập tờ khai hàng tháng/quý

```
Ngày 1-15 của kỳ sau:
1. Kiểm tra tất cả HĐ đầu ra đã phát hành → đảm bảo đầy đủ
2. Pull HĐ đầu vào từ TCT → match với phiếu nhập mua
3. Verify tất cả HĐ đầu vào được khấu trừ
4. Lập tờ khai 01/GTGT
5. Review chi tiết:
   - [21]-[27]: đầu ra theo thuế suất
   - [28]-[34]: đầu vào theo thuế suất
   - [40]-[45]: tính toán phải nộp
6. Sinh XML
7. Upload lên cổng thuế điện tử
8. Nộp tiền (nếu [45] > 0)

Ngày 20 (tháng) / 30-31 (quý):
- Hạn chót nộp
```

## 9. Validation rules

- Tổng [22] = [24]+[25]+[26]+[27] (đầu ra)
- Tổng [29] = [31]+[32]+[33] (đầu vào, trừ [34] chuyển kỳ)
- [45] = max(0, [40] - [41] - [42])
- [60] = max(0, [41] + [42] - [40]) (chuyển kỳ sau)
- Mỗi HĐ chỉ kê khai 1 lần

## 10. Báo cáo liên quan

| Mẫu | Tên | Khi nào dùng |
|-----|-----|--------------|
| 01/GTGT | Tờ khai thuế GTGT | Hàng tháng/quý |
| 01-1/GTGT | Bảng kê đầu ra | Kèm 01/GTGT |
| 01-2/GTGT | Bảng kê đầu vào | Kèm 01/GTGT |
| 01-3/GTGT | Bảng kê HH-DV xuất nhập khẩu | Có XNK |
| 01-5/GTGT | Bảng tổng hợp HĐ bán ra/bán sự cố | Có nghiệp vụ đặc thù |
| 03/TNDN | Tờ khai quyết toán TNDN | Năm |

## 11. Nguồn tham khảo

- 🔗 [TT80/2021/TT-BTC](https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-80-2021-TT-BTC-ban-hanh-mau-to-khai-thue-502620.aspx)
- 🔗 [Hướng dẫn lập 01/GTGT theo TT80/2021](https://www.meinvoice.vn/tin-tuc/14642/lap-to-khai-thue-gtgt-mau-01/)
- 🔗 [Tổng cục Thuế hướng dẫn lập tờ khai 01/GTGT](https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tong-cuc-thue-huong-dan-lap-mau-to-khai-thue-gtgt-thang-va-quy-theo-mau-so-01gtgt-nam-2023-nhu-the--83183.html)
- 🔗 [Mẫu 01-1/GTGT - Bảng kê đầu ra](http://www.ketoanthue.vn/index.php/khai-thue-gtgt-mau-khai-thue-gia-tri-gia-tang/2390-mau-so-01-1-gtgt-bang-ke-hoa-don-chung-tu-hang-hoa-dich-vu-ban-ra.html)
- 🔗 [Hướng dẫn lập bảng kê đầu vào 01-2/GTGT](https://ketoanthienung.net/cach-lap-bang-ke-hang-hoa-dich-vu-mua-vao-pl-01-2-gtgt.htm)

---

**Tiếp theo**: [06. Luật Kế toán 2015](./06-luat-ke-toan-2015.md)
