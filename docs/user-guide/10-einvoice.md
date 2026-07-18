# 10 — Hóa đơn điện tử (TT78/2021)

> Quy trình phát hành, hủy, điều chỉnh HĐĐT theo TT78/2021/TT-BTC.

## 1. Tổng quan

HĐĐT bắt buộc từ **01/07/2022** theo TT78/2021/TT-BTC. Visota ERP hỗ trợ:

| Provider | Loại | Trạng thái |
|----------|------|------------|
| **Manual** | Ký PDF thủ công | ✓ sẵn sàng |
| MISA | API | ⚠ Stub — cần credentials |
| VNPT-Invoice | API | ⚠ Stub |
| eHoadon (VNPT) | API | ⚠ Stub |
| BKAV | API | ⚠ Stub |
| Viettel-Invoice | API | ⚠ Stub |

> ⚠ **Quan trọng**: Chế độ `manual` chỉ dùng cho demo/pilot. Khi go-live, **phải
> cấu hình provider thật** để ký số HĐĐT hợp lệ theo TT78.

## 2. Cấu hình provider (Admin)

Sidebar → **Hệ thống → Cấu hình HĐĐT** (chỉ staff)

| Trường | Ví dụ |
|---------|-------|
| Provider | MISA / VNPT / Viettel / Manual |
| Pattern | `1C26T` (mẫu hóa đơn) |
| Serial | `AA/26E` (ký hiệu) |
| Form symbol | `01GTKT` |
| Issue place | Đơn vị phát hành |
| API URL | `https://www.misa.vn/api/einvoice/...` |
| API username | username@pkm |
| API password | (encrypted) |
| API token | Bearer token |

## 3. Quy trình phát hành

### A. Từ SalesInvoice

1. Tạo SalesInvoice bình thường (xem [02-sales](02-sales.md))
2. Sau khi post, vào detail SalesInvoice
3. Bấm **"Phát hành HĐĐT"** → tạo `EInvoice` (draft)
4. Hệ thống auto-generate:
   - XML theo schema TT78 (file `.xml`)
   - JSON payload cho provider API (file `.json`)
5. Vào detail EInvoice → xem trước nội dung → kiểm tra thông tin
6. Bấm **"Phát hành"** → 2 trường hợp:
   - **Manual mode**: gán số HĐĐT, đợi upload PDF đã ký
   - **API mode**: gọi provider → lấy signed PDF → status = `issued`

### B. Trực tiếp (không từ SalesInvoice)

Ít dùng — chỉ cho hóa đơn không có HĐ bán (VD: xuất cho nội bộ).

## 4. Trạng thái HĐĐT

| Status | Ý nghĩa | Đã phát sinh cho CQT |
|--------|---------|----------------------|
| `draft` | Mới tạo, chưa phát hành | ❌ |
| `issued` | Đã phát hành + có số | ✓ |
| `adjusted` | Đã có HĐ điều chỉnh | ✓ (gốc) |
| `replaced` | Đã bị thay thế bởi HĐ khác | ✓ (gốc) |
| `cancelled` | Đã hủy | ✓ (có trong BC01 với lý do) |

## 5. Hủy HĐĐT

Hủy được trong vòng **2 giờ** sau khi phát hành (per TT78).

1. Detail EInvoice → **"Hủy HĐĐT"**
2. Nhập lý do hủy (bắt buộc): "Sai tên KH" / "Sai số tiền" / ...
3. Status → `cancelled`
4. **Bắt buộc**: tải XML/JSON hủy, gửi email cho KH + thông báo CQT trong BC01
   kỳ tiếp theo

## 6. Điều chỉnh / Thay thế

Khi HĐĐT đã phát hành nhưng sai và **không thể hủy** (> 2 giờ):

### Điều chỉnh (Adjust)

Tạo HĐĐT mới với số âm cho khoản sai + số dương cho khoản đúng. Dùng khi:
- Sai số lượng/đơn giá nhỏ
- Sai thông tin phụ

### Thay thế (Replace)

Tạo HĐĐT mới thay thế hoàn toàn. Dùng khi:
- Sai KH hoặc MST
- Sai tổng tiền lớn

> ⚠ **Quan trọng**: Không được thay thế nếu HĐ gốc đã kê khai VAT trong tờ
> khai GTGT kỳ trước. Phải dùng điều chỉnh.

## 7. Báo cáo CQT

### BC01 — Tình hình sử dụng HĐĐT (hàng tháng)

Sidebar → **Báo cáo & Thuế → Hóa đơn điện tử** → cuối trang form BC01:

1. Chọn kỳ (tháng/năm)
2. Bấm **"Tạo BC01"**
3. Hệ thống tổng hợp tất cả HĐĐT `issued` trong kỳ → sinh XML
4. Download XML → nộp qua **Hệ thống mạng HĐĐT** của CQT (tổng cục thuế)

### BC26 — BC định kỳ (hàng quý)

Tương tự BC01 nhưng theo quý.

### TB04 — Thông báo phát hành

Mỗi lần đăng ký mẫu HĐ mới → tạo TB04 gửi CQT trước khi dùng.

## 8. Lưu trữ

| Loại | Nơi lưu | Thời gian |
|------|---------|-----------|
| XML/JSON TT78 | `einvoice/xml/`, `einvoice/json/` | ≥ 10 năm |
| PDF đã ký | `einvoice/pdf/` | ≥ 10 năm |
| BC01/BC26 | `einvoice/reports/` | ≥ 10 năm |

Backup hàng ngày (xem [A5-backup](../admin-guide/05-backup-restore.md)).

## 9. Workflow phát hành đầy đủ

```
SalesInvoice (hóa đơn bán)
   ↓ bấm "Phát hành HĐĐT"
EInvoice (draft)
   ↓ generate XML/JSON
Kiểm tra nội dung
   ↓ OK
Publish → gọi provider API (hoặc đợi ký thủ công)
   ↓
EInvoice (issued) → có số HĐĐT
   ↓
Lưu trữ XML/PDF ≥ 10 năm
   ↓
Cuối kỳ: BC01 → CQT
```

Xem chi tiết: [R5-einvoice-flow](../runbook/05-einvoice-flow.md)

## FAQ

**Q: Lỗi "Provider error: timeout" khi publish?**
A: Provider có thể down. Bấm **"Retry"** sau 5 phút. Nếu vẫn lỗi, chuyển sang
`manual mode` tạm thời (upload PDF đã ký bằng phần mềm riêng của provider).

**Q: Khách hàng yêu cầu xuất lại PDF khác?**
A: Có thể. Vào detail EInvoice → download XML/JSON → regenerate PDF. Không
phát hành lại (số HĐĐT không đổi).

**Q: HĐĐT xuất sai kỳ — khắc phục sao?**
A: Không sửa được kỳ đã báo cáo. Cách duy nhất: tạo HĐ điều chỉnh kỳ hiện tại,
ghi rõ điều chỉnh cho kỳ trước.

**Q: Khách hàng nước ngoài cần HĐ bằng tiếng Anh?**
A: Hệ thống hiện chỉ hỗ trợ tiếng Việt. Workaround: tạo 2 HĐĐT (1 VI + 1 EN
ghi chú "Translation only, not for tax purposes").

**Q: Xuất hóa đơn cho KH không có MST?**
A: Được cho cá nhân không có MST. Bỏ trống `buyer_tax_code`. Hệ thống vẫn phát
hành bình thường.

---

Tài liệu liên quan:
- [R5-einvoice-flow](../runbook/05-einvoice-flow.md) — Quy trình phát hành đầy đủ
- [02-sales](02-sales.md) — Tạo hóa đơn bán
- [A4-tax-config](../admin-guide/04-tax-config.md) — Cấu hình thuế
