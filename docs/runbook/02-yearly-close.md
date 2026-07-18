# R2 — Chốt sổ cuối năm & BCTC

> Quy trình chốt sổ cuối năm, lập BCTC năm, nộp CQT.

## Tổng quan

Cuối năm fiscal (thường 31/12), cần:

1. Chốt sổ kỳ 12 (xem [R1-monthly-close](01-monthly-close.md))
2. KC năm (N5xx/C911, N911/C6xx, N911/C421)
3. Lập BCTC năm (B01-DN, B02-DN, B03-DN)
4. Quyết toán năm (thuế TNDN, TNCN)
5. Nộp CQT trước 31/03 năm sau

## Timeline

| Ngày | Hạng mục |
|------|----------|
| 31/12 | Cắt số liệu năm |
| 1-15/01 | Chốt sổ kỳ 12 + KC năm |
| 15-31/01 | Lập BCTC draft |
| 1-15/02 | Audit nội bộ + KTT review |
| 15-28/02 | Nộp BCTC + quyết toán thuế (nếu có audit) |
| ≤ 31/03 | Deadline nộp TNDN năm |
| ≤ 30/01 | Nộp BHXH năm (BHXH quyết toán) |

## Quy trình chi tiết

### 1. Cắt số liệu 31/12

Tất cả nghiệp vụ năm phải phản ánh vào phiếu có `voucher_date ≤ 31/12`:

- Hóa đơn bán: phải phát hành ≤ 31/12 (nếu KH nhận hàng trong năm)
- Hóa đơn mua: phải nhập ≤ 31/12 (nếu nhận hàng trong năm)
- Chi phí: phải có hóa đơn + phiếu chi ≤ 31/12
- Lương: phải tính kỳ 12 (PayrollRun)
- Khấu hao TSCĐ: kỳ 12 (DepreciationRun)
- Phân bổ 242: kỳ 12
- CCDC 2421/142: phân bổ kỳ 12

> ⚠ **Quan trọng**: Nghiệp vụ không có chứng từ năm → chuyển sang kỳ 1 năm sau.

### 2. Chốt sổ kỳ 12

Xem [R1-monthly-close](01-monthly-close.md). Đảm bảo:
- BCĐTK kỳ 12 cân
- KC kỳ 12 đã chạy

### 3. Khấu hao + CCDC phân bổ cả năm

Verify:
- Tất cả TSCĐ có KH đủ 12 kỳ
- Tất cả CCDC có phân bổ đủ 12 kỳ
- Đối chiếu N642/C211, N642/C242

### 4. Định giá lại ngoại tệ cuối năm

**Bắt buộc** theo TT200/2014 — cuối năm phải định giá lại số dư ngoại tệ:

```
/modern/fx/revaluation/run/
  - year=2026
  - month=12
```

Hệ thống tự:
- Lấy tỷ giá VCB ngày 31/12
- Tính lại số dư các TK 1112, 1122, 131, 331 (foreign)
- Hạch toán chênh lệch: N635 (lỗ) hoặc N5151/C... (lãi)

### 5. Kiểm kê kho

Tổ chức kiểm kê vật lý:
- Tồn kho thực tế vs sổ sách
- Phát hiện chênh lệch → điều chỉnh:
  - Thiếu: N632 / C155, C156
  - Thừa: N155, N156 / C711

### 6. Lập dự phòng

#### Dự phòng nợ khó đòi (N2293/C2293)

Cho KH quá hạn > 6 tháng:

```python
# Tính per customer
debt_amount × percent_by_aging:
  - 6-12 months: 30%
  - 12-18 months: 50%
  - 18-24 months: 70%
  - > 24 months: 100%
```

Hạch toán: N642 / C2293

#### Dự phòng giảm giá hàng tồn kho

Nếu giá thị < giá sổ sách: N632 / C2293

#### Dự phòng giảm giá TSCĐ

Seldom cho SME. Theo TT200: N642 / C2293.

### 7. KC năm (KC06 - kết chuyển năm)

```
/modern/closing/?type=yearly&year=2026
```

Tự động:
- **KC doanh thu**: N5111, N5112 / C911
- **KC chi phí**:
  - N911 / C632 (giá vốn)
  - N911 / C641 (CP bán hàng)
  - N911 / C642 (CP QLDN)
  - N911 / C635 (CP tài chính)
  - N911 / C821 (CP TNDN)
- **Xác định KQKD**:
  - Lãi: N911 / C421
  - Lỗ: N421 / C911

### 8. Lập BCTC năm

#### B01-DN — Bảng CĐTK

```
/modern/reports/balance-sheet/?year=2026&period=12
```

Download PDF. Verify:
- Tài sản = Nguồn vốn (cân đối)
- TK có số dư kỳ đầu = TK có số dư kỳ cuối của năm trước

#### B02-DN — KQ HĐKD

```
/modern/reports/pnl/?year=2026&period=12
```

#### B03-DN — Lưu chuyển tiền tệ

(chưa có — làm thủ công qua Excel)

#### Thuyết minh BCTC

(chưa có template — làm thủ công)

### 9. Quyết toán thuế TNDN năm

```
TNDN phải nộp = (Doanh thu - Chi phí hợp lý) × 20% (SME có thể 15%)
```

Hạch toán:
- Tính số TNDN phải nộp: N8211 / C3334
- Nộp: N3334 / C112

Submit form **03/TNDN** qua thuedientu.gdt.gov.vn trước **31/03 năm sau**.

### 10. Quyết toán PIT năm

Trước **31/03 năm sau**:

Xem [R6-payroll-bhxh-flow](06-payroll-bhxh-flow.md) section Quyết toán.

Submit form **05/CK-TNCN** (chứa tổng hợp PIT từng NV).

### 11. Nộp BHXH quyết toán năm

Trước **31/01 năm sau**:
- Tổng quỹ lương năm
- Tổng BHXH đã nộp
- Điều chỉnh (nếu chênh lệch do tăng/giảm NV)

Submit qua **vss.gov.vn** (BHXH điện tử).

### 12. Khóa năm

Sau khi tất cả báo cáo đã nộp:

1. Set tất cả voucher năm = `locked`
2. Set kỳ 1-12 = `period_locked`
3. Notification cho toàn bộ user: không được sửa năm cũ

```python
# Bulk lock (admin only)
from apps.ledger.models import AccountingVoucher
vouchers = AccountingVoucher.objects.filter(
    company=..., fiscal_year=2026, status='ledger_posted'
)
vouchers.update(is_locked=True)
```

> ⚠ Sau khi lock, không thể unlock (audit trail). Hành động nghiêm túc —
> chỉ làm sau khi:
> - Tất cả báo cáo đã nộp CQT
> - KTT đã ký duyệt
> - Đã backup full DB

### 13. Lập năm mới

Tạo kỳ 1 năm sau:

```bash
# Reset các số thứ tự
python manage.py reset_sequences --year=2027
```

## Báo cáo gửi CQT

| Báo cáo | Form | Deadline |
|---------|------|----------|
| Tờ khai TNDN năm | 03/TNDN | 31/03 năm sau |
| BCTC năm | B01+B02+B03+Thuyết minh | 31/03 năm sau (DN lớn), 31/01 (SME) |
| Quyết toán PIT | 05/CK-TNCN | 31/03 năm sau |
| Quyết toán BHXH | BHXH form | 31/01 năm sau |
| BC HĐĐT năm | BC26 (quý) | 20/1, 20/4, 20/7, 20/10 |

## Checklist cuối năm

- [ ] Cắt số liệu 31/12
- [ ] Chốt kỳ 12
- [ ] Khấu hao + CCDC cả năm
- [ ] FX revaluation
- [ ] Kiểm kê kho
- [ ] Dự phòng nợ khó đòi
- [ ] Dự phòng giảm giá HTK
- [ ] KC năm
- [ ] B01-DN, B02-DN
- [ ] Quyết toán TNDN (03/TNDN)
- [ ] Quyết toán PIT (05/CK-TNCN)
- [ ] BHXH quyết toán
- [ ] Khóa năm (lock vouchers)
- [ ] Lập kỳ 1 năm sau

## FAQ

**Q: Khi nào làm chốt năm?**
A: Thường 15-31/01 năm sau. CQT deadline:
- 31/03: TNDN + PIT quyết toán
- 31/01: BHXH + BCTC SME

**Q: Phát hiện sai năm cũ sau khi khóa?**
A: Tạo phiếu điều chỉnh kỳ 1 năm sau. KHÔNG sửa năm đã khóa.

**Q: BCTC cần audit không?**
A: DN lớn (vốn > 20 tỷ, > 100 cổ đông) → bắt buộc. SME → không bắt buộc nhưng
nên có internal audit.

**Q: Phải nộp BCTC bằng tiếng Anh không?**
A: Không. Tiếng Việt theo mẫu chuẩn.

**Q: Kỳ 13 (sau cutoff) là gì?**
A: Một số công ty dùng kỳ 13 cho điều chỉnh cuối năm. Visota ERP không dùng —
chỉ 12 kỳ/năm.

---

Tài liệu liên quan:
- [R1-monthly-close](01-monthly-close.md) — Chốt tháng
- [R3-vat-filing](03-vat-filing.md) — VAT hàng tháng
- [16-fx](../user-guide/16-fx.md) — Định giá ngoại tệ
- [T1-architecture](../technical/01-architecture.md) — KC technical
