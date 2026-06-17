# Design Spec: Full HR Module — HĐLĐ + BHXH + PIT + Nghỉ phép + Báo cáo

## 1. Tổng quan

Mở rộng `apps/hr` + `apps/payroll` thành module HR đầy đủ, liên kết chặt với kế toán qua auto-voucher.

## 2. Pháp lý áp dụng

| Văn bản | Nội dung áp dụng |
|---------|-----------------|
| BLLĐ 45/2019/QH14 | Loại HĐLĐ, thử việc, nghỉ phép 12 ngày |
| Luật BHXH 2014 (sửa đổi) | BHXH/BHYT/BHTN tỷ lệ 10.5% NV + 21.5% DN |
| ND 73/2024/NĐ-CP | Lương cơ sở 2,340,000 → trần đóng 46.8M |
| Luật Việc làm 2025 | BHTN NV+DN mỗi bên 1% |
| TT 111/2013/TT-BTC | Thuế TNCN lũy tiến 7 bậc, GTGC 11M + 4.4M/NPT |
| ND 145/2018/NĐ-CP | Kinh phí công đoàn 2% quỹ lương |

## 3. Tỷ lệ BHXH chính xác (2025-2026)

```
                    NV đóng    DN đóng    Tổng
BHXH (hưu trí)      8.0%       14.0%      22.0%
BHXH (ốm/thai sản)  —           3.0%       3.0%
BHTNLĐ-BNN          —           0.5%       0.5%
BHYT                 1.5%        3.0%       4.5%
BHTN                 1.0%        1.0%       2.0%
─────────────────────────────────────────────────
TỔNG                 10.5%      21.5%      32.0%
KPCĐ (công đoàn)     —           2.0%       2.0%

Trần đóng: 20 × 2,340,000 = 46,800,000 VND/tháng
```

## 4. Models mới / mở rộng

### 4.1 LaborContract (mở rộng apps/contracts hoặc apps/hr)

```python
class LaborContract(CompanyOwnedModel):
    employee = FK Employee
    contract_type = Enum: PROBATION / FIXED_TERM / INDEFINITE / SEASONAL
    contract_no = CharField
    start_date = DateField
    end_date = DateField (nullable cho INDEFINITE)
    probation_end_date = DateField
    
    # Lương
    salary_base = DecimalField          # Lương cơ bản (căn cứ đóng BHXH)
    salary_gross = DecimalField         # Tổng thu nhập (base + allowance)
    allowance_amount = DecimalField     # Phụ cấp
    currency_code = 'VND'
    
    # BHXH
    insurance_salary_base = DecimalField  # Lương đóng BHXH (≤ trần 46.8M)
    join_insurance = BooleanField         = True
    
    # Thông tin HĐ
    position = CharField
    department = FK Department
    work_location = CharField
    signing_date = DateField
    signed_file = FileField
    
    status = Enum: DRAFT / ACTIVE / EXPIRED / TERMINATED
```

### 4.2 Dependent (Người phụ thuộc — giảm trừ gia cảnh)

```python
class Dependent(models.Model):
    employee = FK Employee
    full_name = CharField
    relationship = Enum: SPOUSE / CHILD / PARENT / OTHER
    birth_date = DateField
    id_card_no = CharField
    tax_code = CharField  # MST cá nhân (nếu có)
    deduction_amount = DecimalField(default=4400000)
    valid_from = DateField
    valid_to = DateField (nullable = còn hiệu lực)
    registration_status = Enum: PENDING / REGISTERED / CANCELLED
```

### 4.3 LeaveRecord (Quản lý nghỉ phép)

```python
class LeaveRecord(models.Model):
    employee = FK Employee
    leave_type = Enum: ANNUAL / SICK / MATERNITY / MARRIAGE / FUNERAL / UNPAID
    start_date = DateField
    end_date = DateField
    days = DecimalField  # số ngày nghỉ
    reason = TextField
    approved_by = FK User
    status = Enum: PENDING / APPROVED / REJECTED
    
    # Maternity-specific
    maternity_months = DecimalField (nullable, default=6)
```

### 4.4 LeaveBalance (Số dư phép năm)

```python
class LeaveBalance(models.Model):
    employee = FK Employee
    fiscal_year = SmallInt
    standard_days = DecimalField  # 12 + seniority bonus
    carried_forward = DecimalField
    used_days = DecimalField
    remaining_days = DecimalField  # = standard + carried - used
```

### 4.5 InsuranceContribution (BHXH hàng tháng)

```python
class InsuranceContribution(models.Model):
    company = FK
    employee = FK
    period = CharField  # YYYY-MM
    salary_base = DecimalField  # Lương đóng BHXH (capped)
    
    # NV đóng
    bhxh_employee = DecimalField     # 8%
    bhyt_employee = DecimalField     # 1.5%
    bhtn_employee = DecimalField     # 1%
    total_employee = DecimalField    # 10.5%
    
    # DN đóng
    bhxh_employer = DecimalField    # 17% (14% hưu + 3% ốm/thai)
    bhyt_employer = DecimalField    # 3%
    bhtn_employer = DecimalField    # 1%
    bhtnld_employer = DecimalField  # 0.5%
    total_employer = DecimalField   # 21.5%
    
    kpcd_employer = DecimalField   # 2% kinh phí công đoàn
    
    class Meta:
        unique_together = [('employee', 'period')]
```

## 5. Services

### 5.1 ContractService
- `create_contract()` → tạo HĐ + auto-thiết lập insurance
- `convert_probation()` → chuyển thử việc → chính thức
- `check_expiry()` → cảnh báo HĐ sắp hết

### 5.2 PayrollService (nâng cấp)
- Tính BHXH với **trần đóng** (cap 46.8M)
- Tính PIT với **người phụ thuộc** (4.4M/NPT)
- Tính **kinh phí công đoàn** (2%)
- Tính **BHTNLĐ-BNN** (0.5%)
- Auto-voucher đầy đủ:
  ```
  N641/642  = gross + 21.5% BHXH DN + 2% KPCĐ  (tổng chi phí nhân sự)
  C334      = net thực nhận
  C3336     = thuế TNCN khấu trừ
  C3382     = kinh phí công đoàn (2%)
  C3383     = BHXH (NV 8% + DN 17%)
  C3384     = BHYT (NV 1.5% + DN 3%)
  C3386     = BHTN (NV 1% + DN 1%)
  C3389     = BHTNLĐ-BNN (DN 0.5%) — hoặc TK khác theo setup
  ```

### 5.3 LeaveService
- `calculate_annual_leave(employee, year)` → 12 + floor(thâm_niên/5)
- `request_leave(employee, type, dates)` → tạo LeaveRecord + cập nhật LeaveBalance
- `maternity_calc(employee)` → 6 tháng × lương BHXH → BHXH trả thay

### 5.4 InsuranceService
- `calculate_monthly(employee, period)` → InsuranceContribution
- `generate_d62_report(period)` → Báo cáo D62
- `check_cap(salary)` → min(salary, 46_800_000)

### 5.5 PITService
- `calculate_monthly(gross, insurance_deduction, dependents)` → PIT
- `register_dependent(employee, dependent_data)` → Dependent record
- `year_end_finalization(employee, year)` → Quyết toán TNCN

## 6. Báo cáo

| Báo cáo | API | Output |
|---------|-----|--------|
| **D62** | `/reports/insurance/d62/` | BHXH hàng tháng theo NV |
| **BC lao động** | `/reports/labor-usage/` | SL lao động, biến động |
| **Quỹ lương** | `/reports/salary-fund/` | Tổng quỹ lương kỳ |
| **PIT hàng tháng** | `/reports/pit-monthly/` | TNCN khấu trừ theo NV |
| **Quyết toán TNCN** | `/reports/pit-finalization/` | Năm |

## 7. Auto-voucher đầy đủ

```
PayrollService.post(run):
  N641/642  = total_gross + total_bhxh_employer(21.5%) + total_kpcd(2%)
  C334      = total_net
  C3336     = total_pit
  C3382     = total_kpcd (2%)
  C3383     = total_bhxh (NV 8% + DN 17%)
  C3384     = total_bhyt (NV 1.5% + DN 3%)
  C3386     = total_bhtn (NV 1% + DN 1%)
```

## 8. Implementation tasks (5 groups)

1. **LaborContract + Dependent models** — HĐLĐ lifecycle + người phụ thuộc
2. **InsuranceContribution + LeaveRecord + LeaveBalance** — BHXH + nghỉ phép
3. **Upgrade PayrollService** — trần đóng, NPT, KPCĐ, BHTNLĐ, auto-voucher 8 lines
4. **Báo cáo**: D62, BC lao động, quỹ lương, PIT monthly
5. **UI**: HĐLĐ list/form, dependent mgmt, leave request, insurance dashboard
