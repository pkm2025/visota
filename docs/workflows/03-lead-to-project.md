# W3 — Lead to Project: CRM → Dự án

> Workflow chuyển từ cơ hội bán hàng (Opportunity) thành dự án (Project).

## Sơ đồ tổng thể

```
[Lead]
   ↓ qualify
[Opportunity] (Cơ hội bán hàng)
   ↓ won
   ├─→ [Customer] (auto-create)
   ├─→ [Contract] (auto-create)
   ├─→ [Project] (auto-create, PM assigned)
   └─→ [SalesInvoice draft] (auto-create)
       ↓
[Project phases] (Giai đoạn)
   ↓ tracking
[Project resources] (Nhân sự + vật tư)
   ↓ tracking
[Project transactions] (Chi phí thực tế)
   ↓
[Milestone delivery + Invoice]
   ↓
[Project close] → Profit/Loss report
```

## 1. Lead → Opportunity → Won

Xem chi tiết: [W2-order-to-cash](02-order-to-cash.md) section 1-2.

## 2. Won → Auto-convert

Sidebar → chi tiết Opportunity → bấm **"Convert"**

Hệ thống tự động:

### 2.1. Customer

- Nếu KH đã có (lookup by tax_code) → reuse
- Nếu chưa → tạo mới với thông tin từ Opportunity

### 2.2. Contract

```
contract_no: HĐ-<opp.code>
contract_type: service (mặc định cho IT)
party_code: <customer code>
party_name: <customer name>
value: <opp.estimated_value>
start_date: today
end_date: today + <estimated_duration_days>
status: active
```

### 2.3. Project

```
code: PRJ-<opp.code>
name: <opp.name>
customer_code: <customer code>
contract: <contract vừa tạo>
manager: <current user> → require Employee record
budget_revenue: <opp value>
budget_cost: <estimated cost ~70% revenue>
status: active
```

### 2.4. SalesInvoice draft

```
invoice_no: HĐ-<opp.code>
customer: <customer>
lines: copy từ OpportunityLine
status: draft (chưa post)
```

User phải vào edit + bấm Save mới post.

## 3. Cấu hình Project

Sidebar → **Dự án** → chi tiết project

### 3.1. Phases (Giai đoạn)

Template 6 phases cho dự án IT:

| # | Phase | Weight | Description |
|---|-------|--------|-------------|
| 1 | Discovery & Design | 10% | Khảo sát + thiết kế |
| 2 | Procurement | 20% | Mua thiết bị |
| 3 | Infrastructure setup | 15% | Cáp + rack + điện |
| 4 | Active equipment install | 25% | Server + switch + storage |
| 5 | HA config + Testing | 20% | Cấu hình + test |
| 6 | Handover + Training | 10% | Bàn giao + đào tạo |

Progress tự tính = sum(weight × is_completed) / 100.

### 3.2. Resources

Thêm nhân sự + vật tư:

| Loại | Ví dụ |
|------|-------|
| Human | PM 30 ngày @ 2.5M |
| Human | Kỹ sư hạ tầng 45 ngày @ 1.8M |
| Human | Kỹ sư mạng 30 ngày @ 1.8M |
| Material | Cáp quang + vật tư 1 lot @ 35M |
| Equipment | (đã mua qua PurchaseInvoice) |

Mỗi resource gắn vào phase (auto-track cost per phase).

### 3.3. Đặt Project Manager

Project → edit → chọn Employee (FK).

Employee phải có record trong HR module.

## 4. Tracking tiến độ

### Đánh dấu phase hoàn thành

Detail project → phases → checkbox `is_completed` → bấm **Save**.

Hệ thống tự:
- Tính lại `progress_percent`
- Tạo `ProjectTransaction` nếu có cost
- Fire notification cho PM + Customer (tùy chọn)

### Thêm chi phí phát sinh

Tạo `PurchaseInvoice` gắn với project:

```
PurchaseInvoice → contract = <project contract>
→ auto-track vào project.actual_cost
```

Hoặc tạo voucher trực tiếp: N622/C111 với note `project:PRJ-xxx`.

## 5. Milestone billing

### Theo progress

VD: contract 1B VND, 6 phases:

| Milestone | Trigger | Invoice amount |
|-----------|---------|----------------|
| Kickoff | Hợp đồng ký | 30% = 300M |
| Phase 4 done | Lắp đặt xong | 30% = 300M |
| UAT pass | User accept test | 20% = 200M |
| Go-live | Bàn giao | 15% = 150M |
| Warranty end | Sau 12 tháng | 5% = 50M |

Mỗi milestone → tạo SalesInvoice riêng → auto-post → HĐĐT.

## 6. Theo dõi lợi nhuận

Sidebar → **Dự án → <code>** → Card "Budget vs Actual":

| Hạng mục | Budget | Actual | Variance |
|----------|--------|--------|----------|
| Revenue | 1,000M | 600M (chưa bàn giao hết) | -400M (còn phải xuất HĐ) |
| HR cost | 200M | 180M | +20M (dưới budget) |
| Material | 350M | 380M | -30M (vượt) |
| Equipment | 300M | 300M | 0 |
| Other | 50M | 45M | +5M |
| **Profit** | **100M (10%)** | **-5M (-0.8%)** | -105M (cần xem lại) |

## 7. Project close

Khi tất cả phases done + cuối cùng bàn giao:

1. Verify tất cả SalesInvoice đã post
2. Verify tất cả PurchaseInvoice đã post
3. Verify tất cả project resources đã có actual_cost
4. Tạo SalesInvoice cuối (warranty retention nếu có)
5. Set project status = `completed`
6. Tạo ProjectTransaction cho từng phase đánh dấu done

## 8. Báo cáo

| Report | Use |
|--------|-----|
| Project list | PM xem tất cả dự án |
| Project detail | Drill-down 1 project |
| Resource utilization | HR cost across projects |
| Project margin | Finance xem P/L |
| Phase tracking | PM report KH |

## 9. Tích hợp với module khác

### PurchaseInvoice → Project

Khi mua thiết bị cho project:

```
PurchaseInvoice → contract = <project contract> (link)
→ tự động cộng vào project.actual_cost
```

### Timesheet → Project (planned)

Hiện chưa có module timesheet. Workaround:
- ProjectResource có `actual_quantity` (vs planned)
- Update qua UI khi NV báo cáo

### SalesInvoice → Project

Mỗi SalesInvoice có `project_id` (planned). Workaround: link qua `contract`.

## 10. Notification flow

| Event | Notify ai |
|-------|-----------|
| Project tạo | PM + Customer (account_manager) |
| Phase done | PM + Sale lead |
| Cost exceed budget | PM + KTT |
| SalesInvoice issued | Customer + Sales |
| Payment received | PM + Finance |
| Project closed | All stakeholders |

## 11. Workflow cho hợp đồng IT services

Quy trình PMK thực tế:

```
T0    Hợp đồng ký → Project tạo + Phase 1 active
T0+1  PM contact KH chốt kickoff → phase 1 done
T0+2  Mua sắm thiết bị (PurchaseInvoice) → phase 2 done
T0+4  Thi công hạ tầng → phase 3 done
T0+5  Lắp đặt active → phase 4 done → 30% invoice
T0+7  Cấu hình + UAT → phase 5 done → 20% invoice
T0+9  Bàn giao + training → phase 6 done → 15% invoice
T+12m Hết bảo hành → 5% invoice → close project
```

## 12. KPI Project

- **Schedule**: phases done đúng plan date
- **Budget**: actual ≤ budget
- **Quality**: số ticket bug trong warranty
- **Customer satisfaction**: NPS
- **Margin**: ≥ 15% là tốt

---

Tài liệu liên quan:
- [09-projects](../user-guide/09-projects.md) — User guide dự án
- [08-crm](../user-guide/08-crm.md) — CRM
- [07-contracts](../user-guide/07-contracts.md) — Hợp đồng
- [W2-order-to-cash](02-order-to-cash.md) — Workflow O2C đầy đủ
