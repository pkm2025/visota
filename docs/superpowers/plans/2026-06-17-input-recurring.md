# Input Processing + Recurring Automation + Document Flow

## Part 1: Input Invoice Processing (đầu vào)

### InputInvoice model

```python
class InputInvoice(CompanyOwnedModel):
    """Hóa đơn đầu vào từ NCC — nhận được, xử lý, khớp."""
    DIRECTION_CHOICES = [('input', 'Đầu vào'), ('output', 'Đầu ra')]

    company = FK
    direction = 'input'  # always input for this model
    invoice_no = CharField
    invoice_date = DateField
    seller_tax_code = CharField  # MST người bán
    seller_name = CharField
    seller_address = Text
    buyer_tax_code = CharField  # MST công ty mình
    amount_before_vat = Decimal  # GT chưa VAT
    vat_rate = Decimal
    vat_amount = Decimal
    total_amount = Decimal
    currency_code = 'VND'

    # Linking
    purchase_invoice = FK to PurchaseInvoice (nullable)  # matched PI
    einvoice_xml = TextField (nullable)  # raw XML from TCT
    scanned_file = FileField  # upload scan

    # Processing
    extraction_status = CharField  # pending/extracted/matched/excluded
    extracted_data = JSONField  # parsed result from OCR/XML
    processed_at = DateTime
    processed_by = FK User

    # Audit
    created_at, updated_at
```

### InvoiceExtractionService

```python
class InvoiceExtractionService:
    """Extract invoice data from uploaded files."""

    def extract_from_pdf(self, pdf_file) -> dict:
        """Extract text from PDF, parse invoice fields."""
        # 1. Read PDF text
        # 2. Regex/parse for: invoice_no, date, MST, amounts, VAT
        # 3. Return structured dict

    def extract_from_xml(self, xml_string) -> dict:
        """Parse e-invoice XML from TCT."""
        # Parse XML structure for Vietnamese e-invoice schema

    def extract_from_image(self, image_file) -> dict:
        """OCR image to extract invoice data."""
        # Use Tesseract or similar

    def auto_create_purchase_invoice(self, input_invoice) -> PurchaseInvoice:
        """From extracted data, auto-create PurchaseInvoice + voucher."""
        # 1. Find or create Vendor from seller_tax_code
        # 2. Create PurchaseInvoice with extracted amounts
        # 3. Auto-post voucher (N156/N1331/C331)
        # 4. Link InputInvoice ↔ PurchaseInvoice
```

### UI: Input invoice upload + processing

- `/modern/input-invoices/` — list of input invoices with status badges
- `/modern/input-invoices/upload/` — upload PDF/image/XML
- Auto-extraction on upload → preview → confirm → auto-create PI + voucher
- `/modern/input-invoices/<id>/match/` — match to existing PI if auto-match fails

---

## Part 2: Recurring Entry Automation (bút toán định kỳ)

### RecurringTemplate model

```python
class RecurringTemplate(CompanyOwnedModel):
    """Template for automated recurring accounting entries."""
    name = CharField  # 'Khấu hao TSCĐ hàng tháng'
    description = Text
    service_func = CharField  # 'apps.assets.services.DepreciationService.calculate_period'
    schedule_type = CharField  # monthly/quarterly/yearly
    day_of_month = SmallInt  # run on day N
    is_active = Bool
    last_run_at = DateTime
    last_run_result = JSON
    next_run_at = DateTime
```

### RecurringService

```python
class RecurringService:
    """Run all due recurring templates."""

    def run_all_due(self) -> list:
        """Find all active templates where next_run <= now, execute them."""
        templates = RecurringTemplate.objects.filter(is_active=True, next_run_at__lte=now())
        results = []
        for t in templates:
            result = self.run_one(t)
            results.append(result)
        return results

    def run_one(self, template) -> dict:
        """Execute a single template's service function."""
        # Import and call the service function
        # Capture result
        # Update last_run_at, next_run_at
        # Create audit record

    def setup_defaults(self, company):
        """Create default recurring templates for a new company."""
        defaults = [
            ('Khấu hao TSCĐ/CCDC', 'apps.assets.services.DepreciationService', 'monthly', 1),
            ('Tính lương định kỳ', 'apps.payroll.services.PayrollService', 'monthly', 28),
            ('Phân bổ CCDC ngắn hạn (142)', '...AllocationService', 'monthly', 1),
            ('Kết chuyển cuối tháng', '...PeriodClosingService', 'monthly', 28),
        ]
```

### Pre-built recurring entries

| Template | Schedule | Service | Output |
|----------|----------|---------|--------|
| Khấu hao TSCĐ | Ngày 1 hàng tháng | DepreciationService | N642/C2141 |
| Tính lương | Ngày 28 hàng tháng | PayrollService | N642/C334/C3336/C3383-6 |
| Phân bổ CCDC | Ngày 1 hàng tháng | AllocationService | N641/642/C142 |
| Phân bổ TPR (242) | Ngày 1 hàng tháng | AllocationService | N641/642/C242 |
| Kết chuyển cuối kỳ | Ngày cuối tháng | PeriodClosingService | KC → 911 → 421 |
| Đánh giá tỷ giá | Ngày cuối quý | FxRevaluationService | N/C 413 |

### UI: Recurring management

- `/modern/recurring/` — list templates with status + last/next run
- `/modern/recurring/run/` — manually trigger all due templates
- Button per template to run now

---

## Part 3: Document Flow Linking

### DocumentFlow model (lightweight linking)

Instead of a heavy model, use a simple approach:

```python
class DocumentLink(models.Model):
    """Links any two documents bidirectionally."""
    source_type = CharField  # 'voucher', 'sales_invoice', 'purchase_invoice', 'input_invoice', 'contract', 'minutes'
    source_id = BigInt
    target_type = CharField
    target_id = BigInt
    link_type = CharField  # 'generated_from', 'matched_to', 'signed_scan_of', 'attached_to'
    created_at = DateTime
```

### Flow visualization

From voucher detail, show full chain:
```
Input Invoice (scan from NCC)
  → extracted → Purchase Invoice (PN0001)
    → generated → Voucher (N156/N1331/C331)
      → attached → Scanned contract
      → attached → Signed minutes
```

---

## Execution: 5 tasks

### Task 1: InputInvoice model + extraction service
### Task 2: Input invoice UI (upload + list + auto-match)
### Task 3: RecurringTemplate model + RecurringService
### Task 4: Recurring UI + default templates
### Task 5: Sidebar + seed + final verification
