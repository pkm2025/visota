# A1 — Quản trị Người dùng, Vai trò, Phân quyền

> Hướng dẫn cho superuser quản trị hệ thống phân quyền.

## 1. Kiến trúc phân quyền

PMKetoan dùng mô hình **RBAC 4 lớp**:

```
User (Người dùng)
   ↓
UserCompanyRole (gán role theo công ty)
   ↓
Role (Vai trò) — có nhiều Permission
   ↓
Permission (Quyền) — `<module>.access`
```

**Quy tắc**:
- Mỗi user có 1+ role tại 1+ công ty
- 1 role có nhiều permission
- Permission theo **module** (25 module): `ledger.access`, `sales.access`, ...
- **Superuser** bypass toàn bộ kiểm tra

## 2. Danh sách vai trò mặc định

| Role code | Tên | Module | Phù hợp |
|-----------|-----|--------|---------|
| `admin` | Quản trị hệ thống | 25/25 | Superuser |
| `chief_accountant` | Kế toán trưởng | 25/25 | KTT — duyệt + quản trị |
| `accountant` | Kế toán viên | 19 | KT tổng hợp |
| `sales` | Nhân viên kinh doanh | 9 | Sales + CRM |
| `purchaser` | Nhân viên mua hàng | 6 | Mua hàng + kho |
| `hr_officer` | Nhân sự | 6 | HR + lương |
| `project_manager` | Quản lý dự án | 7 | PM |
| `viewer` | Chỉ xem | 3 | Báo cáo |

## 3. Quản trị user

Sidebar → **Hệ thống → Người dùng** (chỉ superuser/staff)

### Tạo user mới

1. Bấm **"+ Tạo user"** (chưa có UI — dùng Django admin `/admin/auth/user/add/`)
2. Hoặc dùng management command:

```bash
python manage.py shell -c "
from apps.identity.models import User
u = User.objects.create_user(
    username='nguyenvan',
    password='StrongPass123!',
    email='nguyenvan@pkm.vn',
    full_name='Nguyễn Văn A',
)
print(f'Created {u.username}')
"
```

### Reset password

```bash
python manage.py changepassword <username>
```

Hoặc shell:

```bash
python manage.py shell -c "
from apps.identity.models import User
u = User.objects.get(username='nguyenvan')
u.set_password('NewPass123!')
u.save()
"
```

### Khóa / mở khóa tài khoản

```bash
# Khóa do Axes (sau nhiều lần sai pass)
python manage.py axes_reset <username>

# Khóa vĩnh viễn (deactivate)
python manage.py shell -c "
from apps.identity.models import User
u = User.objects.get(username='nguyenvan')
u.is_active = False
u.save()
"
```

### Khóa đăng nhập 2 yếu tố (2FA)

User có field `two_factor_enabled`. Hiện chưa có UI setup — dùng django-otp
trong tương lai.

## 4. Gán vai trò cho user

Sidebar → **Hệ thống → Người dùng** → chọn user → dropdown role → bấm **✓**

### Bulk assign

```bash
python manage.py shell -c "
from apps.identity.models import User, Role, UserCompanyRole
from apps.core.models import Company
company = Company.objects.first()
user = User.objects.get(username='nguyenvan')
role = Role.objects.get(code='accountant', company=company)
ucr, _ = UserCompanyRole.objects.get_or_create(
    user=user, company=company, role=role,
    defaults={'is_default': True},
)
print(f'Assigned {role.name} to {user.username}')
"
```

### Gán nhiều công ty

Mỗi user có thể có role khác nhau ở công ty khác nhau:

```python
# Là accountant ở PKM
UserCompanyRole(user=u, company=pkm, role=acc_role).save()
# Là viewer ở công ty con
UserCompanyRole(user=u, company=sub, role=viewer_role).save()
```

## 5. Quản trị vai trò

Sidebar → **Hệ thống → Vai trò & phân quyền** (chỉ staff)

### Xem role

List 8 system roles + custom roles. Bấm **"Phân quyền"** để xem/sửa.

### Sửa quyền của role

1. Click role → mở trang edit
2. Tick/untick module theo ý muốn
3. Bấm **"Lưu phân quyền"**
4. Cache của user bị invalidate → hiệu lực ngay

> ⚠ Role `admin` (system) không được sửa — toàn quyền cố định.

### Tạo role tùy chỉnh

Hiện chưa có UI — dùng Django admin hoặc shell:

```bash
python manage.py shell -c "
from apps.identity.models import Role, Permission, Company
from apps.core.models import Company
company = Company.objects.first()
role = Role.objects.create(
    company=company, code='custom_sales',
    name='Sales nâng cao', description='Sales + xem BCTC',
)
# Thêm permissions
role.permissions.set(Permission.objects.filter(code__in=[
    'sales.access', 'crm.access', 'contracts.access',
    'reporting.access', 'documents.access',
]))
"
```

## 6. Quyền của tôi (cho user thường)

Mọi user có thể xem quyền của mình tại `/modern/me/permissions/`:

- Tài khoản: username, email, công ty
- Vai trò đã gán (tại công ty hiện tại)
- Module được phép (xanh)
- Module bị từ chối (đỏ — yêu cầu admin)

## 7. Quy ước đặt role

Khuyến nghị:

| Quy tắc | Lý do |
|----------|-------|
| 1 user = 1 role/công ty | Tránh conflict |
| Đặt role theo chức danh | Dễ quản lý |
| Không tạo role trùng system role | Trùng lặp |
| Khi NV đổi vị trí → đổi role | Tránh quyền thừa |
| NV nghỉ → set `is_active=False` (không xóa) | Giữ lịch sử |

## 8. Audit log

Hiện chưa có audit log đầy đủ (planned: django-auditlog). Workaround:
- Log thay đổi user/role trong Sentry
- Backup DB hàng ngày để trace

## 9. FAQ

**Q: User quên mật khẩu?**
A: Admin chạy `python manage.py changepassword <username>`.

**Q: User không login được?**
A: Kiểm tra:
1. `is_active=True`?
2. Tài khoản bị Axes lock? → `python manage.py axes_reset`
3. Đúng URL login? `/auth/login/`

**Q: User có quyền nhưng không thấy menu?**
A: Kiểm tra:
1. Role đã có permission tương ứng?
2. User được gán role tại **đúng công ty** (session `current_company_id`)?
3. Cache: `UserService.invalidate_cache()` hoặc đợi 5 phút

**Q: Cấp thêm quyền tạm thời?**
A: Sửa role (thêm permission) → nhớ bỏ đi sau khi xong. Hoặc tạo role tạm
"temp_xxx" rồi xóa sau.

**Q: Làm sao biết user X có thực sự truy cập được route Y?**
A: Test trực tiếp — login với user đó, vào route. Hoặc audit log.

---

Tài liệu liên quan:
- [A2-companies](02-companies.md) — Quản lý multi-tenant
- [05-security](../technical/05-security.md) — Chi tiết bảo mật
- [00-getting-started](../user-guide/00-getting-started.md) — User guide cơ bản
