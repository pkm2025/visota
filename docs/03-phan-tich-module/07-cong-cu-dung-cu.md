# 07. Module Công cụ dụng cụ (CCDC)

> Quản lý công cụ dụng cụ (TK 142, 242): tăng, phân bổ chi phí, kiểm kê, báo cáo.

## 1. Mục đích nghiệp vụ

- Quản lý CCDC: CCDC ngắn hạn (142) và dài hạn (242)
- Phân bổ chi phí CCDC vào chi phí hoạt động (N641, N642, N635 / C142, C242)
- Theo dõi CCDC tại nơi sử dụng
- Báo cáo tăng/giảm/kiểm kê CCDC

Khác biệt so với TSCĐ:
- CCDC có giá trị thấp hơn, thời gian phân bổ ngắn (≤ 1 năm cho 142, > 1 năm cho 242)
- Phân bổ thay vì khấu hao
- Có thể không bắt buộc theo dõi chi tiết từng CCDC (mặc định theo lô)

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chức năng | Mô tả |
|----------|------|
| CCDC | Khai báo CCDC mới |
| Thay đổi CCDC | Cập nhật thông tin |
| Tính phân bổ | Tính phân bổ định kỳ |
| Điều chỉnh phân bổ | Điều chỉnh |
| Tính khấu hao chi tiết | Tính theo từng CCDC |
| Tạo bút toán chi phí khấu hao | Sinh voucher GL |
| Khai báo hệ số phân bổ | Hệ số cho nhiều BP |

### 2.2. Báo cáo phân bổ

- Bảng tính chi phí CCDC (nhiều variant)
- Bảng tổng hợp chi phí CCDC
- Bảng kê phân bổ chi phí CCDC
- Bảng tổng hợp phân bổ chi phí CCDC

### 2.3. Báo cáo kiểm kê công cụ

- Bảng kê thông tin chung CCDC
- Bảng kê giá trị CCDC
- Bảng tổng hợp giá trị CCDC
- Thẻ công cụ, dụng cụ
- Sổ công cụ, dụng cụ
- Sổ theo dõi CCDC tại nơi sử dụng (S22-DN, S10-DNN)
- Bảng kê CCDC hết phân bổ còn sử dụng

### 2.4. Báo cáo tăng giảm công cụ

- Bảng kê CCDC tăng/giảm trong kỳ
- Báo cáo tổng hợp tăng giảm CCDC
- Bảng kê CCDC chuyển BP sử dụng
- Bảng cân đối phát sinh CCDC

### 2.5. Danh mục từ điển

- Bộ phận sử dụng
- Nhóm CCDC, Loại CCDC, Phân nhóm CCDC
- Lý do tăng giảm
- Nguồn vốn

## 3. Quy trình nghiệp vụ

### 3.1. Quy trình tăng CCDC

```
Mua/nhận CCDC
  ↓
Cập nhật CCDC
  - Mã CCDC, tên
  - Loại, nhóm
  - Giá trị
  - Thời gian phân bổ
  - BP sử dụng
  ↓
Hạch toán tăng:
  N142 / C111, C331, C156...
  ↓
Bắt đầu phân bổ hàng tháng
```

### 3.2. Quy trình phân bổ

```
Mỗi tháng:
1. Tính số kỳ phân bổ còn lại
2. Phân bổ kỳ này = Giá trị còn lại / số kỳ còn lại
3. Phân bổ cho các BP theo hệ số
4. Sinh voucher:
   N641 / C142 (cho CCDC bán hàng)
   N642 / C242 (cho CCDC quản lý DN)
   N635 / C242 (cho CCDC tài chính)
```

### 3.3. Quy trình giảm CCDC

- Hết phân bổ (giá trị = 0) → chuyển trạng thái 'fully_allocated'
- Mất mát, thanh lý → hạch toán giảm
- Có thể vẫn theo dõi "CCDC hết phân bổ còn sử dụng" để theo dõi vật lý

## 4. Đặc tả bảng chính

Tương tự TSCĐ với các thay đổi:
- Bảng `tool` (thay cho `fixed_asset`)
- Bảng `tool_allocation` (thay cho `asset_depreciation`)
- Bảng `tool_transaction`
- Bảng `tool_allocation_rule`

Các trường chính giống TSCĐ nhưng có thêm:
- `allocation_period_months`: số kỳ phân bổ (tháng)
- `allocation_method`: 'straight_line', 'manual'
- `is_tracked_individual`: có theo dõi từng CCDC riêng không

## 5. Sổ theo dõi CCDC (S22-DN, S10-DNN)

```
SỔ THEO DÕI CÔNG CỤ DỤNG CỤ TẠI NƠI SỬ DỤNG
Bộ phận: …  Kỳ: 06/2026

STT | Mã CCDC | Tên CCDC | Ngày nhập | Nguyên giá | Phân bổ tháng | Đã phân bổ | Còn lại | Số kỳ còn
----|---------|----------|-----------|-----------|---------------|-----------|---------|----------
1   | CC001   | Kéo cắt giấy | 01/01/2025 | 1.000.000 | 100.000 | 1.600.000 | 400.000 | 4
2   | CC002   | Búa nhỏ | 01/06/2026 | 500.000 | 50.000 | 50.000 | 450.000 | 9
...
```

## 6. Use cases

### UC-23: Khai báo CCDC mới

1. CCDC → Cập nhật số liệu → CCDC → Thêm mới
2. Nhập:
   - Mã CCDC, tên
   - Loại, nhóm, phân nhóm
   - Giá trị, NT
   - Thời gian phân bổ (tháng)
   - BP sử dụng, hệ số (nếu nhiều BP)
3. Lưu → hạch toán: N142 / C111 (hoặc C331, C156)

### UC-24: Tính phân bổ hàng tháng

1. CCDC → Cập nhật số liệu → Tính phân bổ
2. Chọn kỳ
3. Hệ thống:
   - Lọc CCDC đang phân bổ
   - Tính phân bổ kỳ này = (Giá trị - đã phân bổ) / số kỳ còn lại
   - Lưu `tool_allocation`
   - Sinh voucher GL: N641/642 / C142

## 7. Validation rules

- Giá trị > 0
- Thời gian phân bổ > 0 (tháng)
- Số kỳ phân bổ ≤ thời gian phân bổ
- Khi hết phân bổ → auto change status

## 8. Phân quyền

- `tool.tool.view`, `.create`, `.edit`
- `tool.allocation.calculate`, `.adjust`
- `tool.transaction.increase`, `.decrease`, `.transfer`
- `tool.report.view`

---

**Tiếp theo**: [08. Chi phí, giá thành](./08-chi-phi-gia-thanh.md)
