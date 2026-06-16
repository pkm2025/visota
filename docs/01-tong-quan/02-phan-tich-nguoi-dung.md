# 02. Phân tích người dùng & vai trò

> Các actor tương tác với hệ thống và phân quyền chi tiết.

## 1. Phân loại người dùng

### 1.1. End Users (tương tác thường xuyên)

| Vai trò | Mô tả | Module chính |
|---------|------|-------------|
| **Admin hệ thống** | Quản trị kỹ thuật, cấu hình | Hệ thống, identity |
| **Kế toán trưởng** | Chịu trách nhiệm kế toán, duyệt | Tất cả module nghiệp vụ |
| **Kế toán tổng hợp** | Phiếu kế toán, kết chuyển | Tổng hợp, BCTC |
| **Kế toán công nợ** | Theo dõi công nợ KH/NCC | Bán hàng, Mua hàng |
| **Kế toán kho** | Nhập xuất, tính giá | Tồn kho |
| **Kế toán TSCĐ** | Quản lý TSCĐ, khấu hao | Tài sản cố định |
| **Kế toán tiền lương** | Chấm công, tính lương | Nhân sự, Tiền lương |
| **Thủ quỹ** | Quản lý tiền mặt | Vốn bằng tiền |
| **Kế toán thuế** | Tờ khai thuế | Báo cáo thuế |
| **Nhân viên kinh doanh** | Xem công nợ KH | Bán hàng (view only) |
| **Nhân viên kho** | Lập phiếu nhập xuất | Tồn kho |
| **Giám đốc** | Xem báo cáo, phân tích | Báo cáo (view only) |

### 1.2. External Users (tương tác qua API/integration)

| Actor | Mô tả | Tích hợp |
|-------|------|----------|
| **Khách hàng** | Nhận HĐĐT qua email | HĐĐT provider |
| **Nhà cung cấp** | Nhận phiếu thanh toán | Banking |
| **Cơ quan thuế** | Nhận tờ khai, BCTC | TCT API |
| **Ngân hàng** | Nhận lệnh chi | Banking API |
| **BKAV** | Phát hành HĐĐT | BKAV API |
| **Nhà cung cấp HĐĐT khác** | Viettel, MobiFone, VNPT | API tương ứng |

## 2. Ma trận vai trò - quyền

| Permission | Admin | KT Trưởng | KT Tổng Hợp | KT Công Nợ | KT Kho | KT TSCĐ | KT Lương | Thủ Quỹ | KT Thuế | Sales | NV Kho | Giám Đốc |
|-----------|-------|-----------|-------------|-----------|--------|---------|---------|---------|---------|-------|--------|---------|
| `gl.voucher.view` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | ✓ | – | – | ✓ |
| `gl.voucher.create` | ✓ | ✓ | ✓ | – | – | – | – | – | – | – | – | – |
| `gl.voucher.post` | ✓ | ✓ | ✓ | – | – | – | – | – | – | – | – | – |
| `gl.voucher.lock` | – | ✓ | – | – | – | – | – | – | – | – | – | – |
| `gl.closing.execute` | – | ✓ | ✓ | – | – | – | – | – | – | – | – | – |
| `gl.year_end.carry_forward` | – | ✓ | – | – | – | – | – | – | – | – | – | – |
| `sales.invoice.view` | ✓ | ✓ | ✓ | ✓ | – | – | – | – | ✓ | ✓ | – | ✓ |
| `sales.invoice.create` | ✓ | ✓ | – | ✓ | – | – | – | – | – | ✓ | – | – |
| `sales.customer.view` | ✓ | ✓ | ✓ | ✓ | – | – | – | – | ✓ | ✓ | – | – |
| `purchase.invoice.view` | ✓ | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – | – | ✓ |
| `purchase.invoice.create` | ✓ | ✓ | – | ✓ | – | – | – | – | – | – | – | – |
| `stock.voucher.view` | ✓ | ✓ | ✓ | – | ✓ | – | – | – | – | – | ✓ | ✓ |
| `stock.voucher.create` | ✓ | ✓ | – | – | ✓ | – | – | – | – | – | ✓ | – |
| `stock.cost.calculate` | – | ✓ | ✓ | – | – | – | – | – | – | – | – | – |
| `treasury.cash.view` | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – | – | – | – |
| `treasury.cash.create` | ✓ | ✓ | – | – | – | – | – | ✓ | – | – | – | – |
| `assets.asset.view` | ✓ | ✓ | ✓ | – | – | ✓ | – | – | – | – | – | ✓ |
| `assets.depreciation.calculate` | – | ✓ | ✓ | – | – | ✓ | – | – | – | – | – | – |
| `hr.employee.view` | ✓ | ✓ | – | – | – | – | ✓ | – | – | – | – | ✓ |
| `hr.employee.view_sensitive` | – | ✓ | – | – | – | – | ✓ | – | – | – | – | – |
| `payroll.attendance.view` | ✓ | ✓ | – | – | – | – | ✓ | – | – | – | – | – |
| `payroll.run` | – | ✓ | – | – | – | – | ✓ | – | – | – | – | – |
| `tax.return.generate` | – | ✓ | – | – | – | – | – | – | ✓ | – | – | – |
| `report.bctc.view` | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ | – | – | ✓ |
| `report.bctc.export` | – | ✓ | ✓ | – | – | – | – | – | ✓ | – | – | ✓ |
| `system.user.manage` | ✓ | – | – | – | – | – | – | – | – | – | – | – |
| `system.parameter.edit` | ✓ | – | – | – | – | – | – | – | – | – | – | – |
| `system.fiscal_year.lock` | ✓ | – | – | – | – | – | – | – | – | – | – | – |

## 3. Quy ước format permission

`<module>.<entity>.<action>`

| Action | Mô tả |
|--------|------|
| `view` | Xem danh sách / chi tiết |
| `create` | Tạo mới |
| `edit` | Sửa |
| `delete` | Xóa |
| `post` | Đăng sổ (cho voucher) |
| `unpost` | Bỏ đăng sổ |
| `lock` | Khóa |
| `unlock` | Mở khóa |
| `approve` | Duyệt |
| `export` | Xuất file |
| `import` | Import file |
| `run` | Thực thi (batch job) |
| `manage` | Toàn quyền (CRUD + workflow) |

## 4. Tổ chức user và role

```
Mỗi user có:
- 1 vai trò trong mỗi công ty
- Default company
- Default fiscal year

Mỗi company có:
- Các role mặc định (admin, accountant, viewer)
- Tự tạo thêm role tùy chỉnh
```

---

**Tiếp theo**: [03. Quy trình thu thập thông tin](./03-quy-trinh-suu-tam.md)
