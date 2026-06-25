# 01 — Kế toán tổng hợp

> Phiếu kế toán, sổ cái, kết chuyển cuối kỳ.

## Tổng quan

Module Kế toán tổng hợp là **trung tâm của hệ thống** — mọi bút toán từ
bán/mua/kho/lương đều quy về đây dưới dạng **Phiếu kế toán (AccountingVoucher)**.

### Các khái niệm cốt lõi

| Khái niệm | Mô tả |
|-----------|-------|
| **Phiếu kế toán** (`AccountingVoucher`) | Tập hợp các bút toán cân đối Nợ=Có |
| **Bút toán** (`VoucherLine`) | 1 dòng Nợ hoặc Có trên TK |
| **Sổ cái** (`GeneralLedger`) | Bảng tổng hợp theo TK × kỳ |
| **Bảng CĐTK** (`AccountPeriodBalance`) | Số dư đầu/PS/SD cuối theo TK |
| **Khóa sổ** (`period closing`) | KC cuối kỳ: N5xx/C911, N911/C6xx, N911/C421 |

### Trạng thái phiếu

| Status | Ý nghĩa | Có thể |
|--------|---------|--------|
| `draft` (0) | Lưu tạm | Sửa, xóa |
| `ledger` (2) | Đã ghi sổ | Không sửa (phải unpost) |
| `locked` (3) | Khóa kỳ | Không sửa/xóa |

## Quy trình nghiệp vụ

### A. Tạo phiếu kế toán thủ công

1. Sidebar → **Cập nhật số liệu → Phiếu kế toán**
2. Bấm **"+ Tạo phiếu kế toán"**
3. Điền **Header**:
   - Loại phiếu: `journal` / `payment` / `receipt` / `sales_receipt` / ...
   - Số CT: để trống = tự sinh
   - Ngày CT
   - Diễn giải
4. Thêm **dòng bút toán**:
   - TK Nợ / TK Có
   - Đối tượng (mã KH/NCC/nhân viên)
   - Số tiền Nợ hoặc Có
   - Diễn giải dòng
5. Kiểm tra **tổng Nợ = tổng Có** (phải cân)
6. Bấm **Lưu** → tự động ghi sổ (status = `ledger`)

### B. Tự động sinh phiếu từ module khác

| Module | Bút toán tự sinh | TK |
|--------|-----------------|----|
| Hóa đơn bán (SalesInvoice) | N131 / C5111 / C33311 | Phải thu / Doanh thu / VAT đầu ra |
| Hóa đơn mua (PurchaseInvoice) | N156 / N1331 / C331 | Kho / VAT đầu vào / Phải trả |
| Tính lương (PayrollRun) | N622 / N334 / N3335 / N338 / C111 | Chi phí lương / Phải trả lương / BHXH / KH khác / Tiền |
| Khấu hao TSCĐ | N642 / C211 | Chi phí / Khấu hao lũy kế |
| Phiếu thu CashReceipt | N111 / C131 | Tiền mặt / Phải thu |
| Phiếu chi CashPayment | N331 / N642 / C111 | Phải trả / Chi phí / Tiền mặt |

### C. Sửa / Xóa phiếu

- **Phiếu ở trạng thái `draft`**: Sửa/xóa thoải mái
- **Phiếu ở trạng thái `ledger`**: Phải **unpost** trước (chỉ người có quyền
  `ledger.access`):
  1. Vào chi tiết phiếu
  2. Bấm **"Unpost"** → phiếu về `draft`
  3. Sửa → **Save** → tự động post lại
- **Phiếu `locked`**: Không sửa được. Liên hệ KTT nếu cần điều chỉnh → tạo
  phiếu điều chỉnh.

### D. Kết chuyển cuối kỳ

Sau khi nhập đầy đủ phiếu trong kỳ:

1. Sidebar → **Cập nhật số liệu → Kết chuyển cuối kỳ**
2. Chọn kỳ (tháng/năm)
3. Bấm **"Kết chuyển"** → hệ thống tự động tạo các phiếu:
   - KC doanh thu: **N5111/C911**
   - KC chi phí: **N911/C632, C641, C642, C635**
   - KC thuế: **N911/C33311** (if credit balance)
   - Xác định KQKD: **N911/C421** (lãi) hoặc **N421/C911** (lỗ)

> **Lưu ý**: KC là **idempotent** — chạy lại kỳ đã KC không sinh thêm phiếu.

## Sổ sách

### Sổ nhật ký chung (S03a-DN)

Sidebar → **Sổ sách → Nhật ký chung**. Hiển thị tất cả bút toán theo thời gian.
Filter theo:
- Kỳ (tháng/năm)
- TK
- Số CT

### Sổ cái (S03b-DN)

Sidebar → **Sổ sách → Sổ cái**. Hiển thị **PS Nợ / PS Có / SD** cho 1 TK cụ thể
trong kỳ.

## Báo cáo kế toán

| Báo cáo | Đường dẫn | Chuẩn |
|---------|-----------|-------|
| **Bảng CĐTK** | Báo cáo → BCĐ tài khoản | TT133 |
| **BCTC B01-DN** | Báo cáo → BCTC tài chính | TT200 |
| **KQ HĐKD B02-DN** | Báo cáo → KQ HĐKD | TT200 |
| **Tờ khai GTGT 01/GTGT** | Báo cáo → Tờ khai GTGT | TT80 |
| **BC D62 (BHXH)** | Báo cáo → D62 | TT595 |
| **BC thuế TNCN** | Báo cáo → TNCN | TT111 |
| **BC quỹ lương** | Báo cáo → Quỹ lương | TT22 |

## Phím tắt thường dùng

| Phím | Chức năng |
|------|-----------|
| `g` `v` | Vào voucher list |
| `n` (trong list) | Tạo phiếu mới |
| `Ctrl+S` (trong form) | Lưu phiếu |

## FAQ

**Q: Tạo phiếu nhưng báo "Không cân đối"?**
A: Tổng Nợ phải = tổng Có (sai số ≤ 1 VND). Kiểm tra lại các dòng.

**Q: Phiếu đã ghi sổ nhưng muốn sửa?**
A: Vào detail → **Unpost** → sửa → Save (tự post lại).

**Q: Khóa kỳ thìphiếu kỳ trước có sửa được?**
A: Không. Phải mở khóa kỳ (admin/KTT), sửa, rồi khóa lại. Khuyến nghị tạo
phiếu điều chỉnh kỳ hiện tại.

**Q: Báo cáo BCĐTK không cân?**
A: Kiểm tra:
1. Tất cả phiếu trong kỳ đã `ledger` chưa
2. Đã KC kỳ chưa (KC có thể đang thiếu)
3. Có phiếu kỳ sau nhưng nhập sai kỳ trước

**Q: Làm sao hạch toán ngược 1 phiếu đã post?**
A: Tạo phiếu bút toán đảo — copy phiếu cũ, đảo Nợ/Có, ghi chú "Đảo phiếu #XYZ".

---

Tài liệu liên quan:
- [R1-monthly-close](../runbook/01-monthly-close.md) — Quy trình chốt sổ tháng
- [R2-yearly-close](../runbook/02-yearly-close.md) — Chốt sổ năm
- [T3-data-model](../technical/03-data-model.md) — ERD chi tiết
