# R6 — Quy trình Tính lương & nộp BHXH hàng tháng

> Workflow tính lương, khấu trừ PIT, nộp BHXH, quyết toán.

## Sơ đồ tổng thể

```
[Update timesheet] (cập nhật ngày công)
        ↓
[Update phụ cấp / thưởng] (PayrollLine overrides)
        ↓
[Run PayrollRun] (tính lương kỳ)
        ↓ Auto-voucher N6221/N334/N3335/N3334/C111
[Review PayrollLine]
        ↓
[Export Excel → bank] (phát lương)
        ↓
[Generate BC D62] (BHXH)
        ↓ Nộp cơ quan BHXH
[Generate BC TNCN tháng]
        ↓ Lưu nội bộ
[Quyết toán năm] (năm sau 31/03)
```

## Bước chi tiết

### 1. Cập nhật dữ liệu đầu vào

Trước ngày tính lương (thường ngày 25-28 của tháng trước):

- **Ngày công**: cập nhật qua LeaveRecord (nghỉ phép, ốm, thai sản)
- **Phụ cấp / thưởng**: PayrollLine override nếu có
- **NV mới**: tạo Employee + LaborContract
- **NV nghỉ**: set Employee.status = `resigned` + LaborContract.end_date
- **Tăng lương**: update LaborContract.base_salary + effective_date

### 2. Tính lương kỳ

```
/modern/payroll/run/
  - Chọn kỳ (tháng/năm)
  - Bấm "Tính lương kỳ"
```

Hệ thống tự:
1. Lấy tất cả Employee `status=active`
2. Cho từng NV tính:
   ```
   gross = base_salary + allowances (các khoản chịu thuế)
   bhxh_employee = gross × 10.5%  (8% BHXH + 1.5% BHYT + 1% BHTN)
   pension_contrib = gross × 10.5%
   self_deduction = 13.2M (PIT 2026)
   dependents_deduction = num_dependents × 5.2M
   taxable_income = gross - bhxh_employee - self_deduction - dependents_deduction
   pit = progressive_brackets(taxable_income)  # 7 bậc
   net = gross - bhxh_employee - pit
   ```
3. Tạo `PayrollLine` per NV
4. Tạo `AccountingVoucher` tổng:
   - N6221 (CP lương) = total gross
   - N3335 (Phải trả BHXH) = total BHXH (10.5% NLĐ)
   - N3334 (TNCN) = total PIT
   - N338 (CP khác) = KPCĐ 2%
   - C334 (Phải trả NLĐ) = total net

### 3. Review PayrollLine

Vào detail PayrollRun → review từng dòng:
- Họ tên, MST, chức danh
- Gross, BHXH, GTGT, PIT, Net
- Số ngày công
- Ghi chú

**Nếu cần sửa**: Edit PayrollLine trực tiếp (gross, allowance, deduction) →
voucher sẽ tự update khi re-save PayrollRun.

### 4. Export Excel → Bank

Bấm **"Export Excel"** trong PayrollRun → file `payroll_2026_06.xlsx`:
- Sheet "Bank_upload": STK, STK NH, số tiền net, nội dung CK
- Sheet "Detail": breakdown per NV

Upload file Excel vào hệ thống bank (VCB iBanking, MBBank, ...) → batch transfer.

### 5. Generate BC D62 (BHXH)

```
/modern/reports/d62/?year=2026&month=6
```

Hoặc từ detail PayrollRun → bấm "BC D62"

Download PDF → nộp cơ quan BHXH **trước ngày cuối tháng**.

D62 bao gồm:
- Tổng quỹ lương tháng
- BHXH (NLĐ 10.5% + NSD 21.5%)
- BHYT (NLĐ 1.5% + NSD 3%)
- BHTN (NLĐ 1% + NSD 1%)
- BHTNLD-BNN (NSD 0.5%)
- KPCĐ (NSD 2%)

### 6. Generate BC TNCN tháng

```
/modern/reports/pit-monthly/?year=2026&month=6
```

Lưu nội bộ — không nộp CQT hàng tháng. Quyết toán năm mới nộp.

### 7. Thanh toán các khoản

Tạo CashPayment:
- **BHXH**: N3335 / C112 → nộp cơ quan BHXH
- **PIT** (năm): N3334 / C112 → nộp CQT
- **KPCĐ**: N338 / C112 → nộp công đoàn

### 8. Sau khi nhân viên nghỉ việc

Khi Employee.status = `resigned`:

1. Tính lương kỳ cuối:
   - Prorate theo ngày làm thực tế
   - Trợ cấp thôi việc (nếu có) — tạo PayrollLine riêng
2. **Quyết toán PIT** cho NV đó:
   - Tổng thu nhập năm
   - Tổng PIT đã khấu trừ
   - PIT còn phải nộp (hoặc hoàn)
3. Chốt BHXH: report giảm NV với cơ quan BHXH

## Quyết toán năm PIT

Trước 31/03 năm sau:

### Bước 1: Tổng hợp

```
/modern/reports/pit-monthly/?year=2025
```

Cho từng NV:
- Tổng thu nhập chịu thuế năm
- Tổng giảm trừ (13.2M × 12 + 5.2M × dependent_count × 12)
- Tổng PIT đã khấu trừ

### Bước 2: Quyết toán

Cho từng NV có MST:
- Tính lại PIT theo tổng năm
- So với PIT đã khấu trừ
- Chênh lệch: hoàn (âm) hoặc nộp thêm (dương)

### Bước 3: Báo cáo CQT

Tạo form **05/CK-TNCN** (chưa có auto, làm thủ công):

1. List PayrollRun năm
2. Tổng hợp per NV
3. Điền form 05 paper/PDF
4. Nộp qua Thuế điện tử (thuedientu.gdt.gov.vn)

### Bước 4: Hoàn lại PIT cho NV

Nếu PIT đã khấu trừ > PIT thực:
- Tạo phiếu chi: N3334 / C111 (hoàn PIT cho NV)
- Báo CQT trong tờ khai quyết toán

## Edge cases

### NV mới vào giữa tháng

PayrollRun auto-prorate: `gross × (working_days / standard_days)`.

### NV thai sản

Tạo LeaveRecord loại `maternity`:
- Hệ thống tính trợ cấp BHXH theo mức đóng 6 tháng trước
- Voucher: N334 / C111 (trợ cấp từ BHXH)
- PayrollLine loại trừ tháng nghỉ

### NV nước ngoài

Phân loại:
- **Resident** (> 183 ngày ở VN): tính PIT lũy tiến như VN
- **Non-resident**: 20% flat trên thu nhập

Config qua Employee.pit_type.

### Lương part-time / hourly

PayrollLine có `hourly_rate` + `hours_worked`. Gross = hourly × hours.

### Lương 13

Cuối năm tạo PayrollRun riêng:
- Type = `bonus`
- Period = tháng 12 hoặc tháng 1 năm sau
- Voucher: N6221 / C334 (riêng từng NV)
- Có tính PIT

### Award / Penalty

PayrollLine field `bonus_amount` + `penalty_amount` — adjust gross trước tính PIT.

## Voucher accounting summary

Mỗi PayrollRun post tạo 1 voucher với:

```
Dr 6221 (CP lương) ............ total_gross
Dr 338 (CP khác - KPCĐ) ....... total_gross × 2%
   Cr 334 (Phải trả NLĐ) ...... total_net
   Cr 3335 (Phải trả BHXH) .... total_gross × 10.5%
   Cr 3334 (Phải trả TNCN) .... total_pit
   Cr 338 (KPCĐ) .............. total_gross × 2%
   Cr 3333x (các loại thuế khác nếu có)
```

Khi thanh toán:
```
Dr 334 (Phải trả NLĐ) ........ total_net
   Cr 112 (Bank) ............. total_net
```

## Audit / Compliance

| Hạng mục | Deadline | Hình thức |
|----------|----------|-----------|
| Tính lương | 28 của tháng | Nội bộ |
| Pay bank | 30 của tháng | Bank upload |
| BC D62 BHXH | Cuối tháng | Nộp cơ quan |
| BHXH thanh toán | Cuối tháng | Bank → cơ quan |
| PIT khấu trừ | Hàng tháng | Hold internally |
| Quyết toán PIT năm | 31/03 năm sau | Nộp CQT |
| Quyết toán BHXH năm | 31/01 năm sau | Nộp cơ quan |

---

Tài liệu liên quan:
- [06-hr-payroll](../user-guide/06-hr-payroll.md) — User guide HR
- [R4-pit-filing](04-pit-filing.md) — Kê khai PIT
- [01-monthly-close](01-monthly-close.md) — Chốt sổ tháng
