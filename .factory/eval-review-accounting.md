# Accounting Core Review - Visota ERP

Scope: `apps/ledger/` (models, services, admin), `apps/reporting/` (models, services), TT58 DNSN layer.

Review date: 2026-07-16
Reviewer: Worker Droid (automated)

Legend: [C]ritical, [H]igh, [M]edium, [L]ow

---

## 1. Bugs & Logic Errors

### [H] B-01: VoucherPostingService.post() is NOT idempotent - double-counts balances on re-post
**File:** `apps/ledger/services/voucher_posting_service.py:38-44`
**Description:** `post()` checks `voucher.is_locked` but never checks `voucher.is_posted` (status >= LEDGER). If `post()` is called on a voucher that is already in LEDGER status, `_update_balances(sign=+1)` runs again, doubling every `AccountPeriodBalance.period_debit` / `period_credit`. The existing test `test_post_already_posted_is_idempotent` only calls `post()` once and thus does NOT catch this; calling it a second time would assert 2000 instead of 1000.
**Fix:** Add an early-return guard at the top of `post()`:
```python
if voucher.is_posted:
    return  # idempotent - already posted
```

### [H] B-02: DnsnPostingService.post() is NOT idempotent - creates duplicate ledger entries on re-post
**File:** `apps/ledger/services/dnsn_posting_service.py:39-44`
**Description:** `post()` creates new `DnsnLedgerEntry` rows via `_create_entry` without first checking whether the voucher is already posted. If called twice on the same voucher, duplicate entries are created and `total_amount` is doubled. Unlike `unpost()` which has `if not voucher.is_posted: return`, `post()` has no such guard.
**Fix:** Add at the top of `post()`:
```python
if voucher.is_posted:
    return  # idempotent
```
Alternatively, delete existing entries before re-creating them.

### [H] B-03: Cash-flow direct method `_aggregate_cash_with_offset` leaks cross-company data
**File:** `apps/reporting/services/formula_parser.py:194-218`
**Description:** `_aggregate_cash_with_offset` does NOT filter by `self.company`. Both the `offset_voucher_ids` subquery and the `cash_lines` aggregation query scan ALL companies' posted voucher lines for the given fiscal_year/period. In a multi-tenant deployment this mixes cash flows from different companies, producing incorrect B03-DN reports and exposing one tenant's data in another tenant's report.
**Fix:** Add company filtering to both queries:
```python
offset_voucher_ids = set(
    VoucherLine.objects.filter(
        voucher__company=self.company,   # <-- add
        voucher__fiscal_year=self.fiscal_year,
        ...
    )
)
cash_lines = VoucherLine.objects.filter(
    voucher__company=self.company,   # <-- add
    voucher_id__in=offset_voucher_ids,
).filter(_expand_pattern(cash_pattern))
```

### [H] B-04: `_compute_opening_cash` ignores prior fiscal years - opening cash is wrong for period 1
**File:** `apps/reporting/services/cash_flow.py:118-127`
**Description:** `_compute_opening_cash` filters on `voucher__fiscal_year=fiscal_year, voucher__period__lt=period`. For period 1 this produces an empty queryset, so `opening_cash` is always 0 regardless of the prior year's closing cash balance. The closing cash on the B03-DN therefore does not roll forward across fiscal year boundaries.
**Fix:** Either aggregate from `AccountPeriodBalance` closing balances for all periods before the target (including prior years), or change the filter to `Q(voucher__fiscal_year__lt=fiscal_year) | Q(voucher__fiscal_year=fiscal_year, voucher__period__lt=period)`.

### [M] B-05: ReportEngine `_eval_cong_thuc` has wrong operator precedence for `*` and `/`
**File:** `apps/reporting/services/formula_parser.py:257-269`
**Description:** `_eval_cong_thuc` evaluates tokens strictly left-to-right, giving `+`, `-`, `*`, `/` the same precedence. A formula like `100+200*3` evaluates as `(100+200)*3 = 900` instead of `100+600 = 700`. The VAT return service (`vat_return.py:_eval_formula`) handles this correctly with a multiplicative fold, but the financial-report engine does not.
**Fix:** Port the two-pass additive/multiplicative fold from `VATReturnService._eval_formula` into `_eval_cong_thuc`, or restrict `FinancialReportLine.cong_thuc` to additive-only formulas and document the constraint.

### [M] B-06: ReportEngine `_compute_line_value` returns `debit - credit` regardless of account nature
**File:** `apps/reporting/services/formula_parser.py:298-305`
**Description:** When both `tk_no_pattern` and `tk_co_pattern` yield non-zero amounts, the method always returns `debit - credit`. For revenue/equity/liability accounts (credit-nature), the correct net is `credit - debit`. A B02-DN line configured with `tk_no_pattern=632*` and `tk_co_pattern=511*` would compute `debit_632 - credit_511` (negative revenue minus positive COGS) rather than the intended `credit_511 - debit_632`.
**Fix:** Add a `nature` or `sign` field to `FinancialReportLine` so each line can declare whether it should return `debit - credit` or `credit - debit`. Alternatively, document that `tk_no_pattern` and `tk_co_pattern` should never both be set on the same line (use separate lines instead).

### [M] B-07: DNSN `_entry_total` double-counts for S2c entries that set both `total_amount` and `revenue_amount`
**File:** `apps/ledger/services/dnsn_posting_service.py:138-145`
**Description:** `_entry_total` sums `revenue_amount + cost_amount + cash_in + cash_out + bank_in + bank_out + total_amount`. For an inventory entry (S2c) that populates `total_amount` AND also has a non-zero `revenue_amount` or `cost_amount` (e.g. from a generic form submission), the voucher's `total_amount` double-counts. This inflates the displayed voucher total.
**Fix:** Make `_entry_total` respect ledger-type semantics, or only sum the primary amount field for each entry based on its `ledger_type`.

### [M] B-08: DNSN `_recalculate_balance` double-counts S2c revenue
**File:** `apps/ledger/services/dnsn_posting_service.py:178-181`
**Description:** For S2c entries, the method first adds `entry.revenue_amount` to `period_revenue`, then adds `entry.total_amount` again:
```python
balance.period_revenue += entry.revenue_amount
if ledger_type == "s2c":
    balance.period_revenue += entry.total_amount
```
If an S2c entry has both `revenue_amount` and `total_amount` set (even if revenue_amount is 0 by convention), this is fragile. If revenue_amount is ever non-zero for S2c, it double-counts the inventory value in `period_revenue`.
**Fix:** Use an exclusive branch: for S2c, add only `total_amount` (not `revenue_amount`).

### [M] B-09: B02-DNSN reads TNDN tax from S4c `closing_vat`, but S4c holds "other taxes" (33334/33338), not TNDN
**File:** `apps/reporting/services/dnsn_report_service.py:151`
**Description:** In `generate_b02_dnsn`, `tndn_tax = self._get_balance_value(balances, "s4c", "closing_vat")`. But per `balance_conversion_service.py`, S4c is populated from TK 33334/33338 ("thuế khác" - other taxes), not from TK 33341 (TNDN). The TNDN expense (TK 821) and TNDN payable (TK 33341) are never mapped to any DNSN ledger in the conversion service. This means B02-DNSN's "Thuế thu nhập doanh nghiệp" line shows "other taxes" instead of TNDN, and the net profit calculation is wrong.
**Fix:** Either create a dedicated ledger or field for TNDN, or map TK 33341/821 to S4c separately from TK 33334/33338. Clarify the semantic of S4c `closing_vat` vs a new `closing_tndn` field.

### [M] B-10: B01-DNSN `retained_earnings` reads S4d `closing_revenue`, but nothing ever populates it
**File:** `apps/reporting/services/dnsn_report_service.py:113`
**Description:** `retained_earnings = self._get_balance_value(balances, "s4d", "closing_revenue")`. In `balance_conversion_service.py`, S4d only receives `opening_cash` (from TK 411/4118). No conversion path populates `opening_revenue` for S4d. So after conversion, retained earnings is always 0. Additionally, there is no DNSN period-close mechanism that transfers profit to S4d `closing_revenue`, so even after posting entries, retained earnings stays 0.
**Fix:** Either (a) add a conversion mapping for TK 4212 (undistributed profits) to S4d `opening_revenue`, or (b) add a DNSN period-close service that computes net profit and updates S4d.

### [L] B-11: PeriodClosingService uses `date(fiscal_year, period, 28)` which is incorrect for Feb and invalid for period > 12
**File:** `apps/ledger/services/period_closing_service.py:79`
**Description:** `voucher_date=date(fiscal_year, period, 28)`. For period 2 in a non-leap year, this is Feb 28 (fine). For period 2 in a leap year, Feb 28 is not the last day (Feb 29 is). More importantly, if period > 12 (e.g. adjustment period 13), `date(year, 13, 28)` raises `ValueError`.
**Fix:** Use `calendar.monthrange(fiscal_year, period)[1]` to get the last day of the month, and validate that `period` is 1-12 (or handle 13+ explicitly).

### [L] B-12: `invoice_group_filter` / `tax_code_filter` in VATReportLine used as FK IDs but stored as strings
**File:** `apps/reporting/services/vat_return.py:155-157`
**Description:** The config stores `invoice_group_filter` and `tax_code_filter` as CharFields (e.g. "4", "5", "10"), but the service applies them as `invoice_group_code_id=cfg.invoice_group_filter` and `tax_code_id=cfg.tax_code_filter`. This only works if the string happens to be a valid integer PK. If the config stores a code that is not the PK (e.g. a slug), the filter silently matches nothing, producing 0 for that line.
**Fix:** Either resolve the code to a PK via a lookup, or change the config fields to IntegerField / FK.

---

## 2. Race Conditions

### [H] R-01: VoucherPostingService `_update_one_balance` read-modify-write without `select_for_update`
**File:** `apps/ledger/services/voucher_posting_service.py:111-148`
**Description:** `_update_one_balance` does `get_or_create`, then reads `balance.period_debit`, adds a delta in Python, and calls `balance.save()`. This is a classic lost-update pattern: two concurrent postings to the same `(company, fiscal_year, period, account_code)` can read the same baseline, both add their delta, and the second save overwrites the first. The `@transaction.atomic` wrapper provides atomicity but NOT isolation against this pattern at the default isolation level (REPEATABLE READ on MariaDB does not prevent this without an explicit row lock).
**Fix:** Use `select_for_update` inside the transaction:
```python
balance, _ = AccountPeriodBalance.objects.select_for_update().get_or_create(...)
```
Alternatively, use `F()` expressions: `AccountPeriodBalance.objects.filter(pk=balance.pk).update(period_debit=F("period_debit") + delta)`.

### [H] R-02: No lock on period during closing - postings can occur while PeriodClosingService runs
**File:** `apps/ledger/services/period_closing_service.py:30-55`
**Description:** `close_period` reads balances and creates a closing voucher, but does NOT prevent concurrent voucher postings to the same period. A voucher posted after the balance snapshot but before the closing voucher is posted would either (a) be excluded from the close, or (b) cause the closing voucher to be unbalanced. There is no "period locked" flag or advisory lock.
**Fix:** Add a `Period` model (or a status field on a period table) that is set to "closing" / "closed" atomically. `VoucherPostingService.post()` should check that the period is open before posting. At minimum, acquire a PostgreSQL/MariaDB advisory lock keyed on `(company_id, fiscal_year, period)` at the start of `close_period`.

### [M] R-03: DnsnPostingService `_recalculate_balance` has the same read-modify-write pattern
**File:** `apps/ledger/services/dnsn_posting_service.py:165-205`
**Description:** `_recalculate_balance` does `get_or_create`, resets period accumulators, loops over all entries summing in Python, then saves. Two concurrent posts to the same `(company, fiscal_year, period, ledger_type)` can interleave and produce incorrect balances.
**Fix:** Use `select_for_update` on the balance row, or serialize posting per company via an advisory lock.

---

## 3. N+1 Queries

### [M] N-01: VoucherPostingService fetches `voucher.lines.all()` three times in `post()`
**File:** `apps/ledger/services/voucher_posting_service.py:90-108`
**Description:** During a single `post()` call, `voucher.lines.all()` is evaluated in:
1. `_validate_balanced` (line 94) - iterates all lines for debit/credit sum.
2. `_validate_balanced` (line 103) - iterates again for `total_fc` sum.
3. `_update_balances` -> `_update_one_balance` (line 109) - iterates per line.
This results in 3+ queries for the same lines. For vouchers with many lines, this is wasteful.
**Fix:** Cache the lines list once: `lines = list(voucher.lines.all())` at the top of `post()` and pass it down.

### [M] N-02: Running-balance recompute uses per-row UPDATE instead of bulk_update
**File:** `apps/ledger/services/voucher_posting_service.py:194-199`
**Description:** `_recompute_running_balances_for_codes` collects all updates in a list, then issues one `UPDATE` query per line:
```python
for pk, rbd, rbc in updates:
    VoucherLine.objects.filter(pk=pk).update(...)
```
For an account code with 10,000 posted lines, this is 10,000 individual UPDATE queries.
**Fix:** Use `VoucherLine.objects.bulk_update(lines, ["running_balance_debit", "running_balance_credit"])` with batch_size, or use a window-function-based raw SQL `UPDATE ... SET running_balance = SUM(...) OVER (...)`.

### [M] N-03: DNSN running-balance recompute uses per-entry `save()` instead of bulk_update
**File:** `apps/ledger/services/dnsn_posting_service.py:239-242`
**Description:** Same pattern as N-02. Each entry gets `entry.save(update_fields=["running_balance"])` in a loop.
**Fix:** Use `bulk_update`.

### [L] N-04: PeriodClosingService iterates balances without `.iterator()` or prefetch
**File:** `apps/ledger/services/period_closing_service.py:42-48`
**Description:** `balances = AccountPeriodBalance.objects.filter(...)` loads all balance rows into memory at once. For a company with many accounts, this could be large. The iteration only reads `account_code`, `period_debit`, `period_credit`, so it's not an N+1, but it's memory-heavy.
**Fix:** Use `.only("account_code", "period_debit", "period_credit").iterator()` if memory is a concern.

---

## 4. Transaction Boundaries

### [M] T-01: Notification side-effect inside `@transaction.atomic` in VoucherPostingService.post()
**File:** `apps/ledger/services/voucher_posting_service.py:55-68`
**Description:** `NotificationService.send_to_superusers(...)` is called inside the `@transaction.atomic` wrapper. If the notification service does any DB writes (e.g. creating notification records), those writes are part of the same transaction and will be rolled back if a later error occurs. Conversely, if the notification service does external I/O (e.g. email, websocket), it fires before the transaction commits, so a rollback would leave users notified about a posting that never happened.
**Fix:** Move the notification to `transaction.on_commit(lambda: ...)` so it only fires after the posting is successfully committed.

### [L] T-02: BalanceConversionService.convert resets ALL opening fields per ledger type, even those not being converted
**File:** `apps/ledger/services/balance_conversion_service.py:200-205`
**Description:** For each `ledger_type_involved`, the service sets all four opening fields (`opening_cash`, `opening_revenue`, `opening_cost`, `opening_vat`) to 0, then re-applies only the aggregated amounts. This means if a `DnsnLedgerBalance` row was previously created for S4a with both `opening_cash` (receivables) and `opening_cost` (payables), and a re-conversion only finds receivable accounts, the payables (`opening_cost`) is zeroed out. This is documented as "idempotent" but is actually destructive for multi-field ledger types when the source data changes.
**Fix:** Only reset the specific `opening_field` that is about to be re-applied, not all four.

---

## 5. Permission / Multi-Tenant Gaps

### [H] P-01: DNSN API `_get_company` falls back to `Company.objects.first()` - cross-tenant data leak
**File:** `apps/ledger/dnsn_api.py:19-23`
**Description:** `_get_company` returns `Company.objects.first()` when `request.current_company` is not set (e.g. middleware not configured, or a misconfigured request). This means any authenticated user could read/create/update/delete DNSN vouchers for the first company in the database, regardless of their actual company assignment.
**Fix:** Raise a 403/401 if `request.current_company` is None instead of silently falling back. At minimum, filter by `request.user.company` or enforce the company in middleware.

### [M] P-02: VoucherLine has no direct `company` field - company filtering relies on voucher FK joins
**File:** `apps/ledger/models/voucher.py:120-185`
**Description:** `VoucherLine` inherits from `models.Model` (not `CompanyOwnedModel`) and has no `company` field. All multi-tenant filtering must go through `voucher__company=...`. While this works, it means any query that forgets the join leaks across tenants. The admin (`VoucherLineAdmin`) has no company filter on `list_filter`, and the `list_display` doesn't show the company, making it easy to accidentally expose cross-tenant data in the admin.
**Fix:** Add `company` as a denormalized FK on `VoucherLine` (set in `save()` or via signal from the parent voucher), and add `company` to the admin's `list_filter`.

### [M] P-03: BalanceSheetService legacy path does not filter by company in the initial queryset
**File:** `apps/reporting/services/balance_sheet.py:123-126`
**Description:** In `_generate_legacy`, the initial `balances` queryset filters only by `fiscal_year` and `period`. The company filter is applied AFTER (`if self.company is not None: balances = balances.filter(company=self.company)`). If `self.company` is None (which is valid per the type hint `Company | None`), ALL companies' balances are aggregated together, producing a consolidated report that mixes tenants.
**Fix:** If the service is intended for single-company use only, make `company` required (non-optional). If None means "all companies," document that explicitly and ensure the caller intentionally passes None for consolidation.

---

## 6. Decimal Handling

### [L] D-01: `line.debit_fc or 0` returns `int 0` instead of `Decimal("0")` when debit_fc is falsy
**File:** `apps/ledger/services/voucher_posting_service.py:104`
**Description:** `voucher.total_fc = sum((line.debit_fc or 0 for line in voucher.lines.all()), Decimal("0"))`. When `line.debit_fc` is `Decimal("0")` (falsy), the expression yields `int 0` instead of `Decimal("0")`. While `sum(..., Decimal("0"))` coerces the result back to Decimal, the intermediate `int 0` is inconsistent. More importantly, `line.debit_fc or 0` would also mask `None` values - but the field has `default=0` so None should not occur.
**Fix:** Use `line.debit_fc or Decimal("0")` for consistency.

### [L] D-02: `max(b.closing_debit or 0, b.closing_credit or 0)` in balance_sheet legacy path mixes int and Decimal
**File:** `apps/reporting/services/balance_sheet.py:137`
**Description:** `closing = max(b.closing_debit or 0, b.closing_credit or 0)`. When the Decimal value is 0 (falsy), `or 0` produces `int 0`. `max(Decimal("0"), int 0)` works in Python but is type-inconsistent. No precision loss here, but it's a code smell.
**Fix:** Use `max(b.closing_debit, b.closing_credit)` (both default to Decimal("0") from the model).

---

## 7. Test Gaps

### [H] TG-01: No test for double-posting (calling `post()` twice on the same voucher)
**File:** `tests/test_voucher_posting_service.py`
**Description:** The existing `test_post_already_posted_is_idempotent` creates a voucher with `status=LEDGER` and calls `post()` once. It does NOT call `post()` twice on the same voucher. Since `post()` lacks an `is_posted` guard (see B-01), a second call would double-count balances, but no test verifies this.
**Fix:** Add a test that creates a DRAFT voucher, calls `post()` twice, and asserts balances are NOT doubled.

### [H] TG-02: No test for concurrent posting race condition
**Description:** There are no tests using `select_for_update`, threading, or transaction isolation to verify that concurrent postings to the same account produce correct balances. See R-01.
**Fix:** Add a test using `threading.Thread` or `transaction.atomic` with `select_for_update` to verify concurrent safety.

### [M] TG-03: No test for multi-tenant isolation in reporting services
**Description:** The reporting services (`BalanceSheetService`, `CashFlowService`, `VATReturnService`) accept `company=None` and some have legacy paths that aggregate across all companies when company is None. No test verifies that company A's report does not include company B's data.
**Fix:** Add a test with two companies, each with posted vouchers, and assert that reports only include the requested company's data.

### [M] TG-04: No test for PeriodClosingService double-close prevention
**Description:** `close_period` has an idempotency check (`existing = ... .filter(source="closing").exists()`), but there's no test that verifies calling `close_period` twice for the same period does not create duplicate closing vouchers or double-count the revenue/expense transfer.
**Fix:** Add a test that calls `close_period` twice and asserts only one closing voucher exists.

### [M] TG-05: No test for the `_aggregate_cash_with_offset` company filter (B-03)
**Description:** The cash-flow direct method's offset aggregation lacks a company filter (B-03), and there's no test that catches this.
**Fix:** Add a test with two companies' voucher lines matching the offset pattern and assert only the queried company's cash lines are summed.

---

## 8. Dead Code / Design Observations

### [L] DC-01: `DnsnLedgerEntry.tndn_amount` field is stored but never used in balance calculation or reports
**File:** `apps/ledger/models/dnsn.py:111`
**Description:** The `tndn_amount` field exists on `DnsnLedgerEntry`, is populated by `DnsnPostingService._create_entry`, but is never aggregated into `DnsnLedgerBalance` by `_recalculate_balance`, nor read by `DnsnReportService`. B02-DNSN reads TNDN from S4c `closing_vat` (see B-09) instead of from `tndn_amount`. This field appears to be dead data.
**Fix:** Either wire `tndn_amount` into the balance calculation and report, or remove it.

### [L] DC-02: `AccountPeriodBalance.reset_period` method does not exist (only on `DnsnLedgerBalance`)
**File:** `apps/ledger/models/balance.py`
**Description:** `AccountPeriodBalance` has `recalculate_closing()` but no `reset_period()`. This is fine (not dead code), but worth noting that the TT133 balance model lacks a reset helper that the DNSN model has. No action needed.

### [L] DC-03: `VoucherLine.is_auto_tax_posting` field has no logic referencing it
**File:** `apps/ledger/models/voucher.py:183-185`
**Description:** The field `is_auto_tax_posting` is defined with a help_text referencing auto-creation by `VoucherPostingService` for TK 1331/33311, but `VoucherPostingService` does not create any auto-tax lines. No code reads or filters on this field.
**Fix:** Either implement the auto-tax-posting feature or remove the field.

### [L] DC-04: `FinancialReportLine.tinh_giam_tru` field is unused
**File:** `apps/reporting/models.py:79-81`
**Description:** The `tinh_giam_tru` field is defined as "Optional subtraction formula" but `ReportEngine` never reads it. No code references this field.
**Fix:** Implement the subtraction logic in `ReportEngine` or remove the field.

### [L] DC-05: No DNSN period-close service (counterpart to PeriodClosingService for TT133)
**Description:** `PeriodClosingService` handles TT133/TT200 closing (revenue/expense -> 911 -> 421). There is no equivalent service for DNSN. The DNSN balance model has no mechanism to carry forward period-to-period closing balances (see B-10). Opening balances for period N+1 are never set from period N's closing.
**Fix:** Implement `DnsnPeriodClosingService` that carries closing balances forward as the next period's opening balances.

---

## Summary Table

| ID  | Severity | Category | File | Line |
|-----|----------|----------|------|------|
| B-01 | High | Bug | voucher_posting_service.py | 38 |
| B-02 | High | Bug | dnsn_posting_service.py | 39 |
| B-03 | High | Bug / Multi-tenant | formula_parser.py | 194 |
| B-04 | High | Bug | cash_flow.py | 118 |
| B-05 | Medium | Bug | formula_parser.py | 257 |
| B-06 | Medium | Bug | formula_parser.py | 298 |
| B-07 | Medium | Bug | dnsn_posting_service.py | 138 |
| B-08 | Medium | Bug | dnsn_posting_service.py | 178 |
| B-09 | Medium | Bug | dnsn_report_service.py | 151 |
| B-10 | Medium | Bug | dnsn_report_service.py | 113 |
| B-11 | Low | Bug | period_closing_service.py | 79 |
| B-12 | Low | Bug | vat_return.py | 155 |
| R-01 | High | Race condition | voucher_posting_service.py | 111 |
| R-02 | High | Race condition | period_closing_service.py | 30 |
| R-03 | Medium | Race condition | dnsn_posting_service.py | 165 |
| N-01 | Medium | N+1 | voucher_posting_service.py | 90 |
| N-02 | Medium | N+1 | voucher_posting_service.py | 194 |
| N-03 | Medium | N+1 | dnsn_posting_service.py | 239 |
| N-04 | Low | N+1 | period_closing_service.py | 42 |
| T-01 | Medium | Transaction | voucher_posting_service.py | 55 |
| T-02 | Low | Transaction | balance_conversion_service.py | 200 |
| P-01 | High | Permission | dnsn_api.py | 19 |
| P-02 | Medium | Permission | voucher.py (model) | 120 |
| P-03 | Medium | Permission | balance_sheet.py | 123 |
| D-01 | Low | Decimal | voucher_posting_service.py | 104 |
| D-02 | Low | Decimal | balance_sheet.py | 137 |
| TG-01 | High | Test gap | test_voucher_posting_service.py | - |
| TG-02 | High | Test gap | - | - |
| TG-03 | Medium | Test gap | - | - |
| TG-04 | Medium | Test gap | - | - |
| TG-05 | Medium | Test gap | - | - |
| DC-01 | Low | Dead code | dnsn.py | 111 |
| DC-03 | Low | Dead code | voucher.py | 183 |
| DC-04 | Low | Dead code | reporting/models.py | 79 |
| DC-05 | Low | Design gap | - | - |

**Totals:** 6 High, 13 Medium, 12 Low.
