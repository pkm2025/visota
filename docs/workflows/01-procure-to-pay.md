# W1 — Procure-to-Pay (P2P): Mua đến Trả

> Workflow đầy đủ từ yêu cầu mua → chọn NCC → mua → nhập kho → thanh toán.

## Sơ đồ tổng thể

```
[Yêu cầu mua] (Purchase Request)
        ↓
[Duyệt yêu cầu] (Approval)
        ↓
[Chọn nhà cung cấp] (Vendor selection)
        ↓
[Hợp đồng / Đơn hàng] (Purchase Order)
        ↓
[NCC giao hàng] (Delivery)
        ↓
[Nhập kho] (StockVoucher N152/C156)
        ↓
[Hóa đơn mua] (PurchaseInvoice N156/N1331/C331)
        ↓ auto-voucher
[Voucher kế toán]
        ↓
[Đối soát hóa đơn vs phiếu nhập] (3-way match)
        ↓
[Chờ đến hạn thanh toán]
        ↓
[Phiếu chi / Chuyển khoản] (CashPayment N331/C111/C112)
        ↓
[Đối soát sao kê ngân hàng] (BankReconciliation)
        ↓
[BC công nợ NCC 331]
```

## 1. Yêu cầu mua (Purchase Request)

**Hiện chưa có module** — planned. Workaround:

- Tạo Opportunity trong CRM loại `internal_request`
- Hoặc ticket trong CRM
- Gắn file Excel/Word yêu cầu

## 2. Duyệt yêu cầu

Qua **Approval workflow** (xem [11-approvals](../user-guide/11-approvals.md)):

- Rule: `purchase_request` amount > 50M → cần KTT duyệt
- Step 1: Trưởng phòng mua hàng (`purchaser` role)
- Step 2: KTT (`chief_accountant` role)

## 3. Chọn nhà cung cấp

Sidebar → **Nghiệp vụ → Nhà cung cấp**

### Tạo NCC mới

| Trường | Bắt buộc |
|--------|----------|
| Code | ✓ (VD: `VENDOR001`) |
| Name | ✓ |
| Tax code | |
| Address | |
| Payment terms | | Net 30/60/90 |
| Default VAT | % |

### So sánh báo giá

Tạo nhiều `Opportunity` cùng item → so sánh giá → chọn best.

## 4. Đơn hàng mua (PO)

**Hiện chưa có** — planned. Workaround: tạo `Contract` loại `purchase`:

```
/modern/contracts/new/
  - contract_no: PO-yyyy-mm-NNN
  - contract_type: purchase
  - party_code: <vendor code>
  - value: <total PO>
```

## 5. Nhận hàng + Nhập kho

Sidebar → **Nghiệp vụ → Phiếu nhập xuất**

### Tạo phiếu nhập mua

```
Type: purchase_receipt
Date: <ngày nhận hàng>
Vendor: <code>
Lines:
  - Product: SKU1, qty=10, unit_price=...
  - Product: SKU2, qty=5, unit_price=...
```

**Auto-voucher**:
- N152 (chi phí mua hàng) hoặc N156 (kho hàng)
- C156 → chưa phải NCC, vì chưa có hóa đơn

> ⚠ **Quan trọng**: Nhập kho không ghi nhận công nợ NCC — phải đợi hóa đơn.

## 6. Hóa đơn mua

Sidebar → **Nghiệp vụ → Phiếu nhập mua** (PurchaseInvoice)

### Tạo

| Trường | Ví dụ |
|---------|-------|
| Invoice no | `PN-yyyy-mm-NNN` |
| Vendor | `VENDOR001` |
| Invoice date | ngày trên hóa đơn NCC |
| Lines | qty × unit_price (phải khớp PO + phiếu nhập) |

**Auto-voucher**:
- N156 (kho hàng — theo line)
- N1331 (VAT đầu vào 10%)
- C331 (phải trả NCC — theo vendor)

### 3-way match (kiểm tra 3 chiều)

Trước khi duyệt hóa đơn, verify:

| Source | Value |
|--------|-------|
| **PO** | qty=10, price=1M |
| **GR** (Goods Receipt) | qty=10 received |
| **Invoice** | qty=10, price=1M |

Match → duyệt. Lệch → điều tra.

Hiện chưa có auto-check, làm thủ công qua list.

## 7. Thanh toán

### Chờ đến hạn

Theo `payment_terms` của NCC (Net 30/60/90).

Sidebar → **Báo cáo → BCĐTK** → xem TK 331 theo NCC → tính aging.

### Tạo phiếu chi

Sidebar → **Cập nhật số liệu → Phiếu chi**

| Trường | Ví dụ |
|---------|-------|
| Payment to | `VENDOR001` |
| Amount | 11M (= 10M + 1M VAT) |
| Date | ngày chuyển |
| Account N | 331 |
| Account C | 111 (tiền mặt) hoặc 112 (ngân hàng) |

**Auto-post**: status = `ledger`.

### Chuyển khoản

- Tạo phiếu chi với C=1121
- Thực hiện chuyển khoản qua e-banking
- Import sao kê → đối soát

## 8. Đối soát ngân hàng

Sidebar → **Cập nhật số liệu → Ngân hàng & Đối soát**

1. Import sao kê CSV
2. Bấm **"Chạy auto-reconcile"**
3. Hệ thống match:
   - BankTransaction (credit - tiền ra) ↔ VoucherLine TK 331
   - BankTransaction (debit - tiền vào) ↔ VoucherLine TK 131

## 9. Báo cáo công nợ NCC

Sidebar → **Báo cáo → BCĐTK** → filter TK 331

**Aging analysis** (theo tuổi nợ):

```sql
-- Workaround via SQL
SELECT vendor_code, vendor_name,
       SUM(CASE WHEN DATEDIFF(NOW(), invoice_date) <= 30 THEN amount ELSE 0 END) AS d30,
       SUM(CASE WHEN DATEDIFF(NOW(), invoice_date) BETWEEN 31 AND 60 THEN amount ELSE 0 END) AS d60,
       SUM(CASE WHEN DATEDIFF(NOW(), invoice_date) BETWEEN 61 AND 90 THEN amount ELSE 0 END) AS d90,
       SUM(CASE WHEN DATEDIFF(NOW(), invoice_date) > 90 THEN amount ELSE 0 END) AS d90plus
FROM purchase_invoice
WHERE payment_status != 'paid'
GROUP BY vendor_code;
```

## 10. Voucher tự sinh theo bước

| Bước | Dr | Cr | Mô tả |
|------|----|----|-------|
| Nhập kho (chưa HĐ) | 152/156 | (chưa) | Nhận hàng |
| Hóa đơn mua | 156 / 1331 | 331 | Hạch toán HĐ |
| Thanh toán | 331 | 111/112 | Trả tiền NCC |
| CK có phí | 642 | 112 | Phí chuyển khoản |
| Chiết khấu NCC | 331 | 521 | Chiết khấu thanh toán |
| Trả hàng | 331 | 152/156 | Trả hàng cho NCC |

## 11. Audit trail

Mỗi bước có audit:
- PO → Contract
- GR → StockVoucher
- Invoice → PurchaseInvoice + Voucher
- Payment → CashPayment + Voucher
- Bank rec → ReconciliationMatch

Liên kết qua `party_code` (vendor) và `voucher_no`.

## 12. KPI

- **Cycle time**: từ PR → PO → GR → Invoice → Payment (mục tiêu ≤ 14 ngày)
- **On-time payment**: % HĐ trả đúng hạn
- **Early payment discount**: % tận dụng chiết khấu
- **3-way match rate**: % HĐ match PO/GR/Invoice

---

Tài liệu liên quan:
- [03-purchasing](../user-guide/03-purchasing.md) — Module mua hàng
- [12-banking](../user-guide/12-banking.md) — Đối soát ngân hàng
- [R1-monthly-close](01-monthly-close.md) — Chốt sổ tháng
