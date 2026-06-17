# Full Voucher + Document + Service Industry Module

> Comprehensive plan covering ALL remaining voucher types, accounting books, contracts, minutes, input invoices, and service industry documents per Vietnamese law.

## Legal basis researched

| Văn bản | Áp dụng |
|---------|--------|
| TT133/2016 + TT200/2014 | Chế độ kế toán DN — mẫu sổ, chứng từ |
| ND 123/2020 + TT 78/2021 → TT 32/2025 | Hóa đơn, chứng từ điện tử |
| TT 80/2021 | Tờ khai thuế GTGT (01/GTGT + bảng kê) |
| BL Lao động 2019 | Hợp đồng lao động, thử việc |
| Luật Thương mại 2005 | Hợp đồng mua bán hàng hóa, dịch vụ |
| Luật Xây dựng 2020 | Hợp đồng thi công (cho ngành xây dựng) |
| TT 200/2014 Phụ lục 4 | Danh mục chứng từ kế toán (24 loại) |

---

## Part A: Accounting Books (Sổ sách kế toán)

### A1. Sổ nhật ký chung (S03a-DN)
- View: `/modern/reports/general-journal/`
- Query: `AccountingVoucher.objects.filter(period=).order_by('voucher_date')`
- Output: STT | Ngày | Số CT | Diễn giải | TK Nợ | TK Có | Số tiền

### A2. Sổ cái tài khoản (S03b-DN)
- View: `/modern/reports/general-ledger/<account_code>/`
- Query: `VoucherLine.objects.filter(account_code=).order_by('voucher__voucher_date')`
- Output: Chứng từ | Diễn giải | TK ĐƯ | Nợ | Có | Tồn

### A3. Sổ quỹ tiền mặt (S07-DN)
- Filter: TK 111 transactions
- Opening balance + movements + closing

### A4. Sổ tiền gửi ngân hàng (S08-DN)
- Filter: TK 112 transactions

### A5. Sổ chi tiết công nợ KH (S31-DN)
- Filter: TK 131 by customer
- AR aging per customer

### A6. Thẻ kho (S10-DN)
- View: `/modern/reports/stock-card/<product_id>/`
- Query: `StockLedger movements for product`
- Output: Ngày | CT | Nhập SL/TT | Xuất SL/TT | Tồn SL/TT

### A7. Sổ chi tiết tài khoản (S38-DN)
- Generic detail ledger for any account

---

## Part B: Voucher Forms (Phiếu in)

### B1. Phiếu thu tiền mặt (Form 01-TT)
- Template: `templates/documents/print/cash_receipt.html`
- Data: số CT, ngày, người nộp, địa chỉ, lý do, số tiền, khoản mục
- Hạch toán: N111 / C131, C511, C515...

### B2. Phiếu chi tiền mặt (Form 02-TT)
- Template: `templates/documents/print/cash_payment.html`
- Data: số CT, ngày, người nhận, địa chỉ, lý do, số tiền
- Hạch toán: N331, N641, N642 / C111

### B3. Phiếu thu/chi ngân hàng
- Same as cash but TK 112

### B4. Phiếu nhập kho (Form 03-VT)
- Template: `templates/documents/print/stock_receipt.html`

### B5. Phiếu xuất kho (Form 04-VT)
- Template: `templates/documents/print/stock_issue.html`

### B6. Phiếu tính lương
- Per-employee salary slip with BHXH deductions

---

## Part C: Contract & Minutes Management

### C1. Contract model

```python
class Contract(CompanyOwnedModel):
    class ContractType(models.TextChoices):
        SALE = 'sale', 'Hợp đồng mua bán'
        PURCHASE = 'purchase', 'Hợp đồng mua hàng'
        SERVICE = 'service', 'Hợp đồng cung cấp dịch vụ'
        CONSTRUCTION = 'construction', 'Hợp đồng thi công'
        LABOR = 'labor', 'Hợp đồng lao động'
        LEASE = 'lease', 'Hợp đồng thuê'
        OTHER = 'other', 'Khác'

    contract_no = CharField
    contract_date = DateField
    contract_type = CharField(choices)
    party_code = CharField  # Mã đối tác (KH/NCC)
    party_name = CharField
    party_tax_code = CharField
    party_address = Text
    description = Text
    value = DecimalField  # Giá trị HĐ
    currency_code = CharField
    start_date = DateField
    end_date = DateField
    status = CharField  # draft/active/completed/cancelled
    signed_file = FileField  # Scan HĐ đã ký
    linked_voucher = FK to AccountingVoucher (nullable)
```

### C2. Minutes (Biên bản) model

```python
class Minutes(CompanyOwnedModel):
    class MinutesType(models.TextChoices):
        HANDOVER = 'handover', 'Biên bản bàn giao'
        ACCEPTANCE = 'acceptance', 'Biên bản nghiệm thu'
        INVENTORY = 'inventory', 'Biên bản kiểm kê'
        LIQUIDATION = 'liquidation', 'Biên bản thanh lý'
        RECONCILIATION = 'reconciliation', 'Biên bản đối chiếu'
        ADJUSTMENT = 'adjustment', 'Biên bản điều chỉnh'
        OTHER = 'other', 'Biên bản khác'

    minutes_no = CharField
    minutes_date = DateField
    minutes_type = CharField(choices)
    contract = FK to Contract (nullable)
    party_code = CharField
    description = Text
    signed_file = FileField
    linked_voucher = FK to AccountingVoucher (nullable)
```

---

## Part D: Input Document Management

### D1. InputInvoice model (Hóa đơn đầu vào)

```python
class InputInvoice(CompanyOwnedModel):
    """Hóa đơn GTGT đầu vào từ NCC — đã nhận."""
    invoice_no = CharField
    invoice_date = DateField
    seller_tax_code = CharField
    seller_name = CharField
    seller_address = Text
    amount = DecimalField  # Chưa VAT
    vat_rate = DecimalField
    vat_amount = DecimalField
    total_amount = DecimalField
    purchase_invoice = FK to PurchaseInvoice (nullable)
    einvoice_id = FK to EInvoice (nullable)  # Nếu pull từ TCT
    scanned_file = FileField  # Scan hóa đơn giấy
    status = CharField  # pending/matched/excluded
```

### D2. AdvancePayment (Tạm ứng)

```python
class AdvancePayment(CompanyOwnedModel):
    advance_no = CharField
    advance_date = DateField
    employee = FK to Employee
    amount = DecimalField
    purpose = Text
    expected_settlement_date = DateField
    status = CharField  # open/partial/settled
    settled_amount = DecimalField
```

### D3. AdvanceSettlement (Thanh toán tạm ứng)

```python
class AdvanceSettlement(models.Model):
    advance = FK to AdvancePayment
    settlement_no = CharField
    settlement_date = DateField
    invoice_no = CharField
    amount = DecimalField
    expense_account = CharField  # TK chi phí
```

---

## Part E: Service Industry Vouchers

### E1. ServiceContract (extends Contract)

```python
class ServiceContract(Contract):
    """Hợp đồng cung cấp dịch vụ — mở rộng Contract."""
    service_description = Text  # Mô tả dịch vụ
    billing_cycle = CharField  # monthly/quarterly/per_milestone
    service_period_start = DateField
    service_period_end = DateField
```

### E2. ServiceAcceptance (Biên bản nghiệm thu dịch vụ)

```python
class ServiceAcceptance(Minutes):
    """Biên bản nghiệm thu kết quả dịch vụ."""
    contract = FK to ServiceContract
    period = CharField  # YYYY-MM
    service_amount = DecimalField
    accepted_date = DateField
    accepted_by_customer = BooleanField
```

### E3. ServiceInvoice (extends SalesInvoice)

```python
class ServiceInvoice(SalesInvoice):
    """Hóa đơn dịch vụ — C5112 thay vì C5111."""
    contract = FK to ServiceContract (nullable)
    acceptance = FK to ServiceAcceptance (nullable)
```

---

## Part F: VAT Listing Reports

### F1. Bảng kê hóa đơn đầu ra (01-1/GTGT)

```python
class VATOutputListing:
    """Aggregates SalesInvoice by VAT rate for period."""
    # Query: SalesInvoice.objects.filter(invoice_date__in_period)
    # Group by vat_rate
    # Output: STT | Ký hiệu HĐ | Số HĐ | Ngày | Tên người mua | MST | GT chưa thuế | Thuế suất | Tiền thuế
```

### F2. Bảng kê hóa đơn đầu vào (01-2/GTGT)

```python
class VATInputListing:
    """Aggregates InputInvoice/PurchaseInvoice by VAT rate."""
    # Same structure as output but for purchases
```

---

## Execution Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Sổ cái (S03b-DN) | 1 task | Critical for accountants |
| **P0** | Sổ nhật ký chung (S03a-DN) | 1 task | Critical |
| **P0** | Contract + Minutes models | 1 task | Foundation for docs |
| **P0** | Phiếu thu/chi form + PDF | 1 task | Daily operations |
| **P1** | Thẻ kho (S10-DN) | 1 task | Inventory tracking |
| **P1** | Input invoice management | 1 task | Tax compliance |
| **P1** | Bảng kê VAT đầu ra/đầu vào | 1 task | Tax filing |
| **P1** | Service contract + acceptance | 1 task | Service industry |
| **P2** | Advance payment + settlement | 1 task | Internal operations |
| **P2** | Sổ quỹ TM, TGNH, công nợ | 1 task | Detailed reporting |

---

**Plan complete.** 10 implementation groups. Will execute P0 items first.
