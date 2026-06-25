# Visota — Go-to-Market Strategy: Startup Niche

> Định vị: All-in-one ERP miễn phí năm đầu cho startup VN
> Cập nhật: 2026-06-26

## 1. Định vị cốt lõi

**"Công cụ all-in-one miễn phí cho doanh nghiệp mới thành lập — kế toán + HĐĐT + hợp đồng + CRM trong một chỗ."**

### Nỗi đau thật của startup VN

| Nhu cầu | Hiện dùng | Nỗi đau |
|---------|-----------|---------|
| Kế toán cơ bản | Excel / MISA ASP free | Excel dễ sai, MISA free giới hạn |
| Hóa đơn điện tử | meInvoice / VNPT / BKAV | Phải mua riêng, không liên thông sổ |
| Hợp đồng mẫu | Tải Google + sửa tay | Không chuẩn pháp lý, không có chữ ký |
| Quản lý khách hàng | Sổ tay / Zalo / Excel | Mất khách, không follow-up |
| Chữ ký số | VNPT/Viettel token | Phải cắm USB token |
| Báo cáo thuế | Tự tính + Excel | Sai → phạt, không biết TT133 |

**Họ không thiếu từng thứ riêng — họ thiếu một chỗ gom hết.**

### Khoảng trống thị trường

Không ai cho **tất cả miễn phí** cho năm đầu:
- MISA ASP free = chỉ kế toán cơ bản
- KiotViet free = POS + bán hàng (TT152, không TT133)
- Odoo Community = ERP mạnh nhưng không chuẩn VN

**Visota free = kế toán TT133 + HĐĐT + CRM + 21 mẫu hợp đồng + PWA mobile**


## 2. Phân khúc khách hàng & Upsell Path

```
NĂM 1 — KHỞI NGHIỆP (Revenue < 1 tỷ)
┌─────────────────────────────────────────┐
│ MIỄN PHÍ —不限 thời gian nếu < 1 tỷ     │
│                                          │
│ • Kế toán TT133 cơ bản                   │
│ • HĐĐT (kết nối provider thật)           │
│ • 5 mẫu hợp đồng cơ bản                  │
│ • CRM (leads + opportunities)            │
│ • Dashboard + PWA mobile                 │
│ • 2 user                                 │
│ • Notification + email                   │
└──────────────────┬──────────────────────┘
                   │ DN lớn dần, vượt 1 tỷ
                   ▼
NĂM 2-3 — TĂNG TRƯỞNG (Revenue 1-10 tỷ)
┌─────────────────────────────────────────┐
│ PROFESSIONAL — 3.990.000đ/năm           │
│                                          │
│ • Tất cả Starter +                       │
│ • Nhân sự + tính lương + PIT 2026       │
│ • BHXH 29% + D62                         │
│ • Ngân hàng + đối soát                   │
│ • Phiếu thu/chi + kho + TSCĐ             │
│ • Tất cả 21 mẫu hợp đồng + con dấu       │
│ • Báo cáo thuế TT80 + BCTC B01/B02       │
│ • 5 user                                 │
│ • Phê duyệt workflow                     │
└──────────────────┬──────────────────────┘
                   │ DN phức tạp hơn
                   ▼
NĂM 3+ — MỞ RỘNG (Revenue 10 tỷ+)
┌─────────────────────────────────────────┐
│ ENTERPRISE — 9.990.000đ/năm             │
│                                          │
│ • Tất cả Professional +                  │
│ • Quản lý dự án + đấu thầu               │
│ • Bảo lãnh ngân hàng                      │
│ • Vay vốn + lãi vay                       │
│ • Budget + cash flow forecast             │
│ • FX revaluation                          │
│ • API + webhook                           │
│ • 15 user                                 │
└─────────────────────────────────────────┘
```

**Logic chuyển đổi**: Startup dùng free → quen hệ thống → doanh thu tăng → cần thêm module → trả tiền. Chi phí chuyển đổi (data, quy trình, HTTK) giữ họ ở lại.


## 3. Module Packing theo Gói

| Module | Free (< 1 tỷ) | Pro (3,99tr) | Ent (9,99tr) |
|--------|:---:|:---:|:---:|
| Kế toán TT133 | ✓ | ✓ | ✓ |
| HĐĐT (provider thật) | ✓ | ✓ | ✓ |
| CRM (leads + opp) | ✓ | ✓ | ✓ |
| Hợp đồng (5 mẫu cơ bản) | ✓ | ✓ (21 mẫu) | ✓ (21 + custom) |
| Dashboard + PWA mobile | ✓ | ✓ | ✓ |
| Notifications + email | ✓ | ✓ | ✓ |
| Nhân sự + lương | — | ✓ | ✓ |
| Kho + TSCĐ | — | ✓ | ✓ |
| Ngân hàng + đối soát | — | ✓ | ✓ |
| Báo cáo thuế TT80 + BCTC | — | ✓ | ✓ |
| Phê duyệt workflow | — | ✓ | ✓ |
| Quản lý dự án | — | — | ✓ |
| Đấu thầu + bảo lãnh | — | — | ✓ |
| Vay vốn + FX + budget | — | — | ✓ |
| API + webhook | — | — | ✓ |
| User limit | 2 | 5 | 15 |


## 4. USP (Unique Selling Points)

### USP 1 — "All-in-one, không cần mua thêm"
Startup hiện ráp: Excel + meInvoice + Google Drive + Zalo + sổ tay = 5 hệ thống rời rạc.
Visota: kế toán + HĐĐT + hợp đồng + CRM = 1 hệ thống, bút toán tự sinh.

### USP 2 — "Miễn phí thật,不限 thời gian nếu < 1 tỷ"
MISA ASP free giới hạn tính năng. KiotViet free chỉ bán hàng.
Visota free cho kế toán TT133 + HĐĐT + CRM + hợp đồng.

### USP 3 — "Bút toán tự động — không cần biết kế toán"
Xuất HĐ bán → tự sinh N131/C5111/C33311 → tự vào sổ cái → tự ra BCTC.
Đối thủ: phải hạch toán thủ công hoặc semi-manual.

### USP 4 — "Lớn lên cùng Visota"
Năm 1: free. Năm 2: cần lương → 3,99tr. Năm 3: cần dự án → 9,99tr.
Không phải migrate sang phần mềm khác khi lớn.

### USP 5 — "PWA mobile — chủ xem doanh thu trên điện thoại"
Cài như app, offline mode, push notification. MISA ASP không có mobile.


## 5. Phân tích đối thủ

### Tầng Free (cạnh tranh trực tiếp)

| Đối thủ | Free có gì | Visota free có thêm |
|---------|-----------|---------------------|
| MISA ASP Starter | Kế toán cơ bản, 1 user | CRM, hợp đồng, mobile, 2 user |
| KiotViet kế toán | Sổ sách hộ KD (TT152) | TT133 chuẩn, HĐĐT, BCTC B01/B02 |
| Odoo Community | ERP mã nguồn mở | TT133 sẵn, không cần custom |

### Tầng SME (khi upsell)

| Đối thủ | Giá | Visota Pro có lợi gì |
|---------|-----|---------------------|
| MISA AMIS Standard | 4,55tr/3 user | 3,99tr/5 user + CRM + ngân hàng |
| FAST Online | 1,75-1,95tr | Module nhiều hơn, UI hiện đại hơn |
| Bravo ERP | 30tr+ | Rẻ 7x, module dự án/đấu thầu sẵn |

### Không đối đầu trực tiếp MISA
MISA có 30+ năm brand, 500+ đại lý, meInvoice.
Visota không cạnh tranh bằng "đẹp hơn" — cạnh tranh bằng **độ rộng module free** và **all-in-one**.


## 6. Tích hợp Provider (Ưu tiên)

| # | Provider | Thị phần HĐĐT | API | Thời gian | Commission |
|---|----------|--------------|-----|-----------|------------|
| **1** | meInvoice (MISA) | 60% | REST API công khai | 2 tuần | 10-15% |
| **2** | VNPT eInvoice | 20% | REST API | 2 tuần | 10-15% |
| **3** | Chữ ký số VNPT/Viettel | — | Remote sign API | 3 tuần | Deal riêng |
| **4** | Hub CQT (thuedientu) | — | XML upload | 4 tuần | Cần giấy phép |
| 5 | BKAV/SmartInvoice | 10% | REST API | 2 tuần | 10% |

**Chìa khóa deal**: Visota = đại lý phân phối HĐĐT. Mỗi startup đăng ký Visota → tự động đăng ký HĐĐT → provider có khách mới.


## 7. Kênh tiếp cận Startup VN

| Kênh | Chi phí | Kỳ vọng năm 1 | Chiến thuật |
|------|---------|---------------|------------|
| **Startup hub/incubator** | 0đ | 50-100 startup | Hợp tác Saigon Innovation Hub, BSSC, SIHUB |
| **Đại lý HĐĐT** | Commission | 100-200 lead | Provider giới thiệu Visota khi khách mới đăng ký |
| **Kế toán dịch vụ** | 0đ | 100-300 startup | Multi-tenant — 1 KTV quản lý 10-30 startup |
| **Group FB khởi nghiệp** | 0đ | 50-100 lead | "Công cụ all-in-one free cho startup" |
| **GitHub open source** | 0đ | 10-20 tech startup | Self-host cho DN có IT team |
| **Workshop đăng ký DN** | 5tr/event | 20-30 lead | Hợp tác dịch vụ thành lập DN |
| **SEO blog** | 5tr/tháng | 50-100 lead | "Phần mềm kế toán free", "Tạo HĐĐT online" |
| **YouTube** | 5tr/tháng | 30-50 lead | "Hướng dẫn kế toán TT133 trong 5 phút" |

**Ngân sách năm 1**: 120-200tr (content + ads + event)
**Mục tiêu năm 1**: 200-500 startup đăng ký free → 30-50 chuyển Pro/Ent


## 8. Điều Kiện Tiên Quyết Trước Khi Launch

| # | Phải có | Hiện trạng | Effort |
|---|---------|-----------|--------|
| 1 | **HĐĐT thật** (meInvoice/VNPT API) | Stub XML/JSON | 2 tuần |
| 2 | **Chữ ký số** (VNPT/Viettel) | Chưa có | 3 tuần |
| 3 | **PKM dùng thật** (case study #1) | Chưa dùng | 4 tuần dogfood |
| 4 | **Onboarding wizard** (signup → HĐ đầu tiên trong 10') | Chưa có | 1 tuần |
| 5 | **Migration tool** (Excel MISA → Visota) | Chưa có | 1 tuần |
| 6 | **Support channel** (Zalo OA + hotline + email) | Chưa có | 2 ngày |
| 7 | **Demo online** (visota.net/demo) | Chưa deploy | 2 ngày |
| 8 | **Tài liệu video** (5 video hướng dẫn cơ bản) | Chưa có | 1 tuần |


## 9. Lộ Trình Thực Hiện

### Tuần 1-2: HĐĐT thật
- Chọn provider (meInvoice hoặc VNPT)
- Đọc API docs
- Implement `EInvoiceService._call_provider_api()` thật
- Test phát hành HĐ thật trên môi trường test provider

### Tuần 3-4: Chữ ký số
- Deal với VNPT hoặc Viettel
- API remote signing (không cần USB token)
- Integrate vào flow xuất HĐ + hợp đồng

### Tuần 5: Onboarding wizard
- `/signup` → 5 step wizard
- Auto-seed HTTK TT133 + 5 mẫu HĐ cơ bản
- Welcome notification

### Tuần 6: Migration tool
- Import Excel từ MISA/Fast: khách hàng, NCC, số dư đầu kỳ, HĐ mua/bán

### Tuần 7-8: Deploy + dogfood PKM
- Deploy visota.net thật
- PKM dùng nội bộ làm công ty đầu tiên
- Xuất HĐ thật, nộp thuế thật
- Ghi lại = case study

### Tuần 9-10: Launch free tier
- Mở đăng ký visota.net
- 100-200 startup đầu tiên free
- Thu feedback, fix bugs

### Tháng 3-6: Mở rộng
- Hợp tác startup hub
- Đại lý HĐĐT giới thiệu
- Kế toán dịch vụ multi-tenant
- 200-500 startup đăng ký

### Tháng 6-12: Upsell
- Startup vượt 1 tỷ → suggest Professional
- Thêm module nhân sự/lương/kho
- 30-50 chuyển Pro/Enterprise


## 10. Mô Hình Doanh Thu Dự Kiến

| Năm | Free users | Pro users | Ent users | Doanh thu |
|-----|-----------|-----------|-----------|-----------|
| **1** | 300 | 5 | 2 | ~40tr |
| **2** | 800 | 50 | 10 | ~300tr |
| **3** | 1.500 | 200 | 30 | ~1,1 tỷ |
| **4** | 3.000 | 500 | 80 | ~2,8 tỷ |
| **5** | 5.000 | 1.000 | 150 | ~5,5 tỷ |

**Lưu ý**: Doanh thu đến từ upsell + commission HĐĐT + phí triển khai.
Free tier là acquisition channel, không phải cost center.


## 11. Rủi Ro & Khắc Phục

| Rủi ro | Mức độ | Khắc phục |
|--------|--------|-----------|
| HĐĐT provider không deal được | 🔴 | Có 5 provider — deal ít nhất 1 |
| Startup không chuyển từ Excel | 🟡 | Migration tool 1-click + wizard |
| MISA ra gói free tương tự | 🟡 | Visota có module CRM/dự án MISA không có |
| Chi phí VPS khi nhiều free user | 🟡 | Django + MariaDB nhẹ — 2K users/VPS 2GB RAM |
| Luật thuế đổi | 🟡 | Newsletter + code patch nhanh |
| Support quá tải | 🟡 | FAQ + video + chatbot AI (phase 2) |
