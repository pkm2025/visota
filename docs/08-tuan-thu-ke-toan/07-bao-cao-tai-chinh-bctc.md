# 07. Báo cáo tài chính (BCTC)

> Mẫu BCTC theo TT133/TT200 và cách triển khai trong PMKetoan.

## 1. Bộ BCTC đầy đủ

| Báo cáo | TT133 | TT200 |
|---------|-------|-------|
| Bảng cân đối tài khoản | S06-DN | F01b-DNN |
| BCTH tài chính | B01a-DN | B01-DN |
| BC KQ HĐKD | B02a-DN | B02-DN |
| BC Lưu chuyển tiền tệ | B03a-DN | B03-DN |
| Thuyết minh BCTC | B09a-DN | B09-DN |

## 2. Bảng cân đối tài khoản (S06-DN)

```
Đơn vị: .....................
Địa chỉ: ....................

BẢNG CÂN ĐỐI TÀI KHOẢN
Kỳ: Tháng/Quý/Năm ...

Chỉ tiêu      | Số dư đầu |          | Phát sinh |          | Số dư cuối |          |
TK   | Tên TK | Nợ        | Có       | Nợ        | Có       | Nợ         | Có       |
-----|--------|-----------|----------|-----------|----------|------------|----------
111  | Tiền mặt | 100.000  |          | 50.000    | 30.000   | 120.000    |
131  | PT khách | 200.000  |          | 150.000   | 100.000  | 250.000    |
156  | Hàng hóa | 500.000  |          | 200.000   | 150.000  | 550.000    |
211  | TSCĐ    | 1.500.000 |          |           |          | 1.500.000  |
214  | Hao mòn |           | 600.000  |           | 25.000   |            | 625.000
311  | Vay     |           | 800.000  |           |          |            | 800.000
331  | PT NCC  |           | 150.000  | 100.000   | 50.000   |            | 100.000
411  | Vốn CSH |           | 850.000  |           |          |            | 850.000
421  | Lợi nhuận|          |          |           | 95.000   |            | 95.000
511  | Doanh thu|          |          |           | 350.000  |            | 350.000
632  | Giá vốn |          |          | 150.000   |          | 150.000    |
641  | CP bán  |          |          | 30.000    |          | 30.000     |
642  | CP QL   |          |          | 75.000    |          | 75.000     |
-----|--------|-----------|----------|-----------|----------|------------|----------
Tổng cộng     | 2.300.000 | 2.300.000| 1.030.000 | 1.030.000| 2.545.000  | 2.545.000
```

**Tính chất quan trọng**:
- Tổng số dư N = Tổng số dư C (đầu kỳ, phát sinh, cuối kỳ)
- Đây là check quan trọng sau khi ghi sổ

## 3. B01a-DN - Báo cáo tình hình tài chính (Balance Sheet)

```
STT | Chỉ tiêu | Số cuối kỳ | Số đầu năm
----|----------|------------|-----------
A   | TÀI SẢN  |            |
I   | Tài sản ngắn hạn | 950.000 |
1   | Tiền và tương đương | 120.000 |
2   | Đầu tư TC ngắn hạn | -      |
3   | Các khoản phải thu | 250.000 |
4   | Hàng tồn kho | 550.000 |
5   | Tài sản ngắn hạn khác | 30.000 |
II  | Tài sản dài hạn | 875.000 |
1   | Các khoản phải thu dài hạn | - |
2   | Tài sản cố định | 875.000 | 
    | - Nguyên giá | 1.500.000 |
    | - Hao mòn lũy kế | (625.000) |
    | - GT còn lại | 875.000 |
3   | Bất động sản đầu tư | - |
4   | Đầu tư tài chính dài hạn | - |
5   | Tài sản dài hạn khác | - |
    | TỔNG CỘNG TÀI SẢN (A) | 1.825.000 |

B   | NGUỒN VỐN |            |
C   | Nợ phải trả | 930.000 |
I   | Nợ ngắn hạn | 930.000 |
1   | Vay và nợ thuê TC | 800.000 |
2   | Phải trả NCC | 100.000 |
3   | Thuế và các khoản phải nộp NN | 20.000 |
4   | Phải trả người lao động | 10.000 |
II  | Nợ dài hạn | - |
D   | Vốn chủ sở hữu | 895.000 |
I   | Vốn đầu tư của CSH | 850.000 |
II  | Lợi nhuận chưa PP | 95.000 | 45.000 |
    | TỔNG CỘNG NGUỒN VỐN (B) | 1.825.000 |
```

**Tính chất**: A = B (Tổng TS = Tổng Nguồn vốn)

## 4. B02a-DN - Báo cáo KQ HĐKD (P&L)

```
STT | Chỉ tiêu | Năm nay | Năm trước
----|----------|---------|----------
1   | Doanh thu (511) | 350.000 |
2   | Các khoản giảm trừ DT (521, 531, 532) | - |
3   | Doanh thu thuần (1-2) | 350.000 |
4   | Giá vốn hàng bán (632) | 150.000 |
5   | Lợi nhuận gộp (3-4) | 200.000 |
6   | Doanh thu HĐTC (515) | - |
7   | Chi phí tài chính (635) | 20.000 |
    | - Trong đó: Chi phí lãi vay | 20.000 |
8   | Chi phí bán hàng (641) | 30.000 |
9   | Chi phí QLDN (642) | 75.000 |
10  | LN từ HĐKD (5+6-7-8-9) | 75.000 |
11  | Thu nhập khác (711) | - |
12  | Chi phí khác (811) | - |
13  | LN khác (11-12) | - |
14  | Tổng LN trước thuế (10+13) | 75.000 |
15  | CPTHUẾ TNDN (821) | 15.000 |
16  | LN sau thuế (14-15) | 60.000 |
17  | EPS cơ bản | 6.000 |
18  | EPS pha loãng | - |
```

## 5. B03a-DN - Báo cáo lưu chuyển tiền tệ

### 5.1. Phương pháp trực tiếp

```
I. DÒNG TIỀN TỪ HĐKD
1   | Tiền thu từ KH, người mua | 280.000 |
2   | Tiền trả cho NCC, người bán | 200.000 |
3   | Tiền thu khác từ HĐKD | - |
4   | Tiền chi khác cho HĐKD | 105.000 |
    | DÒNG TIỀN RÒNG TỪ HĐKD (1-2+3-4) | -25.000 |

II. DÒNG TIỀN TỪ HĐĐT
1   | Tiền thu từ thanh toán, bán TS, thu HĐĐT | - |
2   | Tiền chi để mua sắm, XD TSCĐ | - |
    | DÒNG TIỀN RÒNG TỪ HĐĐT | - |

III. DÒNG TIỀN TỪ HĐTC
1   | Tiền vay | - |
2   | Tiền chi trả nợ gốc vay | - |
3   | Tiền thu từ cổ đông | - |
4   | Tiền trả cổ đông | - |
    | DÒNG TIỀN RÒNG TỪ HĐTC | - |

TĂNG/GIẢM TIỀN TRONG KỲ | -25.000 |
Tiền đầu kỳ | 145.000 |
TIỀN CUỐI KỲ | 120.000 |
```

### 5.2. Phương pháp gián tiếp

Điều chỉnh LNST → dòng tiền:

```
LN sau thuế | 60.000 |
(+) Khấu hao TSCĐ | 25.000 |
(+) Tăng "Chi phí trả trước" | - |
(-) Tăng "Phải thu khách hàng" | (50.000) |
(-) Tăng "Hàng tồn kho" | (50.000) |
(+) Tăng "Phải trả NCC" | (50.000) |
(+) Tăng "Phải trả khác" | 10.000 |
DÒNG TIỀN RÒNG TỪ HĐKD | -5.000 |
...
```

## 6. Triển khai trong PMKetoan

### 6.1. Report template definition

```python
# apps/reporting/services/balance_sheet_generator.py
from decimal import Decimal
from apps.ledger.models import AccountPeriodBalance

class BalanceSheetGenerator:
    """Sinh B01-DN (Balance Sheet) theo TT133 hoặc TT200"""
    
    TEMPLATE = {
        'A': {
            'name': 'TÀI SẢN',
            'rows': [
                ('I', 'Tài sản ngắn hạn', '=I.1+I.2+I.3+I.4+I.5', False),
                ('I.1', 'Tiền và tương đương', '=111+112+113', False),
                ('I.2', 'Đầu tư TC ngắn hạn', '=121+128-129', False),
                ('I.3', 'Các khoản phải thu', '=131-129+136+138+141', False),
                ('I.4', 'Hàng tồn kho', '=152+153+154+155+156-159', False),
                ('I.5', 'Tài sản ngắn hạn khác', '=1388+241+242', False),
                
                ('II', 'Tài sản dài hạn', '=II.1+II.2+II.3+II.4+II.5', False),
                ('II.1', 'Các khoản phải thu dài hạn', '=1388', False),
                ('II.2', 'Tài sản cố định', '=211+212+213-214+217', False),
                ('II.3', 'Bất động sản đầu tư', '=221', False),
                ('II.4', 'Đầu tư tài chính dài hạn', '=228-229', False),
                ('II.5', 'Tài sản dài hạn khác', '=242', False),
            ]
        },
        'B': {
            'name': 'NGUỒN VỐN',
            'rows': [
                ('C', 'Nợ phải trả', '=C.I+C.II', True),
                ('C.I', 'Nợ ngắn hạn', '=311+331+333+334+335+338', True),
                ('C.II', 'Nợ dài hạn', '=341', True),
                
                ('D', 'Vốn chủ sở hữu', '=D.I+D.II+D.III+D.IV', True),
                ('D.I', 'Vốn đầu tư CSH', '=411', True),
                ('D.II', 'Chênh lệch đánh giá lại TS', '=412', True),
                ('D.III', 'Chênh lệch tỷ giá', '=413', True),
                ('D.IV', 'Quỹ khen thưởng, phúc lợi', '=418', True),
                ('D.V', 'LN chưa phân phối', '=421', True),
            ]
        }
    }
    
    def generate(self, company_id, fiscal_year, period):
        # Lấy số dư cuối kỳ của tất cả TK
        balances = self._get_balances(company_id, fiscal_year, period)
        
        # Tính từng dòng theo template
        result = self._evaluate_template(self.TEMPLATE, balances)
        
        # Validation: A = B
        total_a = result['A']['total']
        total_b = result['B']['total']
        assert abs(total_a - total_b) < Decimal('1'), \
            f"BS not balanced: {total_a} vs {total_b}"
        
        return result
    
    def _get_balances(self, company_id, fiscal_year, period):
        qs = AccountPeriodBalance.objects.filter(
            company_id=company_id,
            fiscal_year=fiscal_year,
            period=period,
        )
        return {
            b.account_code: (
                b.closing_debit - b.closing_credit
                if b.closing_debit > 0 else
                b.closing_credit - b.closing_debit
            )
            for b in qs
        }
```

### 6.2. Trial balance generator

```python
class TrialBalanceGenerator:
    def generate(self, company_id, fiscal_year, from_period, to_period):
        # Lấy số dư đầu năm
        opening = self._get_opening_balances(company_id, fiscal_year)
        
        # Lấy phát sinh trong khoảng [from_period, to_period]
        movements = self._get_period_movements(
            company_id, fiscal_year, from_period, to_period
        )
        
        # Tính số dư cuối
        result = []
        for acc_code, opening_debit in opening.items():
            opening_credit = opening.get((acc_code, 'C'), 0)
            period_debit, period_credit = movements.get(acc_code, (0, 0))
            
            closing_debit = opening_debit + period_debit - period_credit
            if closing_debit < 0:
                closing_credit = -closing_debit
                closing_debit = 0
            else:
                closing_credit = 0
            
            result.append({
                'account_code': acc_code,
                'opening_debit': opening_debit,
                'opening_credit': opening_credit,
                'period_debit': period_debit,
                'period_credit': period_credit,
                'closing_debit': closing_debit,
                'closing_credit': closing_credit,
            })
        
        # Sort theo account_code
        result.sort(key=lambda x: x['account_code'])
        
        return result
```

### 6.3. P&L generator

```python
class PnLGenerator:
    def generate(self, company_id, fiscal_year, from_period, to_period):
        # Lấy phát sinh Nợ của TK chi phí (6, 8)
        # Lấy phát sinh Có của TK doanh thu (5, 7)
        
        revenue_511 = self._get_credit_movement('511', ...)
        revenue_515 = self._get_credit_movement('515', ...)
        deduction_521 = self._get_debit_movement('521', ...)
        cogs_632 = self._get_debit_movement('632', ...)
        selling_641 = self._get_debit_movement('641', ...)
        admin_642 = self._get_debit_movement('642', ...)
        fin_635 = self._get_debit_movement('635', ...)
        other_income_711 = self._get_credit_movement('711', ...)
        other_expense_811 = self._get_debit_movement('811', ...)
        tax_821 = self._get_debit_movement('821', ...)
        
        revenue_net = revenue_511 - deduction_521
        gross_profit = revenue_net - cogs_632
        operating_profit = gross_profit + revenue_515 - fin_635 - selling_641 - admin_642
        other_profit = other_income_711 - other_expense_811
        profit_before_tax = operating_profit + other_profit
        profit_after_tax = profit_before_tax - tax_821
        
        return {
            'revenue': revenue_511,
            'deduction': deduction_521,
            'revenue_net': revenue_net,
            'cogs': cogs_632,
            'gross_profit': gross_profit,
            # ...
            'profit_after_tax': profit_after_tax,
        }
```

## 7. Xuất BCTC

### 7.1. PDF (WeasyPrint)

```python
# apps/reporting/services/pdf_exporter.py
from weasyprint import HTML
from django.template.loader import render_to_string

class PDFExporter:
    def export_balance_sheet(self, data):
        html = render_to_string('reporting/balance_sheet_pdf.html', data)
        return HTML(string=html).write_pdf()
```

### 7.2. Excel (openpyxl)

```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border

class ExcelExporter:
    def export_trial_balance(self, data):
        wb = Workbook()
        ws = wb.active
        ws.title = 'S06-DN'
        
        # Header
        ws['A1'] = 'BẢNG CÂN ĐỐI TÀI KHOẢN'
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        ws.merge_cells('A1:G1')
        
        # Column headers
        headers = ['TK', 'Tên TK', 'Số dư đầu Nợ', 'Số dư đầu Có', 
                   'PS Nợ', 'PS Có', 'Số dư cuối Nợ', 'Số dư cuối Có']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Data rows
        for row_idx, row in enumerate(data, 4):
            for col_idx, value in enumerate([
                row['account_code'], row['account_name'],
                row['opening_debit'], row['opening_credit'],
                row['period_debit'], row['period_credit'],
                row['closing_debit'], row['closing_credit'],
            ], 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                if col_idx > 2:
                    cell.number_format = '#,##0'
        
        return wb
```

## 8. Validation rules

- BS: Tổng TS = Tổng Nguồn vốn (A = B)
- P&L: LN sau thuế = LNST - thuế TNDN
- CF: Tiền đầu kỳ + Δ tiền = Tiền cuối kỳ
- BCĐTK: Tổng N = Tổng C (đầu kỳ, PS, cuối kỳ)

## 9. Tần suất lập BCTC

| Loại | Kỳ | Hạn nộp |
|------|----|---------|
| BCTC giữa niên độ | 6 tháng | 30/7 |
| BCTC năm | 12 tháng | 90 ngày từ ngày kết thúc năm TC |

## 10. Nguồn tham khảo

- 🔗 [BCTC theo TT133](https://ketoanthienung.net/bao-cao-tai-chinh-theo-thong-tu-133.htm)
- 🔗 [BCTC theo TT200](https://luatvietnam.vn/tai-chinh/bao-cao-tai-chinh-theo-thong-tu-200-2014-tt-btc-80408-d1.html)
- 🔗 [Mẫu B01a-DN](https://luatvietnam.vn/wp-content/uploads/2020/08/B01a-DN_bao_cao_tinh_hinh_tai_chinh.png)

---

**Tiếp theo**: [Kế hoạch triển khai →](../09-ke-hoach-trien-khai/01-roadmap.md)
