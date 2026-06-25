# 02 — Bán hàng & Công nợ phải thu

> Hóa đơn bán, khách hàng, công nợ, HĐĐT, BC công nợ theo tuổi.

## 1. Khách hàng

Sidebar → **Nghiệp vụ → Khách hàng**

### Tạo khách hàng mới

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| Code | ✓ | Duy nhất (VD: `CUST001`) |
| Name | ✓ | Tên đầy đủ |
| Tax code | | Mã số thuế |
| Address | | Địa chỉ |
| Phone / Email | | Liên hệ |
| Customer group | | Phân loại |
| Credit limit | | Hạn mức tín dụng |
| Default VAT rate | % | Mặc định khi tạo HĐ |

### Import nhiều KH

Liên hệ admin — chưa có UI import.

## 2. Hóa đơn bán

Sidebar → **Nghiệp vụ → Hóa đơn bán**

### Tạo hóa đơn

1. **"+ Thêm hóa đơn"**
2. **Header**:
   - Số HĐ: tự sinh `HĐ-yyyy-mm-NNN`
   - Ngày HĐ
   - Khách hàng (dropdown)
   - Nhân viên sales
   - Tiền tệ (mặc định VND)
3. **Dòng hàng**:
   - Chọn sản phẩm (auto-fill đơn giá)
   - Số lượng, đơn giá
   - % VAT (0/5/8/10)
   - Thành tiền tự tính
4. **Tổng cộng** tự tính
5. **Lưu** → tự động:
   - Sinh phiếu kế toán `N131 / C5111 / C33311`
   - Ghi sổ

### Trạng thái hóa đơn

| Status | Ý nghĩa |
|--------|---------|
| `draft` | Chưa ghi sổ |
| `posted` | Đã ghi sổ, chờ thanh toán |
| `paid` | Đã thanh toán đủ |
| `partial` | Thanh toán một phần |
| `cancelled` | Đã hủy |

### Thanh toán (ghi nhận)

Tạo **Phiếu thu** (CashReceipt) → chọn HĐ → nhập số tiền → bút toán tự sinh:
- N111 / C131 (từng KH theo object_code)

Hệ thống tự cập nhật `paid_amount` của HĐ và `payment_status`.

## 3. Hóa đơn điện tử (HĐĐT)

Xem chi tiết: [10-einvoice.md](10-einvoice.md)

### Phát hành HĐĐT

Từ chi tiết hóa đơn bán → bấm **"Phát hành HĐĐT"** → hệ thống:
1. Tạo EInvoice draft với XML/JSON TT78
2. Gán số HĐĐT tuần tự
3. (Manual mode) Đợi user upload PDF đã ký

### Hủy / Điều chỉnh HĐĐT

- **Hủy**: detail HĐĐT → "Hủy HĐĐT" → nhập lý do → status `cancelled`
- **Điều chỉnh**: detail HĐĐT → "Tạo HĐ điều chỉnh" → tạo EInvoice mới với số
  âm, cùng số HĐ gốc

## 4. Báo cáo công nợ

### BC tổng hợp

Sidebar → **Báo cáo → BCĐTK** → xem TK **131**

### BC công nợ theo tuổi (Aging)

Chưa có báo cáo tự động. Workaround:
1. Xuất Excel list SalesInvoice
2. Pivot theo `[HĐ] × [ngày] × [số tiền] × [ngày tới hạn]`
3. Tính aging bucket: 0-30/31-60/61-90/90+ ngày

## 5. Workflow Order-to-Cash đầy đủ

```
Lead (CRM)
   ↓
Opportunity (cơ hội)
   ↓ Won
Quote → Sales Order
   ↓
Delivery (StockVoucher xuất kho)
   ↓
SalesInvoice (hóa đơn bán)
   ↓ tự sinh
Voucher (N131/C5111/C33311)
   ↓
E-Invoice (HĐĐT)
   ↓
Customer pays (CashReceipt N111/C131)
   ↓
Aging Report
```

Xem chi tiết: [W2-order-to-cash](../workflows/02-order-to-cash.md)

## 6. Phím tắt

| Phím | Chức năng |
|------|-----------|
| `g` `s` | Vào sales invoice list |
| `g` `c` | Vào customer list |

## FAQ

**Q: Khách hàng trả tiền trước (chưa có HĐ) — hạch toán sao?**
A: Tạo Phiếu thu `N111 / C131` (KH), ghi chú "Tạm ứng KH". Khi xuất HĐ sau, bút
toán là `N131 / C5111 / C33311` → tự động đối trừ với tạm ứng.

**Q: HĐ bị sai thông tin nhưng đã post?**
A: Unpost → sửa → post lại (nếu trong kỳ chưa chốt). Nếu kỳ đã chốt → tạo
phiếu điều chỉnh kỳ sau.

**Q: HĐ xuất nhưng KH chưa thanh toán — làm sao theo dõi?**
A: List SalesInvoice → filter `payment_status != paid` → xem aging.

**Q: Xuất HĐ nhưng muốn xuất 2 lần (1 cho KH, 1 lưu)?**
A: In 2 bản PDF (nút "In hóa đơn" / "Print"). Hệ thống không giới hạn.

**Q: Khách hàng thanh toán bằng USD?**
A: Chọn `currency_code = USD` khi tạo HĐ. Hệ thống quy ra VND theo tỷ giá ngày
HĐ và hạch toán bằng VND. Cuối kỳ chạy FX revaluation.

---

Tài liệu liên quan:
- [10-einvoice.md](10-einvoice.md) — Hóa đơn điện tử
- [W2-order-to-cash](../workflows/02-order-to-cash.md) — Workflow đầy đủ
- [R3-vat-filing](../runbook/03-vat-filing.md) — Kê khai VAT hàng tháng
