# 09. Module Quản lý nhân sự (HR)

> Hồ sơ nhân viên, hợp đồng lao động, quá trình công tác, BHXH, tuyển dụng.

## 1. Mục đích nghiệp vụ

- Quản lý **hồ sơ nhân viên** (employee profile) - entity trung tâm
- Theo dõi quan hệ gia đình, bằng cấp, chứng chỉ, lịch sử công tác
- Quản lý **hợp đồng lao động** (trial + official + appendix)
- Theo dõi quá trình tham gia BHXH, BHYT, BHTN
- Cấp phát, thu hồi CCDC cho nhân viên
- Quản lý khen thưởng, kỷ luật, nghỉ việc, thai sản
- Cung cấp dữ liệu cho module Tiền lương (chấm công)

## 2. Cấu trúc module

### 2.1. Cập nhật số liệu

| Chức năng | Mô tả |
|----------|------|
| Hồ sơ nhân viên | Entity trung tâm |
| Quan hệ gia đình | Cha, mẹ, vợ/chồng, con |
| Hợp đồng thử việc | Trial contract |
| Hợp đồng lao động | Official labor contract |
| Phụ lục hợp đồng lao động | Contract appendix |
| Quá trình công tác | Work history |
| Bằng cấp, chứng chỉ | Education & certification |
| Quá trình tham gia bảo hiểm | Insurance history |
| Giao nhận HS | Profile handover log |
| Điều chuyển NS | Internal transfer |
| Xếp loại nhân viên | Performance rating |
| Khen thưởng, kỷ luật | Reward & discipline |
| Nhân viên vi phạm | Violations |
| Nhân viên nghỉ việc | Resignations |
| Nhân viên nuôi con dưới 12 tháng | Maternity tracking |
| Nhân viên nghỉ thai sản | Maternity leave |
| Nhân viên công tác | Business travel |
| Danh sách NV gửi lương | Salary-payment NV list |
| Đề xuất chi phí | Cost proposal |

### 2.2. Cấp phát CCDC

- Cấp phát công cụ dụng cụ
- Thu hồi, điều chuyển CCDC
- Báo cáo tổng hợp CCDC

### 2.3. Tuyển dụng, đào tạo

- Thông tin tuyển dụng

### 2.4. Báo cáo

- Danh sách CB-NV công ty
- Tổng hợp lao động tăng giảm trong tháng
- Sinh nhật NV, hết hạn HĐLĐ, HĐHV, tròn năm
- Biểu đồ biến động nhân viên theo tháng

### 2.5. Danh mục từ điển

Rất nhiều (~35+ danh mục):

- Bộ phận nhân sự
- Chức vụ, Chức danh
- Xếp loại lao động, Trình độ văn hóa
- Xếp loại bằng cấp, Trình độ, Trình độ tin học, Ngoại ngữ
- Dân tộc, Tôn giáo, Quốc gia, Tỉnh thành, Phường/xã
- Giới tính, Tình trạng hôn nhân
- Tình trạng sức khỏe, Tình trạng hợp đồng
- Thành phần xã hội, Chính sách
- Nơi KCB, Nơi cấp thẻ bảo hiểm, Nơi cấp sổ BHXH
- Nơi công tác, Chứng chỉ, Khả năng
- Hình thức đào tạo, Chuyên ngành
- Khen thưởng kỷ luật, Quan hệ gia đình

## 3. Entity relationship

```
                    ┌──────────────────┐
                    │ Employee         │
                    │ (Hồ sơ NV)       │
                    └────────┬─────────┘
                             │ 1
       ┌─────────────────────┼──────────────────────┐
       ↓ *                   ↓ *                    ↓ *
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│FamilyRelation│    │LaborContract     │    │WorkHistory       │
└──────────────┘    └──────────────────┘    └──────────────────┘
                            │ 1                          ↑
                            ↓ *                          │ *
                    ┌──────────────────┐    ┌────────────┴───────┐
                    │ContractAppendix  │    │Education           │
                    └──────────────────┘    └────────────────────┘
                                                  ↑
                                                  │ *
┌──────────────┐    ┌──────────────────┐    ┌────┴───────────────┐
│Insurance     │    │RewardDiscipline  │    │Certification       │
│History       │    │                  │    │                    │
└──────────────┘    └──────────────────┘    └────────────────────┘

┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│LeaveRequest  │    │ToolAssignment    │    │Recruitment         │
└──────────────┘    └──────────────────┘    └────────────────────┘
```

## 4. Đặc tả bảng chính

**`employee`** (Hồ sơ nhân viên):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| company_id | BIGINT FK | |
| code | VARCHAR(50) | Mã NV |
| full_name | VARCHAR(255) | Họ và tên |
| birth_date | DATE | Ngày sinh |
| gender | ENUM | male, female, other |
| id_card_no | VARCHAR(20) | Số CMND/CCCD |
| id_card_date | DATE | Ngày cấp |
| id_card_place | VARCHAR(255) | Nơi cấp |
| personal_tax_code | VARCHAR(20) | MST cá nhân |
| social_insurance_no | VARCHAR(20) | Số sổ BHXH |
| health_insurance_no | VARCHAR(20) | Số thẻ BHYT |
| phone | VARCHAR(20) | |
| email | VARCHAR(255) | |
| address | TEXT | Địa chỉ thường trú |
| current_address | TEXT | Địa chỉ hiện tại |
| dept_id | BIGINT FK | Bộ phận |
| position_id | BIGINT FK | Chức vụ |
| title_id | BIGINT FK | Chức danh |
| hire_date | DATE | Ngày tuyển dụng |
| probation_end_date | DATE | Hết thử việc |
| official_date | DATE | Ngày chính thức |
| leave_date | DATE | Ngày nghỉ việc |
| status | ENUM | active, on_leave, resigned |
| bank_account_no | VARCHAR(50) | TK ngân hàng nhận lương |
| bank_id | VARCHAR(20) | Ngân hàng |
| ethnicity_id | BIGINT FK | |
| religion_id | BIGINT FK | |
| marital_status_id | BIGINT FK | |
| nationality_id | BIGINT FK | |
| province_id | BIGINT FK | Tỉnh |
| district_id | BIGINT FK | Quận/huyện |
| ward_id | BIGINT FK | Phường/xã |
| education_level_id | BIGINT FK | Trình độ |
| avatar | VARCHAR(500) | Ảnh |

**`family_relation`**:
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| relation_type_id | BIGINT FK | Quan hệ |
| full_name | VARCHAR(255) | |
| birth_date | DATE | |
| id_card_no | VARCHAR(20) | |
| is_dependent | BOOL | Người phụ thuộc (giảm trừ gia cảnh) |
| dependent_from | DATE | |
| dependent_to | DATE | |

**`labor_contract`** (Hợp đồng lao động):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| contract_no | VARCHAR(50) | Số HĐ |
| contract_type | ENUM | probation, official, appendixed |
| parent_contract_id | BIGINT FK | Cho appendix |
| start_date | DATE | |
| end_date | DATE | nullable nếu không xác định |
| position_id | BIGINT FK | |
| title_id | BIGINT FK | |
| dept_id | BIGINT FK | |
| base_salary | DECIMAL(20,4) | Lương cơ bản |
| allowance | DECIMAL(20,4) | Phụ cấp |
| currency_code | CHAR(3) | |
| job_description | TEXT | |
| work_location | VARCHAR(255) | |
| status | ENUM | active, expired, terminated |

**`work_history`** (Quá trình công tác):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| effective_date | DATE | |
| dept_id | BIGINT FK | BP mới |
| position_id | BIGINT FK | CV mới |
| title_id | BIGINT FK | Chức danh mới |
| salary_change | DECIMAL(20,4) | |
| change_type | ENUM | hire, transfer, promote, demote, salary_change |
| description | TEXT | |

**`insurance_history`** (Quá trình tham gia bảo hiểm):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| period | CHAR(7) | |
| insurance_salary | DECIMAL(20,4) | Lương đóng BHXH |
| social_insurance | DECIMAL(20,4) | Tiền BHXH |
| health_insurance | DECIMAL(20,4) | BHYT |
| unemployment_insurance | DECIMAL(20,4) | BHTN |
| labor_accident | DECIMAL(20,4) | |
| status | ENUM | registered, paused |

**`education_record`**:
| Cột | Kiểu | Note |
|-----|------|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| education_level_id | BIGINT FK | |
| school_name | VARCHAR(255) | |
| major | VARCHAR(255) | |
| start_date | DATE | |
| end_date | DATE | |
| gpa | VARCHAR(20) | |

**`certification`** (Chứng chỉ):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| cert_name | VARCHAR(255) | |
| issuer | VARCHAR(255) | |
| issue_date | DATE | |
| expiry_date | DATE | |
| score | VARCHAR(50) | |

**`reward_discipline`** (Khen thưởng kỷ luật):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| type | ENUM | reward, discipline |
| date | DATE | |
| reason_code | VARCHAR(20) | |
| amount | DECIMAL(20,4) | Tiền thưởng/phạt |
| description | TEXT | |

**`leave_record`** (Nghỉ việc/thai sản):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| leave_type | ENUM | resignation, maternity, child_under_12m |
| start_date | DATE | |
| end_date | DATE | |
| reason | TEXT | |

**`tool_assignment`** (Cấp phát CCDC):
| Cột | Kiểu | Note |
|-----|------|------|
| id | BIGINT PK | |
| employee_id | BIGINT FK | |
| tool_id | BIGINT FK | |
| assign_date | DATE | |
| return_date | DATE | nullable |
| condition | ENUM | new, used, damaged |

## 5. Use cases

### UC-27: Khai báo nhân viên mới

1. NS → Cập nhật số liệu → Hồ sơ nhân viên → Thêm mới
2. Nhập tab "Thông tin chung":
   - Mã NV, họ tên, ngày sinh, giới tính, CMND
   - Phòng ban, chức vụ
3. Tab "Liên hệ":
   - Điện thoại, email, địa chỉ
4. Tab "Hợp đồng":
   - Tạo HĐ thử việc hoặc HĐLĐ
5. Tab "Bảo hiểm":
   - Số sổ BHXH, nơi KCB
6. Tab "Tài khoản ngân hàng":
   - STK, ngân hàng (để gửi lương)
7. Tab "Nghỉ phép":
   - Số ngày phép đầu năm
8. Lưu

### UC-28: Ký HĐLĐ mới cho NV

1. NS → Hợp đồng lao động → Thêm mới
2. Chọn NV (đang thử việc hoặc hết HĐ cũ)
3. Nhập:
   - Số HĐ, loại HĐ
   - Ngày bắt đầu/kết thúc
   - Lương cơ bản, phụ cấp
   - Chức vụ, bộ phận
4. Lưu → tự động tạo `work_history` với change_type='hire' hoặc 'promote'

### UC-29: Cấp phát CCDC cho NV

1. NS → Cấp phát CCDC → Thêm mới
2. Chọn NV, CCDC
3. Nhập ngày cấp, tình trạng
4. Hạch toán (sang module CCDC): N142 / C111 (nếu mua mới), hoặc giữ nguyên TK 142 (nếu cấp từ kho CCDC)

## 6. Validation rules

- Mã NV duy nhất trong công ty
- Số CMND/CCCD duy nhất
- Ngày tuyển dụng ≤ ngày chính thức
- Số sổ BHXH duy nhất
- HĐ thử việc: start_date < HĐLĐ start_date

## 7. Phân quyền

- `hr.employee.view`, `.create`, `.edit`, `.delete`
- `hr.employee.view_sensitive` (xem thông tin nhạy cảm: lương, CMND)
- `hr.contract.view`, `.create`
- `hr.leave.manage`
- `hr.tool.assign`

---

**Tiếp theo**: [10. Tiền lương, chấm công](./10-tien-luong-cham-cong.md)
