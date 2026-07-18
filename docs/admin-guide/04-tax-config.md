# A4 — Cấu hình Thuế & Tuân thủ

> Hướng dẫn cấu hình 14 loại thuế VN + TT133/TT200 + PIT 2026.

## 1. Cấu hình thuế (TaxRateConfig)

Sidebar → **Hệ thống → Cấu hình** (hoặc Django admin `/admin/core/taxrateconfig/`)

### 14 loại thuế hỗ trợ

| Code | Tên | Tỷ lệ |
|------|-----|-------|
| `VAT` | GTGT | 0/5/8/10% |
| `CIT` | TNDN | 15/17/20% (theo SME size) |
| `PIT` | TNCN | 7 bậc lũy tiến 5-35% |
| `SCT` | TTĐB | Theo nhóm hàng |
| `EPT` | Bảo vệ môi trường | Theo nhóm |
| `IMP` | Nhập khẩu | 0/5/10/15/20% |
| `EXP` | Xuất khẩu | 0/5% |
| `FCT` | Nhà thầu | 5% (cho KH nước ngoài) |
| `MB` | Lệ phí môn bài | 1-3M/năm |
| `RB` | Lệ phí trước bạ | 0.5-12% |
| `NR` | Tài nguyên | Theo loại |
| `AL` | SD đất nông nghiệp | Theo hạng |
| `LB` | Lợi tức vốn | 5% |
| `CAP` | Chuyển nhượng vốn | 0.1% |

### Cấu hình VAT theo ND-174/2025 (giảm 8%)

Per Nghi định 174/2025/NĐ-CP, một số ngành được giảm VAT 8% đến 30/06/2026:

```bash
python manage.py shell -c "
from apps.core.models import TaxRateConfig, Company
config = TaxRateConfig.objects.get_or_create(company=Company.objects.first())[0]
# Cấu hình VAT
config.vat_rates = {
    'standard': 10.0,
    'reduced_8pct': 8.0,
    'zero': 0.0,
    'exempt': 0.0,
}
# PIT 2026 (effective 01/07/2026 per Luật 09/2026/QH16)
config.pit_self_deduction = 13_200_000  # 13.2M (was 11M)
config.pit_dependent_deduction = 5_200_000  # 5.2M
config.pit_brackets = [
    (0, 5_000_000, 0.05),
    (5_000_000, 10_000_000, 0.10),
    (10_000_000, 18_000_000, 0.15),
    (18_000_000, 32_000_000, 0.20),
    (32_000_000, 52_000_000, 0.25),
    (52_000_000, 80_000_000, 0.30),
    (80_000_000, None, 0.35),
]
# CIT
config.cit_standard_rate = 0.20  # 20%
config.cit_sme_rate = 0.15  # 15% for SME (TT200)
# BHXH
config.bhxh_employee_rate = 0.105  # 10.5%
config.bhxh_employer_rate = 0.215  # 21.5%
config.kpcd_rate = 0.02  # 2% Kinh phí công đoàn
config.save()
"
```

## 2. Chế độ kế toán (AccountingRegime)

Per **TT133/2016** (SME) hoặc **TT200/2014** (lớn):

```bash
python manage.py shell -c "
from apps.core.models import Company
c = Company.objects.first()
c.accounting_regime = 'tt133'  # hoặc 'tt200'
c.sme_size = 'small'  # micro/small/medium/large
c.save()
"
```

SME size theo **ND 80/2021**:
- Micro: ≤ 3 tỷ revenue, ≤ 100 employees
- Small: ≤ 50 tỷ, ≤ 200 employees (được dùng TT133)
- Medium: ≤ 300 tỷ, ≤ 300 employees
- Large: > 300 tỷ (dùng TT200)

## 3. Hệ thống tài khoản

Load 116 tài khoản TT133 hoặc 200 TK TT200:

```bash
# TT133 (mặc định cho SME)
python manage.py load_tt133

# TT200 (cho công ty lớn)
python manage.py load_tt200
```

Kiểm tra:
- Sidebar → **Danh mục → Hệ thống tài khoản**
- Có 116 (TT133) hoặc 200 (TT200) tài khoản

## 4. PIT rate history

Hệ thống track PIT history qua `PITRateHistory`:

| Period | Self deduction | Dependent | Brackets |
|--------|---------------|-----------|----------|
| 2009-2012 | 4M | 1.6M | 4 bậc |
| 2013-2020 | 9M | 3.6M | 7 bậc |
| 2020-06/2026 | 11M | 4.4M | 7 bậc |
| 07/2026+ | 13.2M | 5.2M | 7 bậc |

Khi tính lương kỳ:
```python
# Tự động lấy config phù hợp với kỳ
from apps.payroll.services import TaxConfigService
rate = TaxConfigService.get_pit_rate(year=2026, month=7)  # returns 13.2M
```

## 5. Cấu hình HĐĐT (EInvoiceConfig)

Sidebar → **Hệ thống → HĐĐT** (chi tiết [10-einvoice](../user-guide/10-einvoice.md))

## 6. Cấu hình email (SMTP)

`config/settings/prod.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = f'Visota ERP <{EMAIL_HOST_USER}>'
```

Test:
```bash
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('test', 'body', DEFAULT_FROM_EMAIL, ['test@example.com'])
"
```

## 7. Tuân thủ pháp lý (LegalReference)

Sidebar → **Right sidebar → Quy định pháp luật** để xem 39+ văn bản VN:
- Luật Kế toán 2015
- TT133/2016/TT-BTC
- TT200/2014/TT-BTC
- TT78/2021/TT-BTC (HĐĐT)
- TT80/2021/TT-BTC (thuế)
- Luật Đấu thầu 23/2023/QH15
- ND 174/2025 (giảm VAT)
- Luật 09/2026/QH16 (PIT mới)

## 8. Kiểm tra cấu hình

Sau khi cấu hình xong, verify:

```bash
python manage.py shell <<'EOF'
from apps.core.models import Company, TaxRateConfig
c = Company.objects.first()
print(f'Company: {c.name} ({c.accounting_regime})')
print(f'SME size: {c.sme_size}')
config = TaxRateConfig.objects.filter(company=c).first()
if config:
    print(f'VAT standard: {config.vat_rates.get("standard") if config.vat_rates else "?"}')
    print(f'PIT self deduction: {config.pit_self_deduction or 11000000}')
    print(f'CIT rate: {config.cit_standard_rate}')
    print(f'BHXH NLĐ: {config.bhxh_employee_rate * 100}%')
    print(f'BHXH NSD: {config.bhxh_employer_rate * 100}%')

from apps.master_data.models import ChartOfAccounts
print(f'HTTK: {ChartOfAccounts.objects.filter(company=c).count()} tài khoản')
EOF
```

## 9. Update thuế theo luật mới

Khi luật thay đổi (VD: tăng PIT thêm):

1. Update `TaxRateConfig` qua admin
2. Tạo `PITRateHistory` mới với effective_date
3. Test với PayrollRun kỳ mới
4. Notification cho toàn bộ user

```bash
python manage.py shell -c "
from apps.core.models import PITRateHistory
PITRateHistory.objects.create(
    effective_from='2027-01-01',
    self_deduction=15_000_000,  # giả sử tăng
    dependent_deduction=6_000_000,
    brackets=[...],
    legal_basis='Luật 09/2026/QH16 (sửa đổi)',
)
"
```

---

Tài liệu liên quan:
- [06-hr-payroll](../user-guide/06-hr-payroll.md) — Tính lương + PIT
- [10-einvoice](../user-guide/10-einvoice.md) — HĐĐT
- [04-pit-filing](../runbook/04-pit-filing.md) — Kê khai PIT
