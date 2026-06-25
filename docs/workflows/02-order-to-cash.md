# W2 — Order-to-Cash (O2C): Đặt đến Thu

> Workflow đầy đủ từ lead → contract → delivery → invoice → collection.

## Sơ đồ tổng thể

```
[Lead] (CRM)
   ↓ qualify
[Opportunity] (Cơ hội)
   ↓ negotiate
[Quote] (Báo giá)
   ↓ won
[Contract] (Hợp đồng)
   ↓ auto-create
[Project] (Dự án) + [SalesInvoice draft]
   ↓
[Delivery] (StockVoucher xuất kho)
   ↓
[SalesInvoice posted] (Hóa đơn bán)
   ↓ auto-voucher N131/C5111/C33311
[Voucher kế toán]
   ↓
[Phát hành HĐĐT] (E-Invoice)
   ↓
[Customer pays]
   ↓
[CashReceipt N111/C131] (Phiếu thu)
   ↓
[Đối soát sao kê ngân hàng]
   ↓
[BC công nợ KH 131]
```

## 1. Lead → Opportunity

Sidebar → **CRM → Khách tiềm năng**

### Tạo Lead

| Trường | Ví dụ |
|---------|-------|
| Lead code | `LD-2026-001` |
| Full name | `Nguyễn Văn A` |
| Job title | `Trưởng phòng CNTT` |
| Company name | `Bệnh viện X` |
| Source | `referral` / `website` / `cold_call` |
| Status | `new` |

### Convert Lead → Opportunity

Bấm **"Convert"** trên Lead:
- Tự động tạo `CRMAccount`
- Tạo `Opportunity` link với account

## 2. Quản lý Opportunity

Sidebar → **CRM → Cơ hội bán hàng**

### Cập nhật

| Trường | Mô tả |
|---------|-------|
| Stage | `identification` → `qualification` → `negotiation` → `won`/`lost` |
| Estimated value | Tổng ước tính |
| Probability | % thắng |
| Expected close | Ngày dự kiến close |

### Lines (dự kiến scope)

Thêm các line:
- Product/service
- Số lượng
- Đơn giá

Hệ thống tự tính `estimated_value`.

## 3. Won → Auto-create Contract + Project + Invoice

Khi opportunity stage = `won`:

Sidebar → chi tiết opportunity → bấm **"Convert"** → tự động:

1. Tạo `Customer` (nếu chưa)
2. Tạo `Contract` với các line từ opportunity
3. Tạo `Project` gắn với contract (PM tự động là người tạo)
4. Tạo `SalesInvoice` draft với lines từ opportunity

## 4. Bàn giao + Xuất kho

Nếu có hàng hóa (không chỉ dịch vụ):

Sidebar → **Nghiệp vụ → Phiếu nhập xuất**

Tạo phiếu xuất:
```
Type: sales_issue
Date: <ngày giao>
Customer: <code>
Lines:
  - Product: SKU1, qty=10, unit_cost=...
```

**Auto-voucher**:
- N632 (giá vốn) / C156 (kho)

## 5. Phát hành hóa đơn

Sidebar → **Nghiệp vụ → Hóa đơn bán**

Hoặc từ chi tiết `SalesInvoice` (đã auto-tạo từ Opportunity).

Verify:
- Đúng customer
- Đúng tổng tiền
- Đúng VAT rate

Bấm **Lưu** → tự động post + auto-voucher N131/C5111/C33311.

## 6. Phát hành HĐĐT

Từ chi tiết `SalesInvoice` → bấm **"Phát hành HĐĐT"**

Xem chi tiết: [10-einvoice](../user-guide/10-einvoice.md)

Workflow:
1. Tạo `EInvoice` draft (XML + JSON TT78)
2. User verify nội dung
3. Bấm **"Phát hành"** → status = `issued`
4. (Manual mode) Upload PDF đã ký
5. Gửi HĐĐT (PDF + XML) cho KH qua email

## 7. Theo dõi công nợ

### Aging report

```
/modern/sales-invoices/?payment_status__not=paid
```

Filter:
- Hôm nay đến hạn
- Quá hạn < 30 ngày
- Quá hạn 30-60 ngày
- Quá hạn 60+ ngày (escalate)

### Action khi quá hạn

- 0-30 ngày: gọi điện reminder
- 31-60 ngày: email formal + không xuất HĐ mới
- 61-90 ngày: đề xuất thu hồi nợ (liên hệ pháp chế)
- 90+ ngày: litigate

## 8. Thu tiền

Sidebar → **Cập nhật số liệu → Phiếu thu**

### Tạo CashReceipt

| Trường | Ví dụ |
|---------|-------|
| Receipt from | `CUST001` |
| Amount | 110M (= 100M + 10M VAT) |
| Date | ngày thu |
| Account N | 111 hoặc 112 |
| Account C | 131 |
| Note | "Thu theo HĐ HĐ001" |

**Auto-update**: SalesInvoice `paid_amount` tăng, `payment_status` cập nhật.

### Đối soát ngân hàng

Nếu KH chuyển khoản → import sao kê → auto-match với phiếu thu.

## 9. Tính KQ lỗ/lãi cho HĐ/Project

Sidebar → **Dự án → <project code>**

Xem:
- **Doanh thu**: tổng SalesInvoice đã post
- **Chi phí**:
  - Chi phí nhân sự (ProjectResource × days × daily_rate)
  - Vật tư (PurchaseInvoice gắn project)
  - Chi phí khác
- **Margin**: (revenue - cost) / revenue

## 10. Voucher tự sinh theo bước

| Bước | Dr | Cr | Mô tả |
|------|----|----|-------|
| Xuất kho | 632 | 156 | Giá vốn hàng bán |
| Phát hành HĐ bán | 131 | 5111 | Doanh thu |
|  | 131 | 33311 | VAT đầu ra |
|  | (nếu có) 521 | 131 | Chiết khấu |
| Thu tiền | 111/112 | 131 | Khách trả |
| CK có phí | 642 | 112 | Phí ngân hàng |
| Trả hàng | 5111 | 131 | KH trả lại hàng |
| Bad debt | 2293 | 131 | Tạm ứng xóa sổ |

## 11. KPI

- **Cycle time**: Lead → Won → Paid (mục tiêu ≤ 60 ngày)
- **Win rate**: Won / (Won + Lost)
- **DSO** (Days Sales Outstanding): AR balance / revenue × 365
- **Collection rate**: % HĐ đúng hạn
- **Average deal size**: total revenue / num deals

## 12. Workflow cho sale dịch vụ (IT company)

Đặc thù PKM — bán dịch vụ CNTT:

1. **Lead** từ referral / website
2. **Discovery call** (track trong CRM Activity)
3. **Proposal** (PDF, export từ Contract template)
4. **Negotiation** (track trong Opportunity lines)
5. **Won** → tạo Contract + Project
6. **Kickoff** Project → phases
7. **Delivery** theo phases → bàn giao từng phase
8. **Invoice** theo milestone (50% kickoff, 30% phase 4 done, 20% handover)
9. **Collection** theo payment schedule trong contract
10. **Warranty** (12 tháng) — track qua Ticket

## 13. Audit trail

| Event | Object | Link |
|-------|--------|------|
| Lead tạo | CRMLead | `/modern/crm/leads/` |
| Convert | Opportunity → Customer | opp.code + cust.code |
| Won → Contract | Contract → Opp | contract.opportunity_id |
| Won → Project | Project → Contract | project.contract_id |
| Invoice issue | SalesInvoice → Contract | si.contract_id |
| Payment | CashReceipt → Invoice | cr.lines[].object_code = invoice |

---

Tài liệu liên quan:
- [02-sales](../user-guide/02-sales.md) — Bán hàng chi tiết
- [08-crm](../user-guide/08-crm.md) — CRM chi tiết
- [09-projects](../user-guide/09-projects.md) — Quản lý dự án
- [10-einvoice](../user-guide/10-einvoice.md) — Hóa đơn điện tử
