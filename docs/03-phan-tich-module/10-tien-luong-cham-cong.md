# 10. Module Tiền lương, chấm công (Payroll & Time Attendance)

> Chấm công, ca làm việc, tăng ca, lịch nghỉ. (Trong demo chỉ thấy phần chấm công; phần tính lương không có UI.)

## 1. Mục đích nghiệp vụ

- Quản lý ca làm việc, lịch nghỉ trong năm
- Chấm công NV (vào/ra) theo ca
- Theo dõi tăng ca, nghỉ phép, nghỉ ốm, nghỉ việc riêng
- Tính công chuẩn, công thực tế
- Cung cấp dữ liệu cho module tính lương (sẽ bổ sung khi tái hiện)

## 2. Cấu trúc module

### 2.1. Báo cáo

| Báo cáo | Mô tả |
|---------|------|
| Vào ra chi tiết | Log chấm công vào/ra |
| Vào ra chi tiết 1 NV | Cho 1 NV |
| Bảng chấm tổng hợp | Tổng hợp công trong tháng |
| Bảng chấm công CT 1 NV | Bảng chấm chi tiết |
| Tình hình nghỉ phép | Sử dụng phép |
| NV đi muộn về sớm | Late/early tracking |
| Tổng hợp NV làm thêm | Overtime summary |
| NV đi làm trong ngày | Daily attendance |
| Tổng hợp công cơm theo tháng | Meal allowance calc |

### 2.2. Cập nhật số liệu

| Chức năng | Mô tả |
|----------|------|
| Lịch nghỉ trong năm | Public holidays |
| Đăng ký ca làm việc NV | Shift assignment |
| Ngày nghỉ phép đầu năm | Leave opening balance |
| Định mức nghỉ năm | Annual leave quota |
| Kết chuyển nghỉ phép sang năm sau | Leave carry-forward |
| Chấm công | Time punch entries |
| Ngày nghỉ, lý do nghỉ | Leave records |
| Đăng ký tăng ca/làm thêm | Overtime registration |

### 2.3. Danh mục từ điển

| Danh mục | Trường chính |
|----------|-------------|
| Danh mục ca làm việc | code, name, start_time, end_time, break_minutes, late_grace_period |
| Khai báo ngày công chuẩn | period, standard_days, standard_hours |
| Danh mục máy chấm công | code, name, model, location, type (fingerprint, face, card) |

## 3. Quy trình nghiệp vụ

### 3.1. Thiết lập ca làm việc

```
1. Vào Tiền lương → Danh mục ca làm việc → Thêm mới
   - Mã ca: Sáng, Chiều, Đêm, Hành chính
   - Giờ bắt đầu, giờ kết thúc
   - Nghỉ giải lao (phút)
   - Grace period (số phút trễ cho phép)
2. Vào Tiền lương → Đăng ký ca làm việc NV
   - Gán ca cho NV theo tuần/tháng
3. Vào Tiền lương → Khai báo ngày công chuẩn
   - Số ngày công chuẩn trong tháng (vd: 22)
   - Số giờ công chuẩn
```

### 3.2. Chấm công

```
1. NV quẹt thẻ/vân tay tại máy chấm công → tạo raw_log
2. Hệ thống import raw_log từ máy → tạo attendance_record
3. NV/Admin đăng ký nghỉ phép → leave_record
4. NV đăng ký tăng ca → overtime_record
5. Cuối tháng: hệ thống tổng hợp:
   - Số ca làm thực tế
   - Số ca trễ, về sớm
   - Số ngày nghỉ có phép/không phép
   - Số giờ làm thêm
   - Tính công chuẩn = tổng công theo ca
```

### 3.3. Tính công

```
Công chuẩn = số ngày làm việc thực tế / số ngày công chuẩn × 22

Hoặc theo giờ:
Công chuẩn = tổng giờ làm / (8 × 22)

Phân loại công:
- Làm đủ ca: 1.0 công
- Trễ/về sớm > grace period: 0.5 hoặc 0 công (theo quy định)
- Nghỉ phép: 1 công (hưởng lương)
- Nghỉ ốm: 0.7 công (theo BHXH)
- Nghỉ không phép: 0 công
- Làm thêm giờ: tính hệ số 1.5x (ngày thường), 2x (CN), 3x (lễ)
```

## 4. Entity relationship

```
┌────────────────┐    ┌────────────────────────┐
│ Shift          │ 1 *│ ShiftAssignment        │
└────────────────┘───→│ (NV gán ca)            │
                       └────────────────────────┘
                                ↑
                                │ *
┌──────────────────┐    ┌───────┴────────────────┐
│ AttendanceRecord │    │ Employee               │
│ (Chấm công)      │───→│                        │
└──────────────────┘    └────────────────────────┘
        ↑
        │ (import from)
┌───────┴──────────┐
│ TimeClockLog     │
│ (Raw log)        │
└──────────────────┘

┌──────────────────┐       ┌──────────────────────┐
│ LeaveRecord      │       │ OvertimeRecord       │
└──────────────────┘       └──────────────────────┘

┌──────────────────┐       ┌──────────────────────┐
│ AnnualLeave      │       │ PublicHoliday        │
│ Balance          │       │ (Lịch nghỉ)          │
└──────────────────┘       └──────────────────────┘
```

## 5. Đặc tả bảng chính

**`shift`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(20) | SANG, CHIEU, DEM, HC |
| name | VARCHAR(100) | Ca sáng / Ca chiều / Ca đêm / Hành chính |
| start_time | TIME | |
| end_time | TIME | |
| break_minutes | INT | |
| late_grace_minutes | INT | Phút trễ cho phép |
| early_leave_grace_minutes | INT | |
| is_night_shift | BOOL | Ca đêm (có phụ cấp) |
| is_weekend | BOOL | |

**`shift_assignment`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| shift_id | BIGINT FK | |
| effective_date | DATE | |
| end_date | DATE | nullable |
| week_days | VARCHAR(20) | '1,2,3,4,5' = T2-T6 |

**`attendance_record`** (Chấm công đã xử lý):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| attendance_date | DATE | |
| shift_id | BIGINT FK | Ca đã làm |
| check_in_time | DATETIME | |
| check_out_time | DATETIME | |
| late_minutes | INT | Số phút trễ |
| early_minutes | INT | Số phút về sớm |
| work_hours | DECIMAL(5,2) | Số giờ làm |
| overtime_hours | DECIMAL(5,2) | Giờ làm thêm |
| leave_type | ENUM | none, annual, sick, maternity, unpaid, business_trip |
| leave_hours | DECIMAL(5,2) | |
| meal_allowance_count | INT | Số suất cơm |
| status | ENUM | present, late, early_leave, absent, leave, holiday |
| source | ENUM | manual, time_clock |

**`time_clock_log`** (Raw log từ máy):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| time_clock_id | BIGINT FK | |
| employee_code | VARCHAR(50) | |
| punch_time | DATETIME | |
| punch_type | ENUM | in, out |
| raw_data | JSON | |

**`leave_record`** (Nghỉ phép):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| leave_type | ENUM | annual, sick, maternity, unpaid, business_trip |
| start_date | DATE | |
| end_date | DATE | |
| days | DECIMAL(5,2) | |
| hours | DECIMAL(5,2) | |
| reason | TEXT | |
| approver_id | BIGINT FK | |
| status | ENUM | pending, approved, rejected |

**`overtime_record`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| date | DATE | |
| start_time | TIME | |
| end_time | TIME | |
| hours | DECIMAL(5,2) | |
| ot_type | ENUM | weekday, weekend, holiday |
| coefficient | DECIMAL(4,2) | 1.5, 2.0, 3.0 |
| reason | TEXT | |
| approver_id | BIGINT FK | |

**`annual_leave_balance`** (Số dư nghỉ phép):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| fiscal_year | SMALLINT | |
| opening_days | DECIMAL(5,2) | |
| accrual_days | DECIMAL(5,2) | Phép tích lũy trong năm |
| used_days | DECIMAL(5,2) | Đã dùng |
| remaining_days | DECIMAL(5,2) | Còn lại |
| carry_forward_days | DECIMAL(5,2) | Chuyển sang năm sau |

**`public_holiday`** (Lịch nghỉ trong năm):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| holiday_date | DATE | |
| holiday_name | VARCHAR(255) | |
| is_paid | BOOL | |

**`time_clock_machine`** (Máy chấm công):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| code | VARCHAR(20) | |
| name | VARCHAR(255) | |
| model | VARCHAR(100) | |
| location | VARCHAR(255) | |
| api_endpoint | VARCHAR(500) | URL API để pull data |
| api_key | VARCHAR(255) | |
| last_sync | DATETIME | |

## 6. Use cases

### UC-30: Setup ca làm việc và ngày công chuẩn

1. Tiền lương → Danh mục ca làm việc → Thêm các ca
2. Tiền lương → Khai báo ngày công chuẩn → Nhập 22 ngày/tháng
3. Tiền lương → Lịch nghỉ trong năm → Thêm các ngày lễ

### UC-31: Chấm công hàng ngày

1. NV quẹt thẻ máy chấm công → raw log
2. Hệ thống auto sync (or manual import) → time_clock_log
3. Hệ thống xử lý:
   - Match với ca đã đăng ký
   - Tính late_minutes, early_minutes
   - Set status
4. Tạo attendance_record

### UC-32: Đăng ký nghỉ phép

1. Tiền lương → Cập nhật số liệu → Ngày nghỉ, lý do nghỉ
2. Chọn NV, ngày nghỉ, loại nghỉ (annual, sick, ...)
3. Hệ thống:
   - Tạo leave_record
   - Trừ annual_leave_balance.used_days
   - Cập nhật attendance_record (status='leave')

### UC-33: Đăng ký tăng ca

1. Tiền lương → Đăng ký tăng ca/làm thêm
2. Chọn NV, ngày, giờ bắt đầu/kết thúc
3. Hệ thống:
   - Tính overtime_hours, ot_type, coefficient
   - Tạo overtime_record

### UC-34: Báo cáo chấm công tháng

```
BẢNG CHẤM CÔNG THÁNG 06/2026
Phòng: ………  

Mã NV | Họ tên | 1 | 2 | 3 | 4 | 5 | 6 | 7 | ... | 30 | Tổng công | Công chuẩn | OT giờ
------|---------|---|---|---|---|---|---|---|-----|----|-----------|-----------|-------
NV001 | Nguyễn A | X | X | X | X | X | - | - | ... | X  | 22        | 22        | 8
NV002 | Trần B   | X | X | X | P | X | - | - | ... | X  | 21        | 22        | 0
```

## 7. Validation rules

- check_in_time < check_out_time
- leave_days ≤ annual_leave_balance.remaining_days (cho phép phép năm)
- overtime_hours ≤ số giờ quy định (max 4h/ngày, 40h/tháng)
- shift_assignment: không trùng giờ cho 1 NV trong 1 ngày

## 8. Phân quyền

- `payroll.shift.view`, `.create`, `.edit`
- `payroll.attendance.view`, `.create`, `.edit`, `.import`
- `payroll.leave.manage`, `.approve`
- `payroll.overtime.manage`, `.approve`
- `payroll.time_clock.sync`
- `payroll.report.view`

---

**Tiếp theo**: [11. Báo cáo tài chính](./11-bao-cao-tai-chinh.md)
