# 06 — Nhân sự & Tính lương

> Nhân viên, HĐLĐ, BHXH, phép năm, bảng lương, PIT.

## 1. Nhân viên

Sidebar → **Nhân sự → Nhân viên**

### Tạo nhân viên

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| Mã NV (`code`) | ✓ | VD: `EMP001` |
| Họ tên | ✓ | |
| Ngày sinh | | DD/MM/YYYY |
| Giới tính | | Nam/Nữ/Khác |
| CCCD | | Số CMND/CCCD |
| Ngày cấp + Nơi cấp | | |
| MST cá nhân | | Mã số thuế TNCN |
| Số BHXH | | |
| Điện thoại / Email | | |
| Địa chỉ | | |
| Phòng ban | | FK |
| Chức danh | | FK Position |
| Ngày vào | ✓ | Hire date |
| Trạng thái | | `probation`/`active`/`maternity`/`resigned` |

### HĐ lao động

Mỗi nhân viên có 1+ HĐ lao động (`LaborContract`):
- Loại: `probation` (thử việc) / `indefinite` (không xác định thời hạn) /
  `fixed` (xác định thời hạn)
- Ngày bắt đầu / kết thúc
- Lương cơ bản (`base_salary`)
- Lương đóng BHXH (`insurance_salary_base`)
- Phụ cấp

## 2. BHXH & BHYT

### Tỷ lệ đóng (2026)

| Thành phần | NLĐ (%) | NSDLĐ (%) | Tổng |
|------------|---------|-----------|------|
| BHXH (hưu/trí tuệ) | 8.0 | 14.0 | 22.0 |
| BHYT | 1.5 | 3.0 | 4.5 |
| BHTN | 1.0 | 1.0 | 2.0 |
| BHTNLD-BNN | — | 0.5 | 0.5 |
| **Tổng** | **10.5** | **18.5** | **29.0** |
| Kinh phí công đoàn | — | 2.0 | 2.0 |

### Cấu hình

Sidebar → **Nhân sự → BHXH** để xem:
- Tổng quỹ lương tháng
- Số phải đóng BHXH (NLĐ + NSDLĐ)
- BC D62 (PDF để nộp cho cơ quan BHXH)

## 3. Phép năm & Nghỉ phép

Sidebar → **Nhân sự → Nghỉ phép**

### Xin nghỉ

1. Bấm **"+ Tạo đơn nghỉ"**
2. Chọn loại: `annual` (phép năm) / `sick` (ốm) / `unpaid` (không lương) /
   `maternity` (thai sản) / `wedding` / `funeral`
3. Từ ngày → đến ngày
4. Lý do
5. Submit → cần Trưởng phòng duyệt

### Dự phòng phép

12 ngày phép năm / năm (theo LĐ 2012). Nếu > 5 năm = +1 ngày/năm.

## 4. Người phụ thuộc (cho giảm trừ gia cảnh)

Sidebar → **Nhân sự → Người phụ thuộc`

Mỗi nhân viên có thể đăng ký tối đa N NPT (không giới hạn từ 2024):
- Vợ/chồng không có thu nhập
- Con < 18 tuổi (hoặc < 22 tuổi đang học CĐ/ĐH)
- Cha mẹ > tuổi nghỉ hưu

Mỗi NPT giảm trừ **4.4 triệu/tháng** (đang chờ Luật 09/2026/QH16 tăng lên).

## 5. Tính lương hàng tháng

Sidebar → **Nhân sự → Tính lương** (PayrollRun)

### Quy trình

1. Chọn kỳ (tháng/năm)
2. Hệ thống tự tính cho từng NV active:
   - **Lương gross** = base_salary + phụ cấp
   - **Giảm trừ gia cảnh**:
     - Bản thân: 13.2 triệu (eff. 01/07/2026)
     - Mỗi NPT: 5.2 triệu
   - **Thu nhập chịu thuế** = gross − BHXH(NLĐ 10.5%) − giảm trừ
   - **PIT** theo 7 bậc lũy tiến (0→35%)
   - **Net** = gross − BHXH(NLĐ) − PIT
3. Bấm **"Tính lương kỳ"** → tạo `PayrollRun`
4. PayrollRun tự sinh voucher:
   - N6221 (CP lương) / N334 (Phải trả NLĐ)
   - N338 (CP khác-KPCĐ 2%)
   - N3335 (Phải trả BHXH)
   - N3334 (TNCN)
   - C111/C112 (thanh toán net)

### Bảng lương

Mỗi PayrollRun có nhiều `PayrollLine` — chi tiết theo NV:
- Họ tên, MST
- Gross, BHXH, GTGT, PIT, Net
- Ngày công

Export Excel để phát lương qua bank.

## 6. Thuế TNCN

### Khấu trừ tại nguồn (hàng tháng)

Tự động trong PayrollRun.

### Quyết toán năm

Năm sau (trước 31/03) thực hiện:
1. List PayrollRun trong năm
2. Tổng hợp thu nhập/PIT từng NV
3. Tạo **BC TNCN năm** để gửi CQT (form 05/CK-TNCN)
4. NV có MST > 1 nguồn thu → quyết toán cá nhân

## 7. Thai sản / Ốm đau

- Tạo `LeaveRecord` loại `maternity` hoặc `sick`
- Hệ thống auto-tính trợ cấp BHXH (theo mức đóng BHXH của 6 tháng trước)
- Voucher: N334 / C111 (trợ cấp từ BHXH)

## 8. Báo cáo nhân sự

| Báo cáo | Đường dẫn |
|---------|-----------|
| D62 (BHXH) | Báo cáo → D62 |
| BC sử dụng lao động | Báo cáo → BC lao động |
| BC quỹ lương | Báo cáo → Quỹ lương |
| BC thuế TNCN | Báo cáo → TNCN |
| BC HĐLĐ | (PDF từ list) |

## 9. Workflow Payroll đầy đủ

```
LaborContract (HĐLĐ)
   ↓
Monthly timesheet (chưa có — nhập tay)
   ↓
PayrollRun (tính lương)
   ↓ auto-voucher
N6221 / N334 / N338 / N3335 / N3334 / C111
   ↓
Bank disbursement (export Excel)
   ↓
Báo cáo D62 → nộp BHXH
   ↓
Báo cáo TNCN → nộp CQT
```

Xem chi tiết: [R6-payroll-bhxh-flow](../runbook/06-payroll-bhxh-flow.md)

## FAQ

**Q: NV mới vào giữa tháng — tính lương sao?**
A: PayrollRun tự nhân `(ngày làm / ngày công chuẩn)` cho base_salary. Có thể
override trong `PayrollLine`.

**Q: NV nghỉ phép không lương — hạch toán?**
A: Tạo LeaveRecord `unpaid` → PayrollRun tự trừ ngày công.

**Q: Phụ cấp có chịu thuế TNCN không?**
A: Có, trừ phụ cấp ăn trưa (≤ 730k/tháng), điện thoại (≤ 500k), xăng xe (≤
200k) theo TT 111/2013.

**Q: Lương 13 — tính sao?**
A: Tạo PayrollRun riêng kỳ `12` với loại `bonus` — bút toán N6221 / C334.

**Q: NV nước ngoài — PIT khác không?**
A: Có. Phân loại Resident / Non-resident theo số ngày ở VN. Resident = lũy tiến,
non-resident = 20% toàn bộ. Liên hệ kế toán trưởng để config.

---

Tài liệu liên quan:
- [R4-pit-filing](../runbook/04-pit-filing.md) — Kê khai PIT hàng tháng
- [R6-payroll-bhxh-flow](../runbook/06-payroll-bhxh-flow.md) — Quy trình lương
