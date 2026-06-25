# Visota — Feature Gap Analysis cho Startup Niche

> Phân tích khách quan: có gì, thiếu gì, cần hoàn thiện gì
> Đối tượng: startup VN, doanh thu < 1 tỷ, chủ DN không phải kế toán

## Phân tích theo hành trình startup

### Tuần 1: Mở công ty → Giao dịch đầu tiên

| Hành động | Cần gì | Visota có? | Gap |
|-----------|--------|-----------|-----|
| Nhập thông tin công ty | Wizard 5 bước: tên + MST + địa chỉ + ngành + HTTK | ❌ Không có onboarding | **P0 — Onboarding wizard** |
| Tự sinh HTTK TT133 | Auto-seed 116 TK theo ngành | ✓ Có seed_tt133 nhưng không auto chạy | **P1 — Auto-seed khi tạo company** |
| Tạo khách hàng đầu tiên | Form đơn giản: tên + SĐT + MST | ✓ Có customer form | OK |
| Xuất hóa đơn đầu tiên | Tạo HĐ bán → phát hành HĐĐT thật | ✓ Form có + ❌ HĐĐT stub | **P0 — HĐĐT provider thật** |
| Gửi HĐ cho khách | Email HĐ PDF đính kèm | ❌ Không auto-email | **P1 — Auto-email HĐ** |

### Tháng 1: Vận hành hàng ngày

| Hành động | Cần gì | Visota có? | Gap |
|-----------|--------|-----------|-----|
| "Ai nợ tôi tiền?" | Bảng công nợ aging: 0-30/31-60/60+ ngày | ❌ Không có aging report | **P0 — AR Aging dashboard** |
| "Tôi còn bao nhiêu tiền?" | Cash balance: tiền mặt + ngân hàng | ⚠️ Có số liệu nhưng không tóm tắt | **P1 — Cash position widget** |
| "Tháng này lãi/lỗ bao nhiêu?" | P&L đơn giản: thu - chi = lãi | ✓ Có B02 nhưng phức tạp | **P1 — Simple P&L card** |
| "Khi nào nộp thuế?" | Lịch thuế: VAT 20th, PIT 20th, BHXH cuối tháng | ❌ Không có calendar | **P0 — Tax calendar** |
| "Nhắc tôi nộp thuế!" | Push notification trước hạn | ✓ Có notification system | **P1 — Auto tax reminder** |
| Chụp ảnh hóa đơn | Mobile: chụp → OCR → tự hạch toán | ❌ Không có | **P2 — Receipt OCR (phase 2)** |

### Tháng 2-3: Phức tạp hơn

| Hành động | Cần gì | Visota có? | Gap |
|-----------|--------|-----------|-----|
| Thuê nhân viên đầu tiên | Tạo NV → HĐLĐ mẫu → tính lương đơn giản | ✓ Có HR + payroll | OK (cần đơn giản hóa form) |
| Ký hợp đồng với đối tác | Chọn mẫu → điền → PDF → email | ✓ Có 21 mẫu | OK |
| Theo dõi chi phí | Nhập chi nhanh: số tiền + mô tả + ảnh | ❌ Quá phức tạp (cần tạo voucher) | **P1 — Quick expense entry** |
| Lưu trữ chứng từ | Upload PDF/ảnh → tìm kiếm được | ✓ Có attachment system | OK (cần улучшить UX) |
| Báo cáo thuế | Sinh tờ khai VAT/PIT 1 click | ✓ Có report views | OK (cần pre-fill từ data) |

### Tháng 6+: Chuẩn bị lớn dần

| Hành động | Cần gì | Visota có? | Gap |
|-----------|--------|-----------|-----|
| Quản lý nhiều nhân viên | Bulk import NV + auto PIT | ✓ Có payroll | OK |
| Mở CRM đơn giản | Ai là khách tiềm năng? Ai chưa chốt? | ✓ Có CRM | OK (cần đơn giản hơn) |
| Ngân hàng đối soát | Import sao kê → match | ✓ Có banking module | OK |
| Thay accountant | Người mới hiểu nhanh | ❌ Không có audit trail UI | **P2 — Activity log** |

---

## 10 tính năng PRIORITY — Xếp theo tác động vs effort

### P0 — Chặn launch (phải có)

#### 1. Onboarding Wizard
**Tại sao**: Startup đăng ký → thấy form kế toán phức tạp → bỏ. Cần flow 5 bước.

```
/signup
  Step 1: Email + password
  Step 2: Tên công ty + MST + địa chỉ
  Step 3: Chọn ngành (TM/DV/SX/XD/IT)
    → Auto-seed HTTK TT133 phù hợp
  Step 4: Kết nối HĐĐT (chọn provider + API key)
  Step 5: Chào mừng → "Tạo khách hàng đầu tiên"
```
**Effort**: 3-5 ngày
**Files**: `apps/public/views.py` (SignupView), `templates/public/signup.html`

#### 2. HĐĐT Provider Thật
**Tại sao**: Không có = không xuất hóa đơn = vô dụng cho startup.

**Cần**: Implement `EInvoiceService._call_provider_api()` thật với meInvoice hoặc VNPT.

**Effort**: 2 tuần (đọc API docs + implement + test trên môi trường provider)

#### 3. AR Aging Dashboard
**Tại sao**: Startup chết vì thiếu tiền mặt, không vì thiếu doanh thu. Cần biết AI nợ, bao lâu.

**Cần**: Widget trên dashboard:
```
CÔNG NỢ PHẢI THU
├── Chưa đến hạn:  45.000.000đ  (3 KH)
├── Quá hạn 1-30:  12.000.000đ  (1 KH) ← màu vàng
├── Quá hạn 31-60:  8.000.000đ  (1 KH) ← màu cam
└── Quá hạn 60+:   25.000.000đ  (2 KH) ← màu đỏ
```
**Effort**: 2-3 ngày
**Files**: `apps/ui_modern/views/dashboard_views.py`, `templates/modern/dashboard/index.html`

#### 4. Tax Calendar + Auto Reminder
**Tại sao**: Sai hạn thuế = phạt. Startup không nhớ ngày 20 hàng tháng.

**Cần**:
- Widget dashboard: "Nộp VAT T06 trước 20/07" (3 ngày nữa!)
- Auto notification 7 ngày + 1 ngày trước hạn
- Loại thuế: VAT (20th), PIT (20th), BHXH (cuối tháng), TNDN (quý)

**Effort**: 3-4 ngày
**Files**: `apps/public/models.py` (TaxDeadline model), cron job qua django-q2

---

### P1 — Tăng retention (nên có trong tháng đầu)

#### 5. Cash Position Widget
**Tại sao**: "Tôi còn bao nhiêu tiền?" = câu hỏi #1 của chủ startup mỗi sáng.

**Cần**: Dashboard card:
```
TIỀN HIỆN CÓ: 85.000.000đ
  Tiền mặt (TK 111):  5.000.000đ
  VCB (TK 1121):     60.000.000đ
  TCB (TK 1122):     20.000.000đ
```
**Effort**: 1-2 ngày (query AccountPeriodBalance TK 111/112)

#### 6. Simple P&L Card
**Tại sao**: B02-DN phức tạp. Startup chỉ cần "tháng này thu X, chi Y, lãi Z".

**Cần**: Dashboard card:
```
THÁNG 06/2026
  Doanh thu:   +150.000.000đ
  Chi phí:      -95.000.000đ
  ─────────────────────────
  LỖI/LÃI:     +55.000.000đ
```
**Effort**: 1 ngày (query sum PS TK 511 vs 632+641+642)

#### 7. Quick Expense Entry
**Tại sao**: Muốn ghi "ăn trưa với khách 500k" → phải tạo voucher 6 dòng. Quá phức tạp.

**Cần**: Form 1 dòng trên dashboard:
```
[Chi phí nhanh]
Số tiền: [500.000]  Loại: [Marketing ▼]  Mô tả: [Ăn trưa KH]
→ Tự sinh voucher N641/C111, không cần biết hạch toán
```
**Effort**: 2-3 ngày
**Files**: `apps/ui_modern/views/dashboard_views.py` (QuickExpenseView)

#### 8. Auto-Email HĐ/Contract
**Tại sao**: Xuất HĐ xong phải download PDF rồi gửi email thủ công. Startup muốn 1 click.

**Cần**: Button "Gửi email cho khách" trên HĐ detail → auto-attach PDF + nội dung mẫu.

**Effort**: 1-2 ngày
**Files**: `apps/notifications/services.py` (extend), template email

#### 9. Startup Dashboard (thay kế toán dashboard)
**Tại sao**: Dashboard hiện tại = "Chứng từ hôm nay / Công nợ KH / Tồn kho" — góc nhìn kế toán. Startup cần góc nhìn CEO.

**Cần**: Redesign dashboard cho 3 persona:
- **CEO view**: Tiền + doanh thu + AR aging + tax deadline
- **Kế toán view**: Voucher + sổ cái + báo cáo (hiện tại)
- **Sales view**: Pipeline + lead + opportunity

Auto-chọn view theo role hoặc toggle button.

**Effort**: 3-5 ngày (redesign + 3 variants)

---

### P2 — Khác biệt hóa (3-6 tháng)

#### 10. Startup Knowledge Base
**Tại sao**: Chủ startup không biết TT133 là gì. Cần cẩm nang tích hợp trong app.

**Cần**: `/modern/help/` với bài viết:
- "HĐĐT là gì? Cấu hình lần đầu"
- "Cách hạch toán theo TT133"
- "Nộp thuế GTGT — hướng dẫn từng bước"
- "Thuê nhân viên đầu tiên — thủ tục gì?"

Tích hợp vào context — khi user ở trang HĐĐT, hiện tooltip "Cần giúp? Xem hướng dẫn".

**Effort**: 1 tuần content + 2 ngày dev
**Files**: `apps/public/models.py` (re-use BlogArticle), help templates

---

## Tính năng hiện tại cần hoàn thiện

### A. Voucher Form — Quá phức tạp cho non-accountant

**Vấn đề**: Form tạo phiếu kế toán hiện tại yêu cầu user biết TK Nợ/Có, dòng bút toán, cân đối Nợ=Có.

**Giải pháp**: Thêm "Guided Mode":
```
Thay vì:
  [Loại phiếu] [TK Nợ] [TK Có] [Số tiền]...

Thêm:
  "Bạn muốn làm gì?"
  ☐ Thu tiền từ khách hàng
  ☐ Chi tiền mua hàng
  ☐ Trả lương nhân viên
  ☐ Khác (advanced mode)
  
  → Chọn "Thu tiền" → chỉ cần:
  [Khách hàng ▼] [Số tiền] [HĐ số] 
  → Hệ thống tự sinh N111/C131
```
**Effort**: 1 tuần

### B. CRM — Quá nặng cho startup

**Vấn đề**: CRM hiện có Lead → Opportunity → Ticket → Campaign. Startup chỉ cần "danh sách khách hàng + ai nợ bao nhiêu".

**Giải pháp**: Simplify mode — ẩn Campaign, Ticket. Chỉ hiện:
- Khách hàng (list + công nợ)
- Cơ hội (đang theo)
- Khi DN lớn → mở full CRM

**Effort**: 2 ngày (conditional template)

### C. Contract Templates — Đủ nhưng khó tìm

**Vấn đề**: 21 mẫu, startup không biết chọn mẫu nào.

**Giải pháp**: Thêm "wizard chọn mẫu":
```
"Bạn cần tạo gì?"
☐ Hợp đồng với nhân viên → HĐLĐ
☐ Hợp đồng với khách hàng → HĐ dịch vụ / mua bán
☐ Biên bản → nghiệm thu / bàn giao / thanh lý
☐ Quyết định → nâng lương / điều chuyển

→ Tự suggest mẫu phù hợp
```
**Effort**: 1-2 ngày

### D. Mobile — Có PWA nhưng thiếu tính năng thiết yếu

**Vấn đề**: PWA có bottom nav + offline, nhưng thiếu tính năng quan trọng nhất trên mobile:
- Xem "bao nhiêu tiền" (1 glance)
- Chụp ảnh hóa đơn → lưu
- Duyệt phiếu (approve/reject)

**Giải pháp**: Thêm Mobile Home Screen riêng:
```
┌─────────────────────┐
│  TIỀN: 85,000,000đ  │
│  DOANH THU T6: 150M │
│  CÔNG NỢ: 65M       │
├─────────────────────┤
│ 📸 Chụp hóa đơn     │
│ ✅ Duyệt (2)        │
│ 📊 Xem báo cáo      │
│ 💬 Thông báo (3)    │
└─────────────────────┘
```
**Effort**: 3-4 ngày

---

## Summary: Priority Matrix

```
        TÁC ĐỘNG CAO
             │
    ┌────────┼────────┐
    │  P0    │   P1   │
    │        │        │
    │ #1 Wizard    #5 Cash     │
    │ #2 HĐĐT      #6 P&L      │
    │ #3 AR Aging  #7 Expense  │
    │ #4 Tax Cal   #8 Email    │
    │              #9 Dashboard│
    │              #10 KB      │
    ├────────┼────────┤
    │ P3     │  P2    │
    │        │        │
    │ OCR    │ Simplify│
    │ AI     │ CRM    │
    │ API    │ Mobile │
    └────────┼────────┘
             │
        TÁC ĐỘNG THẤP
    
    ←── ITỂU EFFORT    NHIỀU EFFORT ──→
```

### Thứ tự thực hiện

| Tuần | Tính năng | Effort | Tác động |
|------|-----------|--------|----------|
| **1** | #3 AR Aging + #5 Cash + #6 P&L | 4 ngày | Dashboard tức khắc hữu dụng |
| **2** | #4 Tax Calendar + #7 Quick Expense | 5 ngày | Startup thực sự dùng hàng ngày |
| **3** | #1 Onboarding Wizard | 5 ngày | Mở đăng ký được |
| **4** | #2 HĐĐT thật (meInvoice/VNPT) | 2 tuần | Chặn sale = giải quyết |
| **5** | #8 Auto-email + #9 Dashboard variants | 4 ngày | Retention |
| **6** | #10 Knowledge Base + Mobile Home | 5 ngày | Khác biệt hóa |
| **7** | Guided Voucher Mode | 5 ngày | Non-accountant dùng được |
| **8** | Simplify CRM + Contract Wizard | 3 ngày | UX tốt hơn |

**Total**: 8 tuần → từ codebase "chạy được" → "sẵn sàng cho 100 startup đầu tiên"
