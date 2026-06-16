# 01. Các chế độ kế toán tại Việt Nam

> Tổng quan các văn bản pháp lý kế toán VN liên quan đến phần mềm.

## 1. Khung pháp lý

```
┌─────────────────────────────────────────────────────┐
│  Luật Kế toán 88/2015/QH13 (hiệu lực 01/01/2017)    │
│  Luật sửa đổi LTk 2024                              │
└─────────────────────────────────────────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ↓                  ↓                  ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Doanh nghiệp│    │ Đơn vị HCSN│    │ Ngân hàng,  │
│             │    │             │    │ tổ chức TC │
└─────────────┘    └─────────────┘    └─────────────┘
       ↓
┌──────────────────────────────────────────────────────┐
│  Chuẩn mực kế toán Việt Nam (VAS)                    │
│  - 26 VAS (từ 2001-2005)                             │
│  - VAS 27 (2021): HĐBC                              │
└──────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────┐
│  Chế độ kế toán doanh nghiệp                         │
│  - TT200/2014: DN lớn (tùy chọn DN nhỏ)              │
│  - TT133/2016: DN nhỏ và vừa (bắt buộc)              │
│  - QĐ48/2006: DN nhỏ và vừa (cũ, vẫn dùng)          │
│  - QĐ15/2006: DN nhà nước                            │
│  - TT107/2020: Hợp tác xã                            │
└──────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────┐
│  Văn bản về thuế & hóa đơn                           │
│  - TT80/2021: Tờ khai thuế GTGT (01/GTGT)           │
│  - TT78/2021 → TT32/2025: Hóa đơn điện tử           │
│  - ND123/2020, ND109/2022: Hóa đơn                   │
└──────────────────────────────────────────────────────┘
```

## 2. So sánh TT133 vs TT200

| Đặc điểm | TT133/2016 | TT200/2014 |
|----------|------------|------------|
| **Đối tượng** | DN nhỏ và vừa | Mọi DN (lớn, vừa, nhỏ) |
| **Bắt buộc** | DN nhỏ và vừa (theo ND 80/2021) | DN lớn |
| **Số TK** | ~120 | ~300+ |
| **Tính phức tạp** | Đơn giản | Chi tiết |
| **BCTC** | Đầy đủ nhưng đơn giản hơn | Đầy đủ |
| **Sổ kế toán** | 2 hình thức (NKC + CTGS) | 4 hình thức |
| **Multi-currency** | có | có |
| **Costing** | có | có |

## 3. Phân loại DN nhỏ và vừa (Nghị định 80/2021)

| Tiêu chí | Siêu nhỏ | Nhỏ | Vừa |
|---------|---------|-----|-----|
| **Số nhân viên** | < 10 | 10-50 (CN/DV) hoặc 10-100 (TM/XD) | 50-100 (CN/DV) hoặc 100-200 (TM/XD) |
| **Doanh thu/năm** | < 3 tỷ | < 50 tỷ | < 200 tỷ |
| **Vốn (trừ TM)** | < 3 tỷ | < 20 tỷ | < 100 tỷ |

→ DN nhỏ và vừa **phải** áp dụng TT133 (theo QĐ ở TT133).

## 4. Hệ thống tài khoản TT133

```
LOẠI 1 - TÀI SẢN NGẮN HẠN (100-199)
├── 111 - Tiền mặt
├── 112 - Tiền gửi ngân hàng
├── 113 - Tiền đang chuyển
├── 121 - Đầu tư tài chính ngắn hạn
├── 128 - Đầu tư nắm giữ đến ngày đáo hạn
├── 131 - Phải thu khách hàng
├── 133 - Thuế GTGT được khấu trừ
├── 136 - Phải thu nội bộ
├── 138 - Phải thu khác
├── 141 - Tạm ứng
├── 152 - Nguyên liệu, vật liệu
├── 153 - Công cụ, dụng cụ
├── 154 - Chi phí SXKD dở dang
├── 155 - Thành phẩm
├── 156 - Hàng hóa
├── 159 - Dự phòng giảm giá Hàng tồn kho
└── ...

LOẠI 2 - TÀI SẢN DÀI HẠN (200-299)
├── 211 - TSCĐ hữu hình
├── 212 - TSCĐ thuê tài chính
├── 213 - TSCĐ vô hình
├── 214 - Hao mòn TSCĐ
├── 221 - Bất động sản đầu tư
├── 228 - Đầu tư dài hạn khác
├── 229 - Đầu tư tài chính dài hạn
├── 241 - Xây dựng cơ bản dở dang
├── 242 - Chi phí trả trước
└── ...

LOẠI 3 - NỢ PHẢI TRẢ (300-399)
├── 311 - Vay và nợ thuê TC ngắn hạn
├── 331 - Phải trả cho người bán
├── 333 - Thuế và các khoản phải nộp Nhà nước
│   ├── 3331 - Thuế GTGT
│   ├── 3332 - Thuế TTĐB
│   ├── 3333 - Thuế TNDN
│   ├── 3334 - Thuế nhà thầu
│   ├── 3335 - Thuế môn bài
│   ├── 3336 - Thuế TNCN
│   ├── 3337 - Thuế HBKT
│   ├── 3339 - Phí, lệ phí
├── 334 - Phải trả người lao động
├── 335 - Chi phí phải trả
├── 336 - Phải trả nội bộ
├── 338 - Phải trả, phải nộp khác
├── 341 - Vay và nợ thuê TC dài hạn
└── ...

LOẠI 4 - VỐN CHỦ SỞ HỮU (400-499)
├── 411 - Vốn đầu tư của chủ sở hữu
├── 412 - Chênh lệch đánh giá lại tài sản
├── 413 - Chênh lệch tỷ giá hối đoái
├── 418 - Quỹ khen thưởng, phúc lợi
├── 421 - Lợi nhuận chưa phân phối
└── ...

LOẠI 5 - DOANH THU (500-599)
├── 511 - Doanh thu
│   ├── 5111 - DT bán hàng
│   ├── 5112 - DT cung cấp DV
│   ├── 5113 - DT trợ cấp, cấp tài trợ
│   ├── 5117 - Doanh thu cung cấp DV (TT133 mới)
│   └── 5118 - Doanh thu khác
├── 512 - Doanh thu hàng bán bị trả lại
├── 515 - Doanh thu hoạt động tài chính
└── 711 - Thu nhập khác (TT133 gộp)

LOẠI 6 - CHI PHÍ (600-699)
├── 621 - Chi phí NVL trực tiếp
├── 622 - Chi phí nhân công trực tiếp
├── 623 - Chi phí sử dụng máy móc thiết bị (TT200)
├── 627 - Chi phí SX chung
├── 632 - Giá vốn hàng bán
├── 635 - Chi phí tài chính
├── 641 - Chi phí bán hàng
├── 642 - Chi phí QLDN
│   ├── 6421 - CP bán hàng (TT200 tách ra 641)
│   ├── 6422 - CP QLDN (TT200 tách)
└── 811 - Chi phí khác

LOẠI 7 - THU NHẬP KHÁC (700-799)
└── 711 - Thu nhập khác

LOẠI 8 - CHI PHÍ KHÁC (800-899)
├── 811 - Chi phí khác
└── 821 - Chi phí thuế TNDN
    ├── 8211 - CP thuế TNDN hiện hành
    └── 8212 - CP thuế TNDN hoãn lại

LOẠI 9 - XÁC ĐỊNH KẾT QUẢ (900-999)
└── 911 - Xác định kết quả kinh doanh
```

## 5. Sổ kế toán (theo TT133)

### 5.1. Hai hình thức ghi sổ

```
Hình thức 1: Nhật ký chung (NKC)
  - Chứng từ gốc → NKC → Sổ cái → BCTC
  - Mẫu: S03a-DN (TT133), S03a-DNN (DN lớn)

Hình thức 2: Chứng từ ghi sổ (CTGS)
  - Chứng từ gốc → Bảng kê → CTGS → Sổ đăng ký CTGS → Sổ cái → BCTC
  - Mẫu: S02a-DN (TT133), S02a-DNN (DN lớn)
```

### 5.2. Sổ kế toán chi tiết

| Sổ | Mẫu TT133 | Mẫu TT200 |
|----|----------|----------|
| Sổ quỹ tiền mặt | S07-DN | S07-DN |
| Sổ kế toán chi tiết quỹ tiền mặt | S07a-DN | S07a-DN |
| Sổ tiền gửi ngân hàng | S08-DN | S08-DN |
| Sổ chi tiết bán hàng | S35-DN | S35-DN |
| Sổ chi tiết công nợ | S31-DN | S31-DN |
| Thẻ kho | S10-DN, S12-DN | S10-DN, S12-DN |
| Sổ theo dõi CCDC | S22-DN | S22-DN |
| Sổ detail TK | S38-DN | S38-DN |

### 5.3. Báo cáo tài chính

| Báo cáo | TT133 (DN nhỏ vừa) | TT200 (DN lớn) |
|---------|-------------------|---------------|
| Bảng cân đối tài khoản | S06-DN | F01b-DNN |
| BCTH tài chính | B01a-DN | B01-DN |
| BC KQ HĐKD | B02a-DN | B02-DN |
| BC Lưu chuyển tiền tệ | B03a-DN | B03-DN |
| Thuyết minh BCTC | B09a-DN | B09-DN |

## 6. Hóa đơn và chứng từ

### 6.1. Loại hóa đơn

| Loại | Mô tả |
|------|------|
| Hóa đơn GTGT | Có thuế GTGT, dùng cho KH là DN có MST |
| Hóa đơn bán hàng | Không tính GTGT, dùng cho KH cá nhân |
| Hóa đơn bán tài sản | Bán TS đã sử dụng |
| Hóa đơn khác | Bán vàng bạc đá quý, ...) |
| Phiếu xuất kho | Xuất nội bộ |
| Hóa đơn điện tử | Bắt buộc từ 01/07/2022 (TT78) |

### 6.2. Thuế suất GTGT

| Thuế suất | Áp dụng |
|-----------|---------|
| 0% | Xuất khẩu, vận tải quốc tế, hàng luật định |
| 5% | Lương thực, y tế, sách báo, giáo dục, ... |
| 8% (giai đoạn) | Một số HHDV theo Nghị quyết giảm thuế |
| 10% | Mặc định |
| -KT (không chịu) | Một số nghiệp vụ đặc thù |

### 6.3. Quy trình hóa đơn điện tử

```
1. Doanh nghiệp đăng ký sử dụng HĐĐT với nhà cung cấp (BKAV, Viettel, MobiFone, ...)
2. Cấp MST, tạo chữ ký số
3. Phát hành HĐ → gửi dữ liệu đến người mua + TCT
4. TCT xác nhận + lưu trữ
5. KH mua hàng nhận HĐ qua email/zalo
```

## 7. Kỳ kế toán và niên độ

```
Niên độ kế toán: 12 tháng, từ 01/01 đến 31/12 (mặc định)
Đầu niên độ đầu tiên: có thể < 12 tháng (năm thành lập)
Đầu niên độ cuối: có thể > 12 tháng (nếu đổi niên độ)

Kỳ kế toán:
- Tháng: từ ngày 1 đến cuối tháng
- Quý: 3 tháng
- Năm: trùng niên độ
```

## 8. Đơn vị tiền tệ

- Đồng tiền ghi sổ: **Đồng Việt Nam (VND)**, làm tròn đến 1 VND
- Đối với DN có ngoại tệ: phải quy đổi sang VND theo tỷ giá:
  - Bán ra: tỷ giá bán của ngân hàng TM mà DN mở TK
  - Mua vào: tỷ giá mua
  - Tính khấu hao TSCĐ: tỷ giá bình quân
- Cuối kỳ: đánh giá lại số dư ngoại tệ → lãi/lỗ tỷ giá (TK 413, 515, 635)

## 9. Lưu trữ chứng từ & sổ sách

- Theo Luật Kế toán: lưu trữ tối thiểu **5 năm** (cho CT, sổ, BCTC)
- Một số loại lưu trữ lâu hơn:
  - Hồ sơ nhân sự: 50 năm
  - Hợp đồng bảo hiểm: vĩnh viễn
- Hóa đơn điện tử: lưu trữ điện tử theo quy định

## 10. Tài liệu tham khảo

- 🔗 [Luật Kế toán 88/2015/QH13](https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Luat-Ke-toan-88-2015-QH13-296441.aspx)
- 🔗 [TT200/2014/TT-BTC](https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-200-2014-TT-BTC-huong-dan-Che-do-ke-toan-Doanh-nghiep-263599.aspx)
- 🔗 [TT133/2016/TT-BTC](https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Thong-tu-133-2016-TT-BTC-huong-dan-che-do-ke-toan-doanh-nghiep-nho-va-vua-284997.aspx)
- 🔗 [TT80/2021/TT-BTC](https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-80-2021-TT-BTC-ban-hanh-mau-to-khai-thue-502620.aspx)
- 🔗 [TT78/2021/TT-BTC](https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-78-2021-TT-BTC-huong-dan-Luat-Quan-ly-thue-Nghi-dinh-123-2020-ND-CP-hoa-don-chung-tu-477966.aspx)
- 🔗 [TT32/2025/TT-BTC](https://thuvienphapluat.vn/van-ban/Thue-Phi-Le-Phi/Thong-tu-32-2025-TT-BTC-huong-dan-thuc-hien-Luat-Quan-ly-thue-ve-hoa-don-chung-tu-659105.aspx)
- 🔗 [Nghị định 80/2021/NĐ-CP - DN nhỏ và vừa](https://thuvienphapluat.vn/van-ban/Doanh-nghiep/Nghi-dinh-80-2021-ND-CP-quan-dinh-tieu-chi-xac-dinh-doanh-nghiep-nho-vua-485068.aspx)
- 🔗 [Hệ thống tài khoản TT133](https://www.meinvoice.vn/tin-tuc/16900/bang-he-thong-tai-khoan-theo-thong-tu-133-day-du/)
- 🔗 [Hệ thống tài khoản TT200](https://docs.kreston.vn/vbpl/ke-toan/che-do-ke-toan/che-do-ke-toan-doanh-nghiep/tt-200-2014-tt-btc/phu-luc-1/)

---

**Tiếp theo**: [02. Chi tiết TT133](./02-tt133-2016.md)
