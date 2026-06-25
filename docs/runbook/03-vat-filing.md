# R3 — Kê khai & Nộp thuế GTGT hàng tháng

> Quy trình kê khai VAT kỳ theo TT80/2021. Deadline: ngày 20 tháng sau.

## Tổng quan

Thuế GTGT (VAT) kê khai theo **phương pháp khấu trừ** hàng tháng.

```
VAT phải nộp = VAT đầu ra (thu được) − VAT đầu vào (chi trả)
            = (Cr 33311) − (Dr 1331)
```

## Điều kiện tiên quyết

- [ ] Tất cả HĐ bán trong tháng đã post → VAT đầu ra (33311 credit)
- [ ] Tất cả HĐ mua trong tháng đã post → VAT đầu vào (1331 debit)
- [ ] HĐĐT đã phát hành cho mọi HĐ bán
- [ ] Đã nhập HĐ mua từ NCC (input_docs)
- [ ] Kỳ kế toán đã chốt

## Quy trình

### 1. Tạo tờ khai VAT 01/GTGT

Sidebar → **Báo cáo & Thuế → Tờ khai GTGT (01)**

Hoặc URL: `/modern/reports/vat-return/?year=2026&month=6`

Hệ thống tự tính:

**Phần I — Kê khai VAT đầu ra (Cr 33311)**:

| Mục | VAT rate | Doanh thu | VAT |
|-----|----------|-----------|-----|
| 1.1 | 0% | — | — |
| 1.2 | 5% | (nếu có) | ... |
| 1.3 | 8% (ND 174/2025) | 800M | 64M |
| 1.4 | 10% | 400M | 40M |
| 1.5 | Không chịu VAT | — | — |

**Phần II — Kê khai VAT đầu vào (Dr 1331)**:

| Mục | VAT |
|-----|-----|
| 2.1 HHDV mua trong kỳ | 38M |
| 2.2 CCDC mua | — |
| 2.3 Khấu trừ còn được kỳ trước | — |

**Phần III — Kết quả**:

```
VAT phải nộp = 104M (output) − 38M (input) = 66M
```

### 2. Verify chi tiết

Download Excel → check:

**VAT đầu ra** (BC thuế đầu ra):
- List HĐ bán (SalesInvoice `status=ledger`)
- Tổng theo VAT rate
- Tổng VAT 33311

**VAT đầu vào** (BC thuế đầu vào):
- List HĐ mua (PurchaseInvoice `status=ledger`)
- Phải có HĐ đầu vào hợp lệ (HĐ giấy + HĐĐT)
- Tổng VAT 1331

**Match với BCĐTK**:
- TK 33311 Cr period = VAT output BC
- TK 1331 Dr period = VAT input BC

### 3. HĐĐT đã báo cáo CQT

Phải đảm bảo:
- Tất cả HĐĐT kỳ phát hành → vào BC01 kỳ đó
- BC01 đã nộp CQT qua muasamcong.mpi.gov.vn

Nếu BC01 kỳ chưa nộp → VAT đầu ra sai.

### 4. Submit CQT

#### Bước 1: Nộp qua Thuế điện tử

Đăng nhập **thuedientu.gdt.gov.vn**:

1. Chọn tờ khai 01/GTGT kỳ
2. Nhập số liệu từ PMKetoan:
   - Doanh thu theo VAT rate
   - VAT đầu ra
   - VAT đầu vào
   - VAT phải nộp
3. Upload BC thuế đầu vào + đầu ra (Excel từ PMKetoan)
4. Ký số (USB token hoặc SIM số)
5. Submit → nhận Mã CQT

#### Bước 2: Thanh toán

Lệnh chuyển khoản:
- Beneficiary: Cục Thuế <tỉnh>
- Bank: Kho bạc Nhà nước
- Amount: VAT phải nộp
- Nội dung: "Nộp VAT tháng 06/2026 - MST 0101218690"

Sau khi CK → giữ hóa đơn/biên lai → upload vào attachment.

#### Bước 3: Hạch toán nộp

Tạo CashPayment:

```
Dr 33311 (VAT đầu ra phải nộp) ... 66M
   Cr 1121 (Bank) ................. 66M
```

Note: "Nộp VAT T06/2026, mã CQT xxx".

### 5. Lưu trữ

```
/var/lib/pmketoan/tax/2026-06-vat/
├── 01-GTGT-2026-06.pdf       (Tờ khai đã nộp)
├── input-invoices.xlsx       (BC thuế đầu vào)
├── output-invoices.xlsx      (BC thuế đầu ra)
├── payment-receipt.pdf       (Biên lai CK)
└── notes.md                  (Ghi chú)
```

Lưu ≥ 10 năm per Luật KT.

## Edge cases

### VAT âm (đầu vào > đầu ra)

Được **khoán chuyển kỳ sau** hoặc **hoàn thuế**.

**Khoán chuyển kỳ sau** (mặc định):
- Kỳ sau: VAT phải nộp = (Output - Input) - Khấu trừ kỳ trước
- BC trong tờ khai kỳ sau

**Hoàn thuế** (cho DN xuất khẩu, dự án đầu tư):
- Nộp đơn hoàn thuế (form 01/HTBT)
- Cục Thuế kiểm tra → hoàn trong 6-30 ngày

### Khách hàng return hàng

Sau khi đã kê khai VAT kỳ trước:
- Tạo HĐ điều chỉnh (âm) kỳ hiện tại
- Trừ vào VAT đầu ra kỳ hiện tại
- Báo trong tờ khai "HĐ bị hủy/bán bị trả lại"

### HĐ của kỳ trước phát hiện sai

Không sửa kỳ trước (đã khóa). Cách:
- Tạo bút toán điều chỉnh kỳ hiện tại
- Báo "Điều chỉnh tăng/giảm" trong tờ khai kỳ hiện tại

### Mua sắm CCDC (> 20M)

Nếu VAT đầu vào của CCDC > 20M → kê khai theo 12KK (kỳ >= 200M).

Hiện PMKetoan chưa auto split — làm thủ công.

## Tỷ giá áp dụng VAT

Nếu HĐ ngoại tệ:
- Quy đổi VND theo tỷ giá VCB ngày phát sinh HĐ
- Hạch toán bằng VND
- VAT tính trên VND

## Deadline

| Hạng mục | Deadline |
|----------|----------|
| Kê khai VAT | Ngày 20 tháng sau |
| Nộp tiền | Ngày 20 tháng sau |
| BC HĐĐT (BC01) | Ngày 20 tháng sau |
| Kê khai năm (nếu khuyến khích) | Ngày 31/01 năm sau |

Trễ phạt:
- < 1 ngày: nhắc nhở
- 1-90 ngày: phạt 0.03%/ngày × số tiền
- > 90 ngày: phạt nặng + LST

## Checklist

- [ ] Tất cả HĐ bán post
- [ ] Tất cả HĐ mua post + có HĐ hợp lệ
- [ ] HĐĐT đã phát hành
- [ ] BC01 đã nộp
- [ ] Tờ khai 01/GTGT tạo từ PMKetoan
- [ ] Verify số liệu match BCĐTK
- [ ] Submit thuedientu.gdt.gov.vn
- [ ] Thanh toán KBNN
- [ ] Hạch toán nộp (N33311/C1121)
- [ ] Lưu trữ tờ khai ≥ 10 năm

---

Tài liệu liên quan:
- [10-einvoice](../user-guide/10-einvoice.md) — HĐĐT (BC01)
- [R1-monthly-close](01-monthly-close.md) — Chốt sổ tháng
- [02-sales](../user-guide/02-sales.md) — SalesInvoice → VAT output
- [03-purchasing](../user-guide/03-purchasing.md) — PurchaseInvoice → VAT input
