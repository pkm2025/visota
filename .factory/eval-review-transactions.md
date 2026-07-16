# Business Transactions Review: Sales, Purchasing, E-Invoice, Ledger Integration

**Scope:** `apps/sales/`, `apps/purchasing/`, `apps/einvoice/`, `apps/ledger/` (VoucherPostingService, DnsnPostingService), and UI views in `apps/ui_modern/views/`.

**Reviewer date:** 2026-07-16

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High     | 7 |
| Medium   | 6 |
| Low      | 4 |
| **Total** | **21** |

The core tax calculation and VAT posting logic is largely correct for both `khau_tru` and `ty_le_phan_tram` methods, and the TT58 DNSN integration is well-structured. However, there are critical multi-tenant isolation gaps (missing company scoping), XML injection risks in e-invoice generation, a DNSN voucher total double-counting bug, and missing reversal handling for e-invoice adjustments.

---

## Findings

### CRITICAL

#### C-1: Sales/Purchase invoice list views have no company filter (multi-tenant data leak)

**Severity:** Critical
**File:** `apps/ui_modern/views/sales_views.py:22-24`, `apps/ui_modern/views/purchase_views.py:22-24`
**Also:** `apps/ui_modern/views/sales_views.py:37` (create view uses `Company.objects.first()`)

**Description:**
`SalesInvoiceListView.get_queryset()` and `PurchaseInvoiceListView.get_queryset()` return ALL invoices across ALL companies with no company scoping:

```python
def get_queryset(self):
    return SalesInvoice.objects.select_related("customer").order_by("-invoice_date", "-id")
```

The create views use `Company.objects.first()` instead of `request.current_company`, meaning invoices can be created for the wrong tenant. Every other view in the codebase (e.g. `EInvoiceListView`) correctly scopes by `getattr(self.request, "current_company", None)`.

**Impact:** Any logged-in user can see and interact with invoices from every company in the system, violating tenant isolation.

**Fix:**
```python
def get_queryset(self):
    company = getattr(self.request, "current_company", None) or Company.objects.first()
    return (
        SalesInvoice.objects
        .filter(company=company)
        .select_related("customer")
        .order_by("-invoice_date", "-id")
    )
```
Apply the same pattern to `PurchaseInvoiceListView` and both create views.

---

#### C-2: EInvoiceIssueFromSalesView has no company scoping (IDOR)

**Severity:** Critical
**File:** `apps/einvoice/views.py:66-69` (`EInvoiceIssueFromSalesView.post`)

**Description:**
```python
def post(self, request, sales_invoice_id, *args, **kwargs):
    from apps.sales.models import SalesInvoice
    si = get_object_or_404(SalesInvoice, pk=sales_invoice_id)
```
Unlike `EInvoicePublishView`, `EInvoiceCancelView`, and all download views (which all filter `company=company`), this view fetches the `SalesInvoice` by bare PK with no company check. A user can issue an e-invoice from any company's sales invoice by guessing the ID.

**Fix:**
```python
company = getattr(request, "current_company", None) or Company.objects.first()
si = get_object_or_404(SalesInvoice, pk=sales_invoice_id, company=company)
```

---

#### C-3: E-invoice XML generation has no XML escaping (XML injection)

**Severity:** Critical
**File:** `apps/einvoice/services/__init__.py:230-270` (`_build_xml`), also `_build_xml` BC01 report at line 300+

**Description:**
The XML is built via f-string interpolation with no escaping of user-controlled data:

```python
<ItemName>{line.description}</ItemName>
...
<Name>{einvoice.seller_name}</Name>
<TaxCode>{einvoice.seller_tax_code}</TaxCode>
<Address>{einvoice.buyer_address}</Address>
```

If any field (customer name, address, product description, tax code) contains `<`, `>`, `&`, or `"`, the XML becomes malformed or injectable. An attacker (or just a customer named `A&B`) can break the XML, cause provider API submission failures, or inject arbitrary XML nodes.

The same issue exists in `EInvoiceReportService.generate_bc01` for `company.name`, `company.tax_code`, `e.buyer_name`, etc.

**Fix:** Use `xml.sax.saxutils.escape` for text content and `quoteattr` for attributes:
```python
from xml.sax.saxutils import escape

return f"""...
    <Name>{escape(einvoice.seller_name)}</Name>
    <TaxCode>{escape(einvoice.seller_tax_code)}</TaxCode>
    <Address>{escape(einvoice.seller_address)}</Address>
    ..."""
```
Apply to both `_build_xml` and `generate_bc01`. Better yet, use `lxml.etree` or `xml.etree.ElementTree` to build the XML tree and serialize it, which handles escaping automatically.

---

#### C-4: DNSN voucher `total_amount` double-counts revenue + cost + cash + total_amount

**Severity:** Critical
**File:** `apps/ledger/services/dnsn_posting_service.py:138-148` (`_entry_total`)

**Description:**
```python
def _entry_total(self, entry: DnsnLedgerEntry) -> Decimal:
    return (
        entry.revenue_amount
        + entry.cost_amount
        + entry.cash_in
        + entry.cash_out
        + entry.bank_in
        + entry.bank_out
        + entry.total_amount
    )
```

This method sums ALL amount fields unconditionally. For a sales revenue entry, `revenue_amount` is set but `cost_amount`, `cash_in`, etc. are 0, so it works. But for entries where multiple fields are set simultaneously (e.g., a cash receipt that records both `revenue_amount` and `cash_in`), the voucher `total_amount` will be inflated. Additionally, `cash_out` and `bank_out` are **added** rather than subtracted, so a payment entry (`cash_out=1M`) inflates the total by 1M instead of reducing it.

The `voucher.total_amount` is displayed on the voucher and used in reports. For the current sales/purchase invoice flows this happens to work because only one amount field is populated per entry, but the method is fundamentally wrong and will produce incorrect totals for cash vouchers, mixed entries, or any future code path that sets multiple fields.

**Fix:** Only sum the primary amount for the entry's ledger_type, or define which field is "primary" per ledger type:
```python
def _entry_total(self, entry: DnsnLedgerEntry) -> Decimal:
    # Use the net amount already computed for running balances
    return abs(self._entry_net_amount(entry))
```

---

### HIGH

#### H-1: `discount_amount` and `discount_rate` fields are never populated or applied

**Severity:** High
**File:** `apps/sales/services/invoice_service.py:83-100`, `apps/purchasing/services/invoice_service.py:83-100`

**Description:**
Both `SalesInvoiceLine` and `PurchaseInvoiceLine` models have `discount_rate` and `discount_amount` fields (both defaulting to 0). The invoice models also have `discount_amount` (header level). However, the service `create()` methods **completely ignore** any discount data:

```python
amount_before_vat = quantity * unit_price  # no discount subtraction
vat_amount = (amount_before_vat * vat_rate).quantize(...)
amount = amount_before_vat + vat_amount
```

The `SalesInvoiceLine.objects.create(...)` call does not pass `discount_rate` or `discount_amount` from `line_data`. If a user submits a discount, it is silently ignored, and the invoice total will be wrong. The header-level `invoice.discount_amount` is also never set.

**Impact:** Incorrect invoice totals and VAT amounts when discounts are involved. The model fields exist, implying the feature is expected to work.

**Fix:** Either apply discounts in the calculation:
```python
discount_amount = Decimal(str(line_data.get("discount_amount", 0)))
amount_before_vat = (quantity * unit_price) - discount_amount
```
or remove the unused model fields to avoid confusion. Pass `discount_rate` and `discount_amount` to the line `create()` call.

---

#### H-2: `_next_invoice_no` has a race condition (duplicate invoice numbers)

**Severity:** High
**File:** `apps/einvoice/services/__init__.py:220-228` (`_next_invoice_no`)

**Description:**
```python
@staticmethod
def _next_invoice_no(company, config):
    today = timezone.now()
    count = EInvoice.objects.filter(
        company=company,
        issue_date__year=today.year,
        issue_date__month=today.month,
        status__in=[EInvoice.Status.ISSUED, EInvoice.Status.ADJUSTED],
    ).count()
    return f"{config.serial}{today.strftime('%y%m')}{count + 1:06d}"
```

Two concurrent `publish()` calls can read the same `count` and generate the same invoice number. There is no unique constraint on `EInvoice.invoice_no` and no `select_for_update` on the count query. The `EInvoice` model has no `unique_together` on `invoice_no`.

**Impact:** Duplicate e-invoice numbers, which violates tax authority requirements (each e-invoice must have a unique sequential number).

**Fix:** Add a unique constraint on `(company, invoice_no)` (or `(company, pattern, serial, invoice_no)`) and use `select_for_update` or a database sequence. Handle `IntegrityError` with a retry loop.

---

#### H-3: E-invoice adjustment creates negative amounts but does NOT reverse ledger entries

**Severity:** High
**File:** `apps/einvoice/services/__init__.py:204-219` (`adjust`)

**Description:**
The `adjust()` method creates a new `EInvoice` with negated amounts:
```python
subtotal=-original.subtotal,
vat_amount=-original.vat_amount,
total_amount=-original.total_amount,
```

However, there is no code to create a corresponding reversal voucher or ledger entry. The original `SalesInvoice`'s posted `AccountingVoucher` or `DnsnVoucher` remains unchanged. The adjustment e-invoice exists in the e-invoice subsystem but has no effect on the general ledger or DNSN ledger.

Similarly, `cancel()` only sets the e-invoice status to `CANCELLED` but does not unpost or reverse the linked `SalesInvoice`'s voucher.

**Impact:** Adjusted or cancelled e-invoices have no ledger impact, causing the ledger to be out of sync with tax authority records. VAT declarations will be incorrect.

**Fix:** When an adjustment e-invoice is issued, create a reversal voucher linked to the original `SalesInvoice` (or call `unpost` on the original invoice and repost with corrected amounts). When an e-invoice is cancelled, unpost the linked sales invoice's voucher.

---

#### H-4: E-invoice VAT rate division by subtotal can produce wrong rate or crash

**Severity:** High
**File:** `apps/einvoice/services/__init__.py:130-131` (`issue_from_sales_invoice`)

**Description:**
```python
avg_vat_rate = (vat / subtotal * Decimal("100")) if subtotal else Decimal("0")
...
vat_rate=avg_vat_rate / Decimal("100"),
```

Two issues:
1. If `subtotal` is zero (zero-amount invoice, credit note, or sample invoice), `avg_vat_rate` is set to `Decimal("0")` but then divided by 100 and stored. This is technically fine (0), but the logic is convoluted.
2. If there are multiple lines with different VAT rates (e.g., 5% and 10%), the average rate stored on the `EInvoice` header is a blended rate that does not match any individual line. This blended rate is displayed on the PDF and submitted to the provider. Vietnamese tax authorities require per-line VAT rates, and a blended header rate can cause rejection or audit flags.

**Impact:** Incorrect VAT rate on e-invoice header for mixed-rate invoices. Potential tax filing errors.

**Fix:** The per-line VAT rates are already in the XML/JSON items. Remove the header-level `vat_rate` field from the e-invoice (or compute it correctly only for single-rate invoices, and set it to `None`/omit for multi-rate invoices). The XML already includes `<VATRate>` per item, so the header rate is redundant and misleading.

---

#### H-5: `amount_in_words` produces incorrect Vietnamese for many numbers

**Severity:** High
**File:** `apps/einvoice/services/__init__.py:44-90` (`amount_in_words`)

**Description:**
The Vietnamese number-to-words function has multiple bugs in `three_digits`:

1. **"mười" vs "mươi"**: When `ch == 1` and `tr` is truthy, it outputs "mười" (correct for 10-19 range). But when `ch == 1` and `tr` is falsy (e.g., the number 15 in the lowest tier), it falls through to `units[ch] + " mươi"` = "một mươi" (wrong, should be "mười").

2. **"năm" handling**: The condition `if dv == 5 and ch:` appends "năm" but does NOT append the unit word. The logic `if dv and dv != 5:` skips 5 entirely when `ch` is truthy, but the "năm" append happens inside the `elif ch:` branch, so when `ch == 0 and tr`, the digit 5 is dropped completely.

3. **"mốt" vs "một"**: The condition for "mốt" is `units[dv] == "một" and ch != 0 and ch != 1`, but this is inside a complex nested conditional that often fails. For example, 21 should be "hai mươi mốt" but the logic may produce "hai mươi một".

4. **Edge cases**: Numbers like 100,000 ("một trăm nghìn") work, but 101 ("một trăm lẻ một") may not produce "lẻ" correctly because the condition is `if ch == 0 and dv != 0` which is inside the `if tr:` block but after "trăm" is already appended.

**Impact:** The `total_in_words` field on e-invoices is legally required and must be accurate. Incorrect words can cause e-invoice rejection by tax authorities or disputes with customers.

**Fix:** Replace with a well-tested Vietnamese number-to-words library (e.g., `vncurrency` or `num2words` with `lang='vi'`), or rewrite the function with comprehensive unit tests covering all edge cases (1-9, 10-19, 21, 25, 100, 101, 110, 115, 1000, 1000000, 1000000000, etc.).

---

#### H-6: N+1 query on `EInvoiceListView` (missing `sales_invoice__customer` prefetch)

**Severity:** High (performance)
**File:** `apps/einvoice/views.py:25-28` (`EInvoiceListView.get_queryset`)

**Description:**
```python
qs = EInvoice.objects.filter(company=company).select_related("sales_invoice")
```

This joins `sales_invoice` but not `sales_invoice__customer` or `sales_invoice__company`. If the list template accesses `einvoice.sales_invoice.customer.name` (common for displaying buyer info), each row triggers a separate query for the customer. With 50 invoices per page, this is 50+ extra queries.

Similarly, the `EInvoiceReportService.generate_bc01` iterates `for e in qs` and accesses `e.buyer_name`, `e.issue_date`, etc. which are denormalized on `EInvoice` (fine), but `qs` is not evaluated lazily with `iterator()` for large datasets, loading all invoices into memory.

**Fix:**
```python
qs = (
    EInvoice.objects
    .filter(company=company)
    .select_related("sales_invoice", "sales_invoice__customer", "company")
)
```

---

#### H-7: `total_fc` computation uses `or 0` which converts `Decimal("0")` to `int`

**Severity:** High (type safety)
**File:** `apps/ledger/services/voucher_posting_service.py:101-103`

**Description:**
```python
voucher.total_fc = sum(
    (line.debit_fc or 0 for line in voucher.lines.all()),
    Decimal("0"),
)
```

When `line.debit_fc` is `Decimal("0")` (the default), `Decimal("0") or 0` evaluates to `int(0)` because `Decimal("0")` is falsy. The `sum()` then adds `Decimal("0") + int(0)` which works due to Decimal's mixed-type arithmetic, but produces `Decimal("0")` with no scale. More importantly, if all `debit_fc` values are 0, `total_fc` ends up as `Decimal("0")` with no decimal places, which may cause display or serialization issues.

The same pattern (`debit_vnd or Decimal("0")`) in `_validate_balanced` is fine because it uses `Decimal("0")` as the fallback, but `total_fc` uses bare `0`.

**Impact:** Minor type inconsistency, but in strict mypy mode this would be flagged, and it sets a bad precedent.

**Fix:**
```python
voucher.total_fc = sum(
    (line.debit_fc for line in voucher.lines.all()),
    Decimal("0"),
)
```
Since `debit_fc` has `default=0`, it is never `None`, so the `or` guard is unnecessary.

---

### MEDIUM

#### M-1: `EInvoice.cancel()` does not validate status before cancelling

**Severity:** Medium
**File:** `apps/einvoice/services/__init__.py:186-191` (`cancel`)

**Description:**
```python
@classmethod
def cancel(cls, einvoice, reason, cancelled_by=None):
    einvoice.status = EInvoice.Status.CANCELLED
    einvoice.error_message = reason
    einvoice.note = f"Hủy: {reason}"
    einvoice.save()
```

There is no check that the invoice is in `ISSUED` status before cancelling. A `DRAFT` invoice can be "cancelled" (should just be deleted). An already-`CANCELLED` or `ADJUSTED` invoice can be cancelled again. Per ND 254/2026, only issued invoices that have been transmitted to the tax authority can be cancelled, and only within the allowed timeframe.

**Fix:** Add a status guard:
```python
if einvoice.status != EInvoice.Status.ISSUED:
    raise EInvoiceIssueError(
        f"Chỉ có thể hủy hóa đơn đã phát hành (hiện tại: {einvoice.get_status_display()})"
    )
```

---

#### M-2: `EInvoice.adjust()` does not set sales_invoice link consistency

**Severity:** Medium
**File:** `apps/einvoice/services/__init__.py:194-219` (`adjust`)

**Description:**
The adjustment invoice copies `original.sales_invoice` but does not create any linking on the `SalesInvoice` side. If the adjustment should modify the original sales invoice's amounts or status, there is no mechanism to do so. The `EInvoice` model has `replaces_invoice` and `adjustment_type`, but there is no validation that `original.status == ISSUED` before creating an adjustment.

**Fix:** Add status validation on `original` and optionally create a linked reversal/adjustment voucher on the sales invoice side (see H-3).

---

#### M-3: Foreign currency not converted to VND in voucher lines

**Severity:** Medium
**File:** `apps/sales/services/invoice_service.py:138-179` (`_post_standard`), `apps/purchasing/services/invoice_service.py:130-170`

**Description:**
When `currency_code != "VND"` and `exchange_rate != 1`, the voucher lines are posted with `debit_vnd`/`credit_vnd` set directly from `invoice.total_amount` (which is in foreign currency). There is no multiplication by `exchange_rate` to convert FC to VND:

```python
VoucherLine.objects.create(
    ...
    debit_vnd=invoice.total_amount,  # This is FC amount, not VND!
    ...
)
```

The `voucher.total_vnd` is also set to `invoice.total_amount` directly. The `VoucherLine` model has `debit_fc` and `credit_fc` fields but they are never populated by the service.

**Impact:** For foreign currency invoices, the VND amounts in the ledger are wrong (they contain the FC amount instead of the VND equivalent). Balance sheets and VAT reports will be incorrect.

**Fix:**
```python
vnd_amount = invoice.total_amount * invoice.exchange_rate
VoucherLine.objects.create(
    ...
    debit_vnd=vnd_amount,
    debit_fc=invoice.total_amount,
    ...
)
voucher.total_vnd = vnd_amount
voucher.total_fc = invoice.total_amount
```

---

#### M-4: No validation for negative quantity or unit price on invoice lines

**Severity:** Medium
**File:** `apps/sales/services/invoice_service.py:74-80`, `apps/purchasing/services/invoice_service.py:74-80`

**Description:**
The service accepts any `quantity` and `unit_price` values from `data["lines"]` without validation:
```python
quantity = Decimal(str(line_data["quantity"]))
unit_price = Decimal(str(line_data["unit_price"]))
amount_before_vat = quantity * unit_price
```

Negative quantities or prices will produce negative amounts, which flow into voucher lines and ledger entries. While credit notes legitimately need negative amounts, the service does not distinguish between a data entry error (negative quantity) and an intentional credit note. There is no validation that `quantity > 0` or `unit_price >= 0`.

**Impact:** Accidental negative entries corrupt ledger balances.

**Fix:** Add validation in the service:
```python
if quantity <= 0:
    raise ValueError(f"Số lượng phải lớn hơn 0 (line {idx})")
if unit_price < 0:
    raise ValueError(f"Đơn giá không được âm (line {idx})")
```
For credit notes, use a separate service method or a `credit_note` flag.

---

#### M-5: Voucher balance tolerance allows 1 VND discrepancy per voucher

**Severity:** Medium
**File:** `apps/ledger/services/voucher_posting_service.py:21` (`BALANCE_TOLERANCE`)

**Description:**
```python
BALANCE_TOLERANCE = Decimal("0.01")  # 1 VND rounding tolerance
```

The tolerance is 0.01 VND, but VAT amounts are quantized to 0.0001 (0.1 xu). Over many vouchers, these sub-VND rounding differences accumulate in `AccountPeriodBalance` without any rounding adjustment entry. The tolerance allows posting unbalanced vouchers (debit != credit by up to 0.01), which over time causes the trial balance to not foot.

More importantly, the tolerance check uses `abs(total_debit - total_credit) > tolerance`, which means a difference of exactly 0.01 is allowed. For a financial system, even 1 VND discrepancies should trigger a warning or auto-rounding to a rounding account (TK 811 or similar).

**Fix:** Either tighten the tolerance to `Decimal("0.0001")` to match the VAT quantization, or add an automatic rounding line to a designated rounding account when the difference is within tolerance.

---

#### M-6: `_recompute_running_balances_for_codes` is O(n) per account code, causing lock contention

**Severity:** Medium (performance)
**File:** `apps/ledger/services/voucher_posting_service.py:152-197`

**Description:**
Every voucher post/unpost triggers `_recompute_running_balances_for_codes`, which loads ALL posted `VoucherLine` rows for the affected account codes (across ALL fiscal years and periods) and updates each one individually:

```python
for pk, rbd, rbc in updates:
    VoucherLine.objects.filter(pk=pk).update(
        running_balance_debit=rbd,
        running_balance_credit=rbc,
    )
```

For a company with 10,000+ voucher lines on account 131 or 5111, each post/unpost of any voucher touching those accounts updates thousands of rows. This causes significant database load and lock contention, especially under concurrent posting.

**Impact:** Performance degradation as data grows. Posting a single invoice can take seconds or minutes.

**Fix:** Consider computing running balances on-demand (in SQL with window functions) rather than materializing them. Alternatively, only recompute running balances for lines with `voucher_date >= posted_voucher.voucher_date` (lines before the posted voucher are unaffected).

---

### LOW

#### L-1: `_entry_total` in DnsnPostingService includes `vat_amount` and `tndn_amount` inconsistently

**Severity:** Low
**File:** `apps/ledger/services/dnsn_posting_service.py:138-148`

**Description:**
The `_entry_total` method sums `revenue_amount`, `cost_amount`, `cash_in`, `cash_out`, `bank_in`, `bank_out`, and `total_amount`, but does NOT include `vat_amount`, `tndn_amount`, `vat_input`, `vat_output`, or `vat_payable`. This means the voucher total understates the true transaction value for VAT/tax entries. For the S3b (VAT) ledger, the voucher total will be 0 even though there is VAT activity.

**Fix:** Include VAT and TNDN amounts in the total, or document that `voucher.total_amount` only represents cash/revenue/cost flows.

---

#### L-2: `EInvoiceReportService.generate_bc01` loads all invoices into memory

**Severity:** Low (performance)
**File:** `apps/einvoice/services/__init__.py:283-300`

**Description:**
```python
qs = EInvoice.objects.filter(...)
batch = EInvoiceReportBatch.objects.create(
    ...
    invoice_count=qs.count(),
    total_amount=sum((e.total_amount for e in qs), Decimal("0")),
    ...
)
```

The `sum((e.total_amount for e in qs), ...)` iterates the entire queryset, loading all EInvoice objects into memory. Then the XML generation iterates `qs` again. For a company with thousands of invoices per month, this is memory-intensive.

**Fix:** Use `qs.aggregate(total=Sum("total_amount"))["total"]` for the sum, and use `qs.iterator()` or `.values_list(...)` for the XML generation to avoid loading full ORM objects.

---

#### L-3: Sales invoice `vat_account` hardcoded to "33311" regardless of company regime

**Severity:** Low
**File:** `apps/sales/services/invoice_service.py:102`

**Description:**
```python
vat_account="33311",
```
The VAT account is hardcoded. While 33311 is correct for standard TT133/TT200, some companies may use sub-accounts (e.g., 333113, 333115) or different account structures. The product master could carry a `gl_account_vat_output` field for flexibility.

**Also:** `apps/purchasing/services/invoice_service.py:102` hardcodes `vat_account="1331"`.

**Fix:** Consider making the VAT account configurable via `Product` or `Company` settings, or at minimum document the assumption.

---

#### L-4: Test gap: no tests for e-invoice adjustment/cancel ledger reversal

**Severity:** Low (test gap)
**File:** `tests/` (missing)

**Description:**
There are no tests covering:
1. E-invoice adjustment (`EInvoiceService.adjust`) and its ledger impact (because there is none, see H-3).
2. E-invoice cancellation (`EInvoiceService.cancel`) and its ledger impact.
3. Foreign currency invoice posting (M-3 scenario).
4. Zero-amount or negative-amount invoices.
5. Discount handling in invoice creation (H-1).
6. `amount_in_words` accuracy (H-5).
7. XML injection prevention (C-3).

The existing tests (`test_sales_invoice.py`, `test_purchase_invoice.py`, `test_tt58_sales_purchasing_integration.py`, `test_einvoice_02banhang.py`) cover the happy path well, but miss edge cases and error paths.

**Fix:** Add tests for each of the above scenarios, especially the ledger reversal on e-invoice cancellation/adjustment and foreign currency conversion.

---

## Architecture Notes

### What works well

1. **Tax method branching**: The `is_tt58` / `is_vat_percentage` property pattern cleanly separates TT58 DNSN posting from standard TT133/TT200 posting. The `tax_method_group` property on `Company` correctly computes groups 1-4.

2. **VAT posting for khau_tru vs ty_le_phan_tram**: The logic is correct:
   - `khau_tru`: Revenue excludes VAT (posted to revenue account/ledger), VAT posted separately to 33311 / S3b. Input VAT credited to 1331 / S3b.
   - `ty_le_phan_tram`: Revenue includes VAT (no separate VAT posting). No input VAT deduction.

3. **E-invoice form selection**: `01GTKT` for `khau_tru`, `02BANHANG` for `ty_le_phan_tram` is correct per ND 254/2026.

4. **Transaction safety**: Both `SalesInvoiceService.create` and `PurchaseInvoiceService.create` use `@transaction.atomic`, and the posting services also use `@transaction.atomic`. The invoice -> voucher -> balance chain is atomic within a single service call.

5. **Unpost/reversal for standard vouchers**: `VoucherPostingService.unpost` correctly reverses balance updates by applying `sign=-1` and recomputes running balances. `DnsnPostingService.unpost` deletes entries and recalculates balances from remaining entries.

6. **E-invoice IDOR guards**: Most e-invoice views (publish, cancel, XML/JSON download) correctly scope by `current_company`. (See C-2 for the exception.)

### Key risk areas

1. **Multi-tenant isolation is inconsistent**: Some views filter by company, others don't. There should be a middleware or mixin that enforces company scoping on all querysets.

2. **E-invoice -> Ledger integration is incomplete**: Adjustments and cancellations in the e-invoice subsystem do not flow back to the ledger (H-3).

3. **XML generation is unsafe**: All XML is built via f-string interpolation (C-3).

4. **Discount handling is a dead feature**: Model fields exist but services ignore them (H-1).

---

## Recommendations (Priority Order)

1. **Fix C-1, C-2**: Add company scoping to all sales/purchase/e-invoice views immediately. This is a data security issue.
2. **Fix C-3**: Escape all XML content or switch to a proper XML builder.
3. **Fix C-4**: Correct `_entry_total` to avoid double-counting.
4. **Fix H-3**: Implement ledger reversal for e-invoice cancellation/adjustment.
5. **Fix H-1**: Implement discount calculation or remove dead fields.
6. **Fix H-2**: Add unique constraint and locking for invoice number generation.
7. **Fix M-3**: Implement foreign currency conversion in voucher posting.
8. **Fix H-5**: Replace `amount_in_words` with a tested library.
9. **Add tests** for all edge cases (L-4).
