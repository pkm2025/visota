# R5 — Quy trình phát hành HĐĐT hàng ngày

> Workflow phát hành HĐĐT cho mọi hóa đơn bán — end-to-end.

## Quy trình

```
1. SalesInvoice post → status=ledger
        ↓
2. Vào chi tiết SalesInvoice
        ↓
3. Bấm "Phát hành HĐĐT"
        ↓ Tạo EInvoice draft (XML + JSON)
4. Verify nội dung EInvoice
        ↓ OK
5. Bấm "Phát hành" → cấp số HĐĐT
        ↓ Manual: upload PDF đã ký
        ↓ API: gọi provider, lấy signed PDF
6. EInvoice status = issued
        ↓
7. Gửi HĐĐT cho khách hàng (PDF + XML qua email)
        ↓
8. Lưu trữ: XML + PDF + signed file (≥ 10 năm)
```

## Bước chi tiết

### 1. SalesInvoice đã post

Verify có SalesInvoice với `status=ledger` (đã ghi sổ kế toán).

### 2. Phát hành EInvoice

```
/modern/sales-invoices/<id>/ → bấm "Phát hành HĐĐT"
```

Hệ thống tạo `EInvoice`:
- Snapshot buyer (customer): name, tax_code, address
- Snapshot seller (company)
- Tính tổng: subtotal + VAT 8/10% = total
- Tạo XML theo schema TT78
- Tạo JSON payload cho provider API

### 3. Verify

Vào `/modern/einvoices/<id>/` để xem:
- Mẫu / ký hiệu (pattern/serial)
- Số HĐĐT (cấp tự động tuần tự)
- Bên bán / Bên mua
- Items (description, qty, price, amount, VAT rate)
- Tổng cộng
- Viết bằng chữ (auto-generate)

**Nếu sai**: Bấm "Hủy" → tạo lại từ SalesInvoice.

### 4. Phát hành

- **Manual mode**: Bấm "Phát hành" → status=issued → user upload PDF đã ký
- **API mode**: Bấm "Phát hành" → gọi provider → lấy signed PDF

Sau khi phát hành: **số HĐĐT cố định, không đổi được**.

### 5. Gửi cho khách

Download:
- XML (schema TT78) — bắt buộc gửi cho KH theo luật
- PDF — dễ in/đọc

Gửi qua email + Upload lên portal KH.

### 6. Lưu trữ

```
/var/lib/pmketoan/media/einvoice/
├── xml/2026/06/abc-123.xml       (XML TT78)
├── json/2026/06/abc-123.json     (JSON provider)
└── pdf/2026/06/abc-123.pdf       (PDF signed)
```

Retain ≥ 10 năm per Luật KT.

## Edge cases

### Khách hàng không có MST

- `buyer_tax_code` để trống
- Hệ thống vẫn phát hành
- Báo cáo CQT ghi "KH không MST"

### HĐ xuất sai nhưng đã > 2 giờ

Không hủy được. Lựa chọn:

**Điều chỉnh** (Adjust) — sai nhỏ:
- Tạo EInvoice mới với số âm cho khoản sai
- Ghi rõ "Điều chỉnh HĐ <số gốc>"

**Thay thế** (Replace) — sai lớn:
- Tạo EInvoice mới thay thế hoàn toàn
- Báo CQT trong BC01 kỳ sau

### Khách yêu cầu xuất đợt 2

Được — download lại PDF/XML. Không phát hành lại (số HĐ không đổi).

### Lỗi provider API

```
EInvoice.error_message = "Provider timeout"
```

Switch sang manual mode tạm:

```bash
python manage.py shell -c "
from apps.einvoice.models import EInvoiceConfig
c = EInvoiceConfig.objects.first()
c.provider = 'manual'
c.save()
"
```

User upload PDF đã ký bằng phần mềm riêng của provider (VD: MISA Asoka).

## Cuối kỳ — Báo cáo BC01

Sidebar → **Báo cáo & Thuế → Hóa đơn điện tử**

Cuối trang có form BC01:

1. Chọn kỳ (tháng/năm)
2. Bấm **"Tạo BC01"**
3. Hệ thống tổng hợp HĐĐT đã phát hành + canceled trong kỳ
4. Download XML → nộp qua **muasamcong.mpi.gov.vn** hoặc qua email CQT

**Deadline**: ngày 20 tháng sau (cùng kỳ với VAT).

## Thống kê

Từ `/modern/einvoices/`:
- Tổng HĐĐT đã phát hành kỳ
- Tổng doanh thu (kê khai VAT)
- Tổng VAT đầu ra
- HĐĐT đã hủy

## Audit

Mỗi HĐĐT có audit:
- `issued_by` — user phát hành
- `issue_date` — timestamp
- `provider_response` — response từ provider
- `replaces_invoice` — nếu là HĐ điều chỉnh/thay thế

## Lỗi thường gặp

**"Cannot generate XML — buyer missing"**
→ Update customer có `name` + `tax_code` (nếu có).

**"Invoice no collision"**
→ Hệ thống auto-generate số tuần tự. Nếu conflict, hệ thống skip. Verify
`EInvoiceService._next_invoice_no`.

**"BC01 missing invoices"**
→ BC01 chỉ lấy HĐĐT `status in [issued, adjusted]`. Nếu KH hủy rồi — vẫn
phải báo trong BC01 → check `cancelled` cũng được include.

---

Tài liệu liên quan:
- [10-einvoice](../user-guide/10-einvoice.md) — User guide HĐĐT
- [02-sales](../user-guide/02-sales.md) — Tạo SalesInvoice
- [R3-vat-filing](03-vat-filing.md) — Tờ khai VAT hàng tháng
