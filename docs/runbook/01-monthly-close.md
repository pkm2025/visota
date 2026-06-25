# R1 — Chốt sổ cuối tháng

> Checklist đóng sổ kế toán hàng tháng. Thời gian thực hiện: 2-4 giờ.

## Điều kiện tiên quyết

- [ ] Tất cả hóa đơn bán (SalesInvoice) trong tháng đã tạo
- [ ] Tất cả hóa đơn mua (PurchaseInvoice) trong tháng đã nhập
- [ ] Tất cả phiếu thu/chi đã tạo
- [ ] Đã tính lương kỳ (PayrollRun)
- [ ] Đã tính khấu hao TSCĐ kỳ (DepreciationRun)
- [ ] Đã import sao kê ngân hàng (Banking → import)

## Quy trình (theo thứ tự)

### 1. Kiểm tra phiếu lưu tạm (đảm bảo không quên)

```
/modern/vouchers/?status=draft
```

- Review từng phiếu `draft`
- Hoàn thành hoặc xóa

### 2. Tính khấu hao kỳ

```
/modern/assets/depreciation/
```

- Chọn tháng/năm
- Bấm **"Tính khấu hao kỳ"**
- Verify: voucher `KH-yyyy-mm` được tạo, status = `ledger`
- Voucher: N642 / C211 (mỗi TSCĐ)

### 3. Tính lương kỳ

```
/modern/payroll/run/
```

- Chọn tháng/năm
- Bấm **"Tính lương kỳ"**
- Verify: PayrollRun tạo với N dòng (số NV active)
- Voucher tự sinh: N6221/N334/N338/N3335/N3334/C111

### 4. Phân bổ chi phí chờ kết chuyển (TK 242)

Nếu có chi phí trả trước (VD: thuê nhà cả năm):

```
/modern/recurring/
```

- Tạo recurring voucher: N642/C242 hàng tháng
- Bấm **"Run"** cho kỳ hiện tại

### 5. Đối soát ngân hàng

```
/modern/banking/reconcile/
```

- Import sao kê (nếu chưa)
- Bấm **"Chạy auto-reconcile"**
- Verify: các giao dịch match với phiếu thu/chi
- Match thủ công các giao dịch còn lại

### 6. Phát hành HĐĐT (nếu chưa)

```
/modern/einvoices/?status=draft
```

- Mỗi HĐĐT draft → bấm **"Phát hành"**
- Verify: status = `issued`, có số HĐĐT

### 7. Kiểm tra tổng Nợ = Có

```
/modern/reports/trial-balance/
```

- Chọn kỳ (tháng/năm)
- Verify **Tổng PS Nợ = Tổng PS Có**
- Nếu lệch > 1 VND → tìm phiếu không cân → sửa

### 8. Kết chuyển cuối kỳ

```
/modern/closing/
```

- Chọn kỳ
- Bấm **"Kết chuyển"**
- Verify: 3 voucher tự sinh:
  - KC doanh thu: N511/C911
  - KC chi phí: N911/C6xx
  - Xác định KQKD: N911/C421 (lãi) hoặc N421/C911 (lỗ)

### 9. Khóa kỳ (optional)

Khi kỳ đã hoàn tất + báo cáo gửi CQT:

- Liên hệ KTT để `lock` tất cả voucher trong kỳ
- Sau khi lock → không sửa được (per Luật KT)

> ⚠ **Cảnh báo**: Khóa kỳ là không thể đảo ngược. Chỉ làm sau khi:
> - Báo cáo VAT đã nộp CQT
> - Báo cáo TNCN đã nộp CQT
> - Báo cáo BHXH đã nộp

### 10. Xuất báo cáo kỳ

| Báo cáo | Đường dẫn | Kê khai |
|---------|-----------|---------|
| BCĐTK | /modern/reports/trial-balance/ | Lưu trữ nội bộ |
| BCTC B01 | /modern/reports/balance-sheet/ | Báo cáo QBT (nếu cần) |
| KQ HĐKD B02 | /modern/reports/pnl/ | Báo cáo QBT (nếu cần) |
| Tờ khai GTGT 01 | /modern/reports/vat-return/ | Nộp CQT ngày 20 tháng sau |
| BC D62 | /modern/reports/d62/ | Nộp BHXH ngày cuối tháng |
| BC TNCN | /modern/reports/pit-monthly/ | Lưu nội bộ — quyết toán năm |

## 11. Lưu trữ

Tạo thư mục tháng:

```
/var/lib/pmketoan/closing/2026-06/
├── trial_balance.pdf
├── balance_sheet.pdf
├── pnl.pdf
├── vat_return_01.xlsx
├── d62.pdf
└── notes.md (nhật ký chốt sổ)
```

## Checklist cuối

- [ ] Không còn phiếu draft
- [ ] Khấu hao đã chạy
- [ ] Lương đã chạy
- [ ] HĐĐT đã phát hành hết
- [ ] BCĐTK cân
- [ ] KC kỳ đã chạy
- [ ] Báo cáo kỳ xuất file
- [ ] Gửi cho KTT review trước khi nộp CQT

## FAQ

**Q: Khi nào làm chốt sổ?**
A: Các ngày đầu tháng sau (1-5). Nộp VAT chậm nhất ngày 20.

**Q: Phát hiện sai sau khi đã KC?**
A:
- Nếu chưa nộp CQT: unpost voucher KC → sửa → KC lại
- Nếu đã nộp CQT: tạo phiếu điều chỉnh kỳ hiện tại (bút toán đảo + đúng)

**Q: Cần điều chỉnh kỳ trước đã KC?**
A: Unpost KC kỳ trước → sửa phiếu → KC lại. **Chỉ làm nếu kỳ trước chưa lock**.
Nếu đã lock → liên hệ admin để unlock + audit trail.

**Q: KC kỳ chạy báo lỗi?**
A: Thường vì có phiếu không cân (Nợ ≠ Có). Tìm trong BCĐTK xem TK 911 có
balance không = 0 sau KC.

---

Tài liệu liên quan:
- [R2-yearly-close](02-yearly-close.md) — Chốt sổ cuối năm
- [R3-vat-filing](03-vat-filing.md) — Nộp VAT chi tiết
- [01-ledger](../user-guide/01-ledger.md) — User guide kế toán
