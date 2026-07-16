# Review: Remaining Modules (Inventory, Assets, CRM, Contracts, Bidding, Banking, Budget, Costing, Approvals, FX, Recurring, Input Docs, Projects, Loans, Guarantees, Documents, Notifications)

Scope: apps/{inventory, assets, crm, contracts, bidding, banking, budget, costing, approvals, fx, recurring, input_docs, projects, loans, guarantees, documents, notifications}/

Severity legend: **CRITICAL** (data corruption / legal violation) > **HIGH** (functional bug or data integrity risk) > **MEDIUM** (correctness/quality concern) > **LOW** (polish/dead code).

Findings are grouped by module then by theme. Each finding has: severity, file:line, description, fix recommendation.

---

## 1. Inventory (`apps/inventory/`)

### 1.1 MEDIUM — stock_dashboard_service.py: N+1 query loop in get_summary
- **File:** `apps/inventory/services/stock_dashboard_service.py:22-37`
- **Description:** `get_summary()` iterates over every active `Product` with `min_stock>0` *for each warehouse* and runs a separate `StockLedger.objects.filter(...).aggregate(...)` query per product. With N warehouses × M products this is O(N*M) queries. Same problem in `get_low_stock_products()` at line 47 (one aggregate query per product).
- **Fix:** Replace the inner loop with a single `StockLedger.objects.filter(company=company, warehouse=wh, product__in=products).values("product").annotate(total=Sum("quantity"))` query and build a dict.

### 1.2 MEDIUM — stock_dashboard_service.py:119-123 — Transfer qty silently dropped in stock card
- **File:** `apps/inventory/services/stock_dashboard_service.py:119-123`
- **Description:** `get_stock_card()` treats `voucher_type == "transfer"` as `qty_signed = 0`, so transfers never appear on the stock card even though they move quantity in/out of a warehouse. The stock ledger is updated correctly (via `StockService.create_transfer`) but the historical card is wrong for any product that was transferred.
- **Fix:** For transfers, sign the quantity +/− based on whether `voucher.warehouse` matches the requested `warehouse_id` (out of from-wh = negative, into to-wh = positive).

### 1.3 HIGH — stock_service.py: StockVoucher.status default is opaque integer `2`
- **File:** `apps/inventory/models.py:55` (`status = models.PositiveSmallIntegerField(default=2)`)
- **Description:** `StockVoucher.status` has no `choices`, no documentation of what `2` means, and no `TextChoices` enum. Compare with `StockAdjustment.status` (line 89) which correctly uses a CharField with draft/posted choices. This is inconsistent and error-prone — no code path can interpret the status safely.
- **Fix:** Convert to a `TextChoices` enum (e.g., DRAFT=1, POSTED=2) with `choices=` on the field, matching the pattern used elsewhere in the codebase. Add a migration.

### 1.4 LOW — StockAlert has no `company` FK (multi-tenant leak risk)
- **File:** `apps/inventory/models.py:174-201`
- **Description:** `StockAlert` does not inherit from `CompanyOwnedModel` and has no `company` FK. All other inventory models are company-scoped. While alerts are derived from `Product`/`Warehouse` (which are company-scoped), the lack of a `company` column means list views cannot filter by company efficiently and the model violates the multi-tenant pattern.
- **Fix:** Add `company` FK (or inherit `CompanyOwnedModel`) and update the migration + any views that list alerts.

### 1.5 LOW — StockVoucherLine/StockAdjustmentLine/StockLedger do not inherit CompanyOwnedModel
- **File:** `apps/inventory/models.py:79, 137, 110`
- **Description:** These line/ledger models define their own `company` FK (or none) rather than inheriting `CompanyOwnedModel`. `StockVoucherLine` has no `company` column at all — it relies on `voucher.company`. This is acceptable for lines but inconsistent with the rest of the codebase. Low severity since the patterns are internally consistent within this app.
- **Fix:** Optional — inherit `CompanyOwnedModel` for `StockLedger` (it already has its own `company` FK) for consistency. Leave lines as-is.

---

## 2. Assets (`apps/assets/`)

### 2.1 CRITICAL — depreciation_service.py: voucher_type "depreciation" used but voucher is never posted via VoucherPostingService correctly; also single expense/depreciation account pair is wrong
- **File:** `apps/assets/services/depreciation_service.py:93-130`
- **Description:** Two bugs:
  1. The voucher is created with `voucher_type="depreciation"`, then `VoucherPostingService().post(voucher)` is called immediately (line 127). However the voucher was created with `status=Status.DRAFT` (line 112) and the post call happens *before* `AssetDepreciation` rows are created (lines 132-139). If posting fails, no history rows are written but the voucher may be partially posted.
  2. More importantly, the comment at line 84-86 admits "for simplicity, assume all assets in this period share one expense/depr account pair" and uses `asset_lines[0][0].expense_account` / `.depreciation_account` for **all** assets. If assets have different expense accounts (e.g., 641 vs 642 vs 635) or different depreciation accounts (2141 for TSCĐ vs 142/242 for CCDC), the GL posting is **wrong** — all depreciation is booked to the first asset's accounts.
- **Fix:** Group `asset_lines` by `(expense_account, depreciation_account)` and create one voucher line pair per group. This is the correct TT133/TT200 accounting treatment.

### 2.2 HIGH — asset_lifecycle_service.py: voucher_type="journal" for disposal, but the depreciation account used is `asset.depreciation_account` which may be empty for non-depreciated assets
- **File:** `apps/assets/services/asset_lifecycle_service.py:30-72`
- **Description:** The disposal service creates a journal voucher but **never calls `VoucherPostingService().post(voucher)`**. Wait — re-reading line 68: `VoucherPostingService().post(voucher)` IS called. However, the voucher's `fiscal_year` and `period` fields are **not set** (they are not nullable in the model — `fiscal_year = models.SmallIntegerField()` with no null=True). This will raise an `IntegrityError` on `voucher.save()` at line 33 because `fiscal_year` and `period` are required.
- **Fix:** Set `fiscal_year=date.today().year` and `period=date.today().month` when creating the `AccountingVoucher` in `dispose()`.

### 2.3 MEDIUM — FixedAsset.calculate_monthly_depreciation only implements straight-line
- **File:** `apps/assets/models/asset.py:97-103`
- **Description:** `DECLINING_BALANCE` and `UNITS_OF_PRODUCTION` are offered as choices but `calculate_monthly_depreciation()` returns `Decimal("0")` for them (line 99-100, comment "Other methods not implemented in Phase 3"). An asset configured with declining-balance method will silently never depreciate.
- **Fix:** Either implement the methods or raise `NotImplementedError` / add a validation constraint preventing selection of unimplemented methods. At minimum, add a `clean()` check.

### 2.4 LOW — AssetTransaction.new_asset BooleanField is never used
- **File:** `apps/assets/models/asset.py:152`
- **Description:** `new_asset = models.BooleanField(default=False)` is defined for "increase" transactions but no service code ever sets it to `True` or reads it. It is dead schema.
- **Fix:** Remove the field, or implement the "increase asset" transaction flow that uses it.

---

## 3. CRM (`apps/crm/`)

### 3.1 HIGH — CRMLead has no unique_together on `code`
- **File:** `apps/crm/models.py:35` (`code = models.CharField(max_length=50, blank=True, default="")`)
- **Description:** `CRMLead` has no `unique_together` constraint in its Meta (line 38 only sets `db_table` and `ordering`). Meanwhile `CRMAccount`, `Opportunity`, `Ticket`, `Campaign` all have `unique_together=[("company", "code")]`. This means two leads in the same company can have the same code, leading to duplicate records and reporting confusion. Additionally, `code` defaults to blank string, so all leads without an explicit code collide on `""` — but since there is no unique constraint, this doesn't error, it just creates data hygiene problems.
- **Fix:** Add `unique_together = [("company", "code")]` to `CRMLead.Meta` (with a migration that first populates any existing blank codes). Alternatively, make `code` `null=True` with `UniqueConstraint` with a `condition=Q(code__gt="")`.

### 3.2 MEDIUM — Opportunity uses BigIntegerField instead of ForeignKey for created_contract_id / created_project_id / created_invoice_id
- **File:** `apps/crm/models.py:155-157`
- **Description:** `created_contract_id`, `created_project_id`, `created_invoice_id` are `BigIntegerField` instead of proper `ForeignKey`. This means no referential integrity: if the contract/project/invoice is deleted, the opportunity still references a now-nonexistent ID. The `OpportunityConverter` (in `apps/crm/services/opportunity_converter.py:55-57`) sets these IDs but they are never queried via ORM join.
- **Fix:** Convert to `ForeignKey("contracts.Contract", null=True, blank=True, on_delete=models.SET_NULL)` etc. This enables `.created_contract` access and prevents orphan references.

### 3.3 MEDIUM — opportunity_converter.py: Invoice number collision risk
- **File:** `apps/crm/services/opportunity_converter.py:103`
- **Description:** `_create_invoice()` creates a `SalesInvoice` with `invoice_no=f"HĐ{opportunity.code}"`. If the opportunity code collides with an existing invoice number (or if the opportunity is converted twice after being re-opened), this will fail on the unique constraint. There is no try/except or idempotency guard.
- **Fix:** Use `get_or_create` on `invoice_no` or append a timestamp/sequence suffix.

### 3.4 LOW — CRMContact.account is nullable but no clean() validation
- **File:** `apps/crm/models.py:91-92`
- **Description:** `CRMContact.account` allows `null=True, blank=True`, meaning a contact can float without an organization. This may be intentional (freelance contacts) but there is no validation or UI guard. Low severity.
- **Fix:** Document the intent or add `clean()` validation if contacts must belong to an account.

---

## 4. Contracts (`apps/contracts/`)

### 4.5 MEDIUM — ContractTemplate.contract_type is free-form CharField, not linked to Contract.ContractType choices
- **File:** `apps/contracts/models.py:62-65`
- **Description:** `ContractTemplate.contract_type` is a plain CharField with no choices, but the comment lists values like "labor_fixed, labor_indefinite, ...". Meanwhile `Contract.ContractType` uses different values (sale, purchase, service, construction, etc.). There is no validation that a template's `contract_type` matches any valid `Contract.ContractType`, and the values don't align (template has "labor_fixed" but Contract has "labor"). This makes it impossible to reliably match templates to contracts by type.
- **Fix:** Either add a `TextChoices` enum to `ContractTemplate.contract_type` that mirrors `Contract.ContractType`, or use a FK to a shared type lookup table.

### 4.2 LOW — ContractTemplate has no company FK (global templates)
- **File:** `apps/contracts/models.py:58`
- **Description:** `ContractTemplate` does not inherit `CompanyOwnedModel` and has no `company` field. This may be intentional (system-wide templates) but it breaks the multi-tenant isolation pattern. Any company can see/edit all templates.
- **Fix:** If templates are meant to be global, document this clearly. If per-company, add `company` FK.

### 4.3 LOW — Minutes model has no line items / amount
- **File:** `apps/contracts/models.py:113-145`
- **Description:** `Minutes` (biên bản) has no amount or line-item detail. For acceptance/liquidation minutes (nghiệm thu/thanh lý) this is usually required to post a voucher with the acceptance value. The `linked_voucher` FK exists but there's no service to auto-generate the voucher from the minutes.
- **Fix:** Add optional `amount` field and a service to generate acceptance vouchers. Low severity since this may be a future feature.

### 4.4 PASS — Bidding Law 22/2023/QH15 references correct
- **File:** `apps/contracts/models.py:31-33`
- **Description:** `Contract.ContractType` includes `BIDDING_LUMP_SUM`, `BIDDING_UNIT_PRICE`, `BIDDING_CONSULTING` with comment "--- Bidding Law 22/2023/QH15 ---". The law number is correct. No "23/2023" references found in apps/contracts/.

---

## 5. Bidding (`apps/bidding/`)

### 5.1 CRITICAL — models.py:93 — bid_type default has a leading space bug
- **File:** `apps/bidding/models.py:93`
- **Description:** `bid_type = models.CharField(max_length=30, default=" construction")` — note the leading space in `" construction"`. This means every new `BidOpportunity` gets `bid_type=" construction"` (with a leading space). The `BidConverterService.convert_to_contract()` (line 33 of services.py) checks `if "construction" in (bid_opportunity.bid_type or "")` — this will match due to `in` substring semantics, but any exact-equality comparison or filter (`bid_type="construction"`) will fail. This is a data corruption seed.
- **Fix:** Change default to `"construction"` (no leading space). Add a data migration to strip leading spaces from existing rows.

### 5.2 HIGH — BidOpportunity.status is free-form CharField with no choices
- **File:** `apps/bidding/models.py:81-83`
- **Description:** `status = models.CharField(max_length=20, default="identified")` with no `choices=` parameter. The comment lists values "identified, decided_to_bid, preparing, submitted, won, lost, cancelled" but these are not enforced. The list view (`views.py:21`) filters by `status` from request GET params with no validation, so any string can be used. This leads to typo-induced data fragmentation (e.g., "won " vs "won" vs "WON").
- **Fix:** Define a `Status(TextChoices)` enum and add `choices=Status.choices` to the field.

### 5.3 MEDIUM — bidding/views.py: BidConvertToContractView swallows all exceptions
- **File:** `apps/bidding/views.py:62-66`
- **Description:** The convert-to-contract view wraps the entire conversion in a bare `try/except Exception as e` and shows the error as a Django message. This hides real bugs (e.g., IntegrityError from duplicate contract_no) from the user and from logs. No logging is performed.
- **Fix:** Catch specific expected exceptions (e.g., `Contract IntegrityError`) and let unexpected ones propagate to the 500 handler. Add `logger.exception()`.

### 5.4 MEDIUM — BidConverterService.convert_to_contract: contract_overrides pops contract_no AFTER get_or_create
- **File:** `apps/bidding/services.py:46-52`
- **Description:** Line 51 does `contract_no = contract_overrides.pop("contract_no", ...)` AFTER line 46-50 already builds `defaults` from `contract_overrides`. This means `contract_no` is still in `contract_overrides` when `defaults` is built, so it gets passed into `defaults` dict. Then `Contract.objects.get_or_create(contract_no=..., defaults=defaults)` passes `contract_no` in defaults too, which Django ignores — but it's confusing and fragile. The pop should happen before building defaults.
- **Fix:** Move `contract_no = contract_overrides.pop(...)` to the top of the method, before building `defaults`.

### 5.5 LOW — bidding/ has empty management/commands/ directory
- **File:** `apps/bidding/management/commands/` (only `__init__.py`)
- **Description:** No management commands. May be intentional (no seeding needed) but the directory structure suggests planned commands. Not a bug.
- **Fix:** None required.

### 5.6 PASS — Bidding Law 22/2023/QH15 references correct
- **File:** `apps/bidding/models.py:1`, `apps/bidding/apps.py:2`
- **Description:** Both files cite "22/2023/QH15" correctly. The `test_legal_compliance.py` tests enforce this. No "23/2023" references found in apps/bidding/.

---

## 6. Banking (`apps/banking/`)

### 6.1 HIGH — views.py: BankStatementUploadView duplicates CSV parsing logic
- **File:** `apps/banking/views.py:55-90`
- **Description:** `BankStatementUploadView.post()` re-implements CSV parsing inline (lines 65-85) instead of calling `BankReconciliationService.parse_csv()`. The two implementations can drift. The view also catches all `Exception` per row (line 78) and silently skips bad rows with no logging, making it impossible to diagnose import failures.
- **Fix:** Call `BankReconciliationService.parse_csv(imp, imp.file)` instead of inline parsing. Add logging for skipped rows.

### 6.2 HIGH — services/__init__.py: auto_reconcile N+1 query and weak matching logic
- **File:** `apps/banking/services/__init__.py:64-105`
- **Description:** `auto_reconcile()` iterates over every unreconciled transaction and for each one runs a separate `VoucherLine.objects.filter(...)` query (line 80-86). With N unreconciled transactions this is N queries. The matching logic is also crude: it matches purely on exact amount + date window (±3 days) on bank accounts, with no fuzzy matching, no reference number matching, and no counterparty matching. The `lines[:5]` cap (line 90) means if the first 5 candidates are already matched, the transaction stays unreconciled even if the 6th line would match.
- **Fix:** Batch the query: fetch all candidate voucher lines for the date range once, then match in memory. Improve matching to consider reference and counterparty. Remove or increase the `[:5]` cap.

### 6.3 MEDIUM — views.py: VietQRModalView._load_invoice has no company filter on SalesInvoice customer
- **File:** `apps/banking/views.py:186-193`
- **Description:** `_load_invoice()` for "sales" type accesses `si.customer.code` (line 192). If `si.customer_id` is null (which is allowed since `customer` FK is likely nullable), this will raise `AttributeError`. There's a guard `if si.customer_id else ""` for the code, but if the model's `customer` relationship is broken (orphaned ID), accessing `.code` will raise `DoesNotExist`.
- **Fix:** Use `si.customer.code if si.customer else ""` (which catches both None and orphaned FK via Django's behavior). Verify this is the case.

### 6.4 MEDIUM — ReconciliationMatch uses txn.amount as object_amount (misleading)
- **File:** `apps/banking/services/__init__.py:96-99`
- **Description:** `ReconciliationMatch.object_amount=txn.amount` stores the transaction amount, not the matched voucher line's amount. The field name `object_amount` suggests it's the amount of the matched object (voucher), not the bank transaction. If the two differ (partial payment, fee deduction), the stored value is misleading.
- **Fix:** Rename to `matched_amount` or store the actual voucher line amount separately.

### 6.5 LOW — BankAccount has no unique constraint on `code` per company
- **File:** `apps/banking/models.py:15-16`
- **Description:** `BankAccount` has `unique_together=[("company", "account_number")]` (line 23) which is correct, but `code` (line 15) has no uniqueness constraint. Two bank accounts in the same company can share a code. Low severity since `account_number` is the primary identifier.
- **Fix:** Add `unique_together=[("company", "code")]` if code is meant to be user-facing.

---

## 7. Budget (`apps/budget/`)

### 7.1 HIGH — services.py: range_map uses incorrect prefixes, double-counting and omissions
- **File:** `apps/budget/services.py:19-30`
- **Description:** `BudgetVarianceService.refresh_actuals()` maps `account_group` to account code prefixes, but the mapping is wrong:
  - `"opex": ("641", "64")` — prefix `"641"` matches accounts 6410-6419 (selling expenses) but NOT 642 (admin expenses). The comment says "641-642" but prefix `"641"` only captures 641x.
  - `"marketing": ("6411", "6411")` — this is a subset of "opex" (6411), so the same voucher lines are counted in both groups, double-counting expenses.
  - `"salaries": ("6221", "62")` — prefix `"6221"` only matches 6221x, not 6222 (other labor) or 6223.
  - The second element of each tuple (`"51"`, `"63"`, `"64"`, etc.) is unpacked into `_` and never used (line 22: `prefix, _ = range_map.get(...)`).
  This means budget vs actual variance analysis is incorrect for most groups.
- **Fix:** Use correct prefixes or full account lists. For "opex", use `("641", "642")` and query with `account_code__startswith` in an OR filter, or use a list of explicit account codes. Eliminate the overlap with "marketing".

### 7.2 MEDIUM — services.py: CashFlowService.generate_for_period loads ALL voucher lines into memory
- **File:** `apps/budget/services.py:79-115`
- **Description:** `generate_for_period()` calls `ar_qs = VoucherLine.objects.filter(...)` then `sum(((l.debit_vnd or 0) - (l.credit_vnd or 0) for l in ar_qs), Decimal("0"))` — this iterates every matching voucher line in Python. With thousands of AR lines, this is both slow (no SQL aggregation) and memory-heavy. Same pattern for AP (line 91), payroll (line 102), tax (line 109), and cash (line 115).
- **Fix:** Use `.aggregate(total=Sum(F("debit_vnd") - F("credit_vnd")))` at the database level.

### 7.3 MEDIUM — services.py: CashFlowService uses arbitrary 60%/70% collection heuristics
- **File:** `apps/budget/services.py:87, 98`
- **Description:** `expected_ar = ar_total * Decimal("0.6")` and `expected_ap = ap_total * Decimal("0.7")` — these hardcoded percentages are presented as "rough heuristics" but produce cash flow projections that look authoritative. No documentation, no configurability, no basis for the numbers.
- **Fix:** Make the percentages configurable (per-company setting or constants with clear documentation). Consider basing projections on actual AR/AP aging instead.

### 7.4 LOW — views.py: Decimal imported at bottom of file
- **File:** `apps/budget/views.py:91`
- **Description:** `from decimal import Decimal` appears at the very bottom of the file (line 91) with comment "avoid import error at top of file". It's used in `BudgetDetailView.get_context_data` (line 47). While Python allows late imports, this is unusual and the "avoid import error" comment suggests a past circular import that was worked around rather than fixed.
- **Fix:** Move the import to the top of the file. If there was a circular import, resolve it properly.

---

## 8. Costing (`apps/costing/`)

### 8.1 MEDIUM — costing app has no models.py, no migrations with content
- **File:** `apps/costing/` (only `apps.py`, `services/__init__.py`)
- **Description:** The costing app has no models — it's a pure service app. `CostingService` (in `services/__init__.py`) computes cost summaries from voucher lines and creates closing entries. This is a reasonable design (costing is derived, not stored). However, there's no `CostSummary` persistence — results are ephemeral dataclass instances. If the closing voucher is created but the CostSummary is lost, there's no audit trail of the cost calculation.
- **Fix:** Consider persisting CostSummary to a `CostingRun` model for auditability. Low priority if the closing voucher captures enough detail.

### 8.2 MEDIUM — services/__init__.py: create_closing_entry only does N154/C621,622,623 — no N632/C154
- **File:** `apps/costing/services/__init__.py:113-171`
- **Description:** The docstring (line 9-10) says the flow should be "N154/C621,622,623 then N632/C154" (accumulate into WIP, then transfer WIP to COGS). But `create_closing_entry()` only does the first half (N154/C621,622,623). The N632/C154 entry (transfer from WIP to cost of goods sold) is never created. This means WIP (TK 154) accumulates indefinitely and COGS (TK 632) is understated. The module-level docstring even says "Kết chuyển: N154/C621,622,623 then N632/C154" but the code stops at step 1.
- **Fix:** Add the second closing entry: `VoucherLine(account_code="632", debit_vnd=summary.total_production_cost)` and `VoucherLine(account_code="154", credit_vnd=summary.total_production_cost)`. This may need to be a separate voucher or the same voucher depending on accounting policy.

### 8.3 LOW — services/__init__.py: _sum_debit/_sum_credit use startswith on account codes
- **File:** `apps/costing/services/__init__.py:174-179`
- **Description:** `_sum_debit(qs, "621")` filters with `account_code__startswith="621"`. This matches 6210-6219 (correct) but also matches any hypothetical "621XYZ" codes. For Vietnamese COA this is fine (accounts are 3-5 digits) but it's fragile.
- **Fix:** Acceptable for Vietnamese accounting. Document the assumption.

---

## 9. Approvals (`apps/approvals/`)

### 9.1 MEDIUM — models.py: ApprovalRequest has no unique constraint preventing duplicate pending requests per object
- **File:** `apps/approvals/models.py:48-83`
- **Description:** `ApprovalRequest` has no `unique_together` on `(content_type, object_id, status)`. While `ApprovalService.submit()` (line 64-67) cancels prior pending requests before creating a new one, this is application-level logic — a race condition or a direct DB insert can create duplicate pending requests for the same object. There is also no constraint that prevents two concurrent approval requests for different voucher types on the same object.
- **Fix:** Add a `UniqueConstraint` with `condition=Q(status="pending")` on `(content_type, object_id)`. This enforces at the DB level that only one pending request can exist per object.

### 9.2 MEDIUM — services.py: _fire_approval_hook swallows all exceptions
- **File:** `apps/approvals/services.py:177-187`
- **Description:** `_fire_approval_hook()` calls `VoucherPostingService().post(obj)` inside a bare `try/except Exception: pass`. If posting fails (e.g., voucher not balanced), the approval is marked as approved but the voucher is never posted, and no one is notified. The exception is silently swallowed.
- **Fix:** Log the exception and notify the submitter that auto-posting failed. Consider making this a non-silent failure.

### 9.3 LOW — context_processors.py exists but not reviewed (out of scope for data integrity)
- **File:** `apps/approvals/context_processors.py`
- **Description:** Not reviewed in depth — context processors are UI-layer and outside the scope of this data-integrity review.
- **Fix:** N/A.

### 9.4 PASS — Approval workflow integrates correctly with notifications + ledger posting
- **Description:** The approval chain (submit → approve step-by-step → fire hook → post voucher) is well-structured. The role-based assignment via `UserCompanyRole` is correct. The `pending_for_user` query is efficient (single query on `ApprovalStep` then filter on `ApprovalRequest`).

---

## 10. FX (`apps/fx/`)

### 10.1 CRITICAL — services.py: run_revaluation gain/loss calculation is fundamentally broken
- **File:** `apps/fx/services.py:104-153`
- **Description:** `run_revaluation()` computes `vnd_book = fc_amount` (line 120, comment says "simplified — normally would be a different number"). This is wrong: `fc_amount` is the foreign currency balance (e.g., 1000 USD), while `vnd_book` should be the VND book value (the sum of original VND amounts at historical rates). By setting `vnd_book = fc_amount`, the code computes `diff = fc_amount * rate - fc_amount = fc_amount * (rate - 1)`, which is nonsensical (it treats the FC amount as if it were VND). For 1000 USD at rate 24500, this gives `1000 * 24500 - 1000 = 24,499,000`, which is clearly wrong — the gain/loss should be the difference between current VND book value and `1000 * 24500`.
- **Fix:** Track the VND book value separately (sum of original `debit_vnd - credit_vnd` for lines where `currency_code != VND`). The current `balances` dict already has `debit_vnd - credit_vnd` as the value (line 84: `balance = (line.debit_vnd or 0) - (line.credit_vnd or 0)`) — but this IS the VND book value, not the FC amount. The variable is mislabeled as `fc_amount` when it's actually `vnd_book`. The entire gain/loss computation needs to be rewritten to: (a) compute FC balance, (b) compute VND book balance, (c) compute VND-at-closing = FC * rate, (d) diff = VND-at-closing - VND-book.

### 10.2 HIGH — services.py: compute_fcl_balances aggregates VND amounts, not FC amounts
- **File:** `apps/fx/services.py:70-89`
- **Description:** `compute_fcl_balances()` iterates voucher lines and sums `(debit_vnd - credit_vnd)` grouped by account and currency. But the variable `balance` (line 84) is the VND amount, not the foreign currency amount. The function is named "fcl_balances" (foreign currency ledger balances) but returns VND balances keyed by currency label. This makes the subsequent gain/loss calculation (see 10.1) incorrect.
- **Fix:** Sum `debit_fc - credit_fc` (or whatever the FC amount field is on `VoucherLine`) for the FC balance, and separately sum `debit_vnd - credit_vnd` for the VND book balance.

### 10.3 MEDIUM — services.py: voucher_type="journal" but no balance check
- **File:** `apps/fx/services.py:109-117`
- **Description:** The revaluation voucher is created with `status=Status.DRAFT` but is never explicitly posted via `VoucherPostingService`. Instead, the batch status is set to `POSTED` (line 152) purely as a metadata flag. The voucher remains in DRAFT status. This means the revaluation entries never hit `AccountPeriodBalance` unless someone manually posts the voucher.
- **Fix:** Call `VoucherPostingService().post(voucher)` after creating all lines, or document that revaluation vouchers must be manually posted.

---

## 11. Recurring (`apps/recurring/`)

### 11.1 MEDIUM — services/recurring_service.py: run_one catches all exceptions silently
- **File:** `apps/recurring/services/recurring_service.py:56-62`
- **Description:** `run_one()` catches `Exception` (line 59, `# noqa: BLE001`) and stores the error in `last_run_result`, but never logs it or sends a notification. If a recurring template (e.g., depreciation, payroll, period closing) fails, it fails silently — the only trace is in the `last_run_result` JSON field on the template. For mission-critical operations like period closing, this is dangerous.
- **Fix:** Add `logger.exception()` and send a notification to admins on failure.

### 11.2 LOW — runners.py: run_payroll may fail if PayrollService signature changes
- **File:** `apps/recurring/runners.py:22-29`
- **Description:** `run_payroll` imports `PayrollService` lazily and calls `svc.calculate(period=...)`. If the `PayrollService.calculate` signature changes, the runner fails at runtime (not at import time). This is a fragile coupling.
- **Fix:** Add integration tests for each runner. Consider a type check or contract test.

### 11.3 PASS — RecurringService scheduling logic is correct
- **Description:** `_compute_next_run()` correctly handles monthly, quarterly, and yearly schedules with the 28-day clamp (avoiding Feb 30 issues). The `run_all_due()` method correctly filters by `next_run_at <= now`. The `setup_defaults()` method creates sensible default templates.

---

## 12. Input Docs (`apps/input_docs/`)

### 12.1 MEDIUM — invoice_extraction_service.py: _to_decimal number parsing is locale-ambiguous
- **File:** `apps/input_docs/services/invoice_extraction_service.py:18-43`
- **Description:** `_to_decimal()` tries to handle Vietnamese number formats but has an ambiguous case: a single dot (line 36-38, "Single dot — ambiguous, leave as decimal"). For Vietnamese invoices, "1.234" is almost always a thousand separator (1,234), not a decimal. But the function leaves "1.234" as `Decimal("1.234")` (one point two three four). This will cause amount misparses on any invoice with values ≥ 1000 that use dot as thousand sep without a decimal comma.
- **Fix:** For Vietnamese context, treat a single dot with 3 digits after it as a thousand separator. Add a locale parameter or default to vi-VN rules.

### 12.2 MEDIUM — invoice_extraction_service.py: auto_create_purchase_invoice auto-posts without approval
- **File:** `apps/input_docs/services/invoice_extraction_service.py:138-175`
- **Description:** `auto_create_purchase_invoice()` creates a `PurchaseInvoice` with `"post": True` (line 170), which auto-posts to GL. There is no human review step between extraction and posting. If OCR/extraction misreads the amount or vendor, a wrong entry hits the ledger immediately.
- **Fix:** Change to `"post": False` by default and require manual review, or integrate with the approvals workflow for amounts above a threshold.

### 12.3 PASS — XML and text extraction regex patterns are comprehensive
- **Description:** The regex patterns for MST, invoice number, date, amounts, and VAT rate cover the common Vietnamese invoice formats. The XML parser handles the TCT e-invoice schema correctly.

---

## 13. Projects (`apps/projects/`)

### 13.1 HIGH — ProjectTransaction uses BigIntegerField for all source document references (no FK integrity)
- **File:** `apps/projects/models.py:203-207`
- **Description:** `sales_invoice_id`, `purchase_invoice_id`, `voucher_id`, `payroll_line_id` are all `BigIntegerField` instead of `ForeignKey`. This is the same pattern as CRM Opportunity (finding 3.2). If any source document is deleted, the project transaction still holds a dangling ID. There is no way to join from project to the source document via ORM.
- **Fix:** Convert to `ForeignKey` with `on_delete=models.SET_NULL, null=True`. This enables `.sales_invoice` traversal and prevents orphaned references.

### 13.2 MEDIUM — ProjectService.calculate_progress uses "in_progress" string literal
- **File:** `apps/projects/services/project_service.py:13-24`
- **Description:** `calculate_progress()` checks `p.status == "completed"` (line 19) and `p.status == "in_progress"` (line 22) using hardcoded strings instead of `ProjectPhase.Status.COMPLETED` enum values. If the enum values change, this silently breaks.
- **Fix:** Use `ProjectPhase.Status.COMPLETED` and `ProjectPhase.Status.IN_PROGRESS`.

### 13.3 LOW — Project has no link to ProjectTransaction auto-creation service
- **File:** `apps/projects/models.py:185-214`
- **Description:** `ProjectTransaction` docstring says "Auto-created from invoices, payroll, stock movements" but no service code auto-creates these transactions. They must be manually inserted. The `ProjectService.get_cost_summary()` (services/project_service.py:28-46) reads them but nothing populates them.
- **Fix:** Implement auto-creation hooks (e.g., signal on SalesInvoice/PurchaseInvoice creation that creates a ProjectTransaction if the invoice has a project link).

---

## 14. Loans (`apps/loans/`)

### 14.1 HIGH — BankLoan.outstanding_principal property causes N+1 query
- **File:** `apps/loans/models.py:62-65`
- **Description:** `outstanding_principal` property iterates `self.disbursements.all()` and `self.repayments.all()` in Python, triggering two queries every time the property is accessed. In `BankLoanListView` (views.py:16), this property is likely accessed per-row in the template, causing 2N queries for N loans.
- **Fix:** Use `.annotate()` with `Sum("disbursements__amount")` and `Sum("repayments__principal")` in the queryset, or cache the value on the model.

### 14.2 MEDIUM — No service layer for loan disbursement/repayment/interest accrual
- **File:** `apps/loans/` (only models.py, views.py, urls.py)
- **Description:** `LoanDisbursement`, `LoanRepayment`, and `LoanInterestAccrual` models have `gl_voucher` FKs but there is no service that creates the GL vouchers when a disbursement/repayment/accrual is recorded. The models are dumb data containers. The docstring at the top of models.py describes the accounting entries ("N112 / C343" etc.) but no code implements them.
- **Fix:** Create a `LoanService` with `disburse()`, `repay()`, and `accrue_interest()` methods that create both the child record and the GL voucher, similar to `AssetLifecycleService.dispose()`.

### 14.3 MEDIUM — loans/management/commands/ is empty
- **File:** `apps/loans/management/commands/` (only `__init__.py`)
- **Description:** No management command for monthly interest accrual, despite `LoanInterestAccrual` being designed for periodic calculation. A cron/scheduled task would need this.
- **Fix:** Add a `accrue_loan_interest` management command.

### 14.4 LOW — Loan list view has no detail view
- **File:** `apps/loans/urls.py:5` (only `path("", ..., name="list")`)
- **Description:** There is no loan detail view, no disbursement/repayment creation views. Users can only see a list. This is a stub UI.
- **Fix:** Add detail, disbursement, repayment views if this module is meant to be usable.

---

## 15. Guarantees (`apps/guarantees/`)

### 15.1 HIGH — No service layer for guarantee issuance/release GL posting
- **File:** `apps/guarantees/` (only models.py, views.py, urls.py)
- **Description:** The model docstring (line 4) says "Auto-creates voucher N244 / C112 on issue + reversal on release" but there is **no service code** to create these vouchers. `BankGuarantee` has `gl_voucher` and `release_voucher` FKs but nothing populates them. This is a model-only stub — the GL integration described in the docstring is not implemented.
- **Fix:** Create a `GuaranteeService` with `issue()` and `release()` methods that create the GL vouchers (N244/C112 on issue, reversal on release).

### 15.2 MEDIUM — Guarantee list view has no detail/create/release views
- **File:** `apps/guarantees/urls.py:5` (only `path("", ..., name="list")`)
- **Description:** Same as loans — only a list view exists. Users cannot create, view details, or release a guarantee through the UI. This is a read-only stub.
- **Fix:** Add create, detail, and release views.

### 15.3 LOW — days_to_expiry property has no timezone awareness
- **File:** `apps/guarantees/models.py:71-74`
- **Description:** `days_to_expiry` uses `date_cls.today()` which is server-local time. For companies operating across timezones, this may be off by one day near midnight. Low severity.
- **Fix:** Use the company's timezone if defined.

---

## 16. Documents (`apps/documents/`)

### 16.1 MEDIUM — VoucherDocument and Attachment overlap in functionality
- **File:** `apps/documents/models/attachment.py` and `apps/documents/models/voucher_document.py`
- **Description:** `Attachment` is a generic content_type-linked file model. `VoucherDocument` is a voucher-specific document model. Both serve similar purposes (linking files to entities). `Attachment` can link to any object (including vouchers) via content_type, making `VoucherDocument` partially redundant. Having both creates confusion about which to use.
- **Fix:** Document when to use each (e.g., `VoucherDocument` for formal voucher print/scan workflow with status tracking; `Attachment` for ad-hoc file uploads). Consider consolidating if the distinction isn't valuable.

### 16.2 LOW — VoucherDocument.save() catches all exceptions on file size
- **File:** `apps/documents/models/voucher_document.py:64-69`
- **Description:** `save()` wraps file size extraction in `try/except Exception: pass`. If the file is missing or unreadable, `file_size` and `file_type` are silently left at defaults. This differs from `Attachment.save()` (line 55-60) which uses `contextlib.suppress(Exception)` — functionally equivalent but stylistically inconsistent.
- **Fix:** Use consistent error handling. Prefer `contextlib.suppress`.

### 16.3 PASS — AttachmentService generic content_type pattern is correct
- **Description:** `AttachmentService.get_for_object()` and `.attach()` correctly use `ContentType` for polymorphic linking. The company resolution logic (explicit param > obj.company_id > obj.company > None) is robust.

---

## 17. Notifications (`apps/notifications/`)

### 17.1 MEDIUM — send_tax_reminders.py: deduplication uses Python hash() which is non-deterministic
- **File:** `apps/notifications/management/commands/send_tax_reminders.py:113, 138`
- **Description:** The dedup key is computed as `hash(dedup_key) % 2147483647` where `hash()` is Python's built-in. **Python's `hash()` is randomized per process for strings** (since Python 3.3, `PYTHONHASHSEED`). This means the same `dedup_key` string produces different hashes on different runs/process restarts, completely defeating the deduplication. The `Notification.related_object_id` field stores this non-deterministic value, so the `.filter(related_object_id=hash(dedup_key) % 2147483647)` check (line 120-123) will rarely match prior runs.
- **Fix:** Use `hashlib.md5(dedup_key.encode()).hexdigest()` (deterministic) or store the dedup key as a string in a dedicated field, or use `related_object_type` + a composite key.

### 17.2 HIGH — services.py: send_to_superusers queries all superusers with no company scoping
- **File:** `apps/notifications/services.py:127-133`
- **Description:** `send_to_superusers()` sends notifications to `User.objects.filter(is_superuser=True, is_active=True)` — all superusers across all companies. In a multi-tenant deployment with multiple companies, this leaks notifications to superusers who may not be associated with the `company` parameter. A superuser at Company A receives notifications about Company B's voucher postings.
- **Fix:** Filter by `UserCompanyRole` for the given company, or document that superusers are global admins who should see all notifications.

### 17.3 MEDIUM — services.py: send_to_role fetches users one-by-one in a loop (N+1)
- **File:** `apps/notifications/services.py:104-119`
- **Description:** `send_to_role()` gets `user_ids` (line 110-112), then for each `uid` does `User.objects.get(id=uid)` (line 115) — one query per user. For a role with N users, this is N queries.
- **Fix:** Fetch all users in one query: `User.objects.filter(id__in=user_ids)`.

### 17.4 LOW — Notification.company is nullable
- **File:** `apps/notifications/models.py:33-37`
- **Description:** `company` FK is `null=True, blank=True`. System-wide notifications (not tied to a company) are allowed, which may be intentional. But the `NotificationListView` (views.py:15) filters only by `user`, not by company, so a user sees notifications from all companies they've ever been associated with. This may be confusing in multi-tenant UIs.
- **Fix:** Consider filtering by current company in the inbox view.

---

## Cross-Module Findings

### X.1 HIGH — Multiple services call VoucherPostingService with incomplete voucher data
- **Files:** `apps/assets/services/asset_lifecycle_service.py:30-33` (missing fiscal_year/period), `apps/fx/services.py:109-117` (created but never posted), `apps/budget/services.py` (no GL interaction)
- **Description:** Several services create `AccountingVoucher` objects but either omit required fields (`fiscal_year`, `period` are non-nullable) or forget to call `.post()`. The `AccountingVoucher` model requires `fiscal_year` and `period` (voucher.py line 32-33) with no default, so any `AccountingVoucher.objects.create(...)` that omits them will raise `IntegrityError` at the DB level. This suggests these code paths are untested.
- **Fix:** Audit all `AccountingVoucher.objects.create()` calls across these modules and ensure `fiscal_year`, `period`, and `voucher_type` are always set. Add integration tests that exercise these paths.

### X.2 MEDIUM — QD48/2006 properly deprecated
- **File:** `apps/core/models.py`
- **Description:** `Company.AccountingRegime.Q48` label is "QĐ48/2006 (cũ — deprecated, khuyến nghị không dùng)" — properly marked as deprecated. Migration `0019_alter_company_accounting_regime_q48_deprecated.py` updates the label. `test_legal_compliance.py::test_q48_accounting_regime_deprecated` enforces this. **PASS.**
- **Note:** QD48 is a choice in the enum but has no implementation (no QD48-specific COA or reports). This is acceptable — it's a migration source, not a target.

### X.3 PASS — Bidding Law 22/2023/QH15 references correct across all modules
- **Files:** `apps/bidding/models.py:1`, `apps/bidding/apps.py:2`, `apps/contracts/models.py:31-33`, `apps/contracts/management/commands/seed_contract_templates.py` (multiple lines), `apps/core/management/commands/seed_legal_references.py`
- **Description:** All references to the Bidding Law cite "22/2023/QH15" correctly. The previous "23/2023" error has been fixed. `test_legal_compliance.py` enforces this with file-content assertions. **PASS.**
- **Note:** `README.md` and `docs/INDEX.md` still say "Luật Đấu thầu 23/2023" (without /QH15 suffix). This is technically the common shorthand but inconsistent with the codebase's corrected references. Low severity — docs only.

### X.4 PASS — Test coverage exists for every in-scope module
- **Description:** Every module in scope has at least one test file in `tests/`:
  - inventory: `test_stock_voucher.py`, `test_enhanced_modules.py`
  - assets: `test_asset_model.py`, `test_asset_category.py`, `test_asset_views.py`, `test_depreciation_service.py`, `test_enhanced_modules.py`
  - crm: `test_crm.py`
  - contracts: `test_contracts.py`, `test_contract_views.py`, `test_contract_templates.py`
  - bidding: `test_bidding.py`, `test_pit_history_bidding.py`
  - banking: `test_banking.py`, `test_vietqr.py`
  - budget: `test_budget.py`
  - costing: `test_costing.py`
  - approvals: `test_approvals.py`
  - fx: `test_fx.py`
  - recurring: `test_recurring.py`, `test_recurring_views.py`
  - input_docs: `test_input_invoice.py`, `test_input_invoice_views.py`
  - projects: `test_projects.py`
  - loans: `test_guarantees_loans.py`
  - guarantees: `test_guarantees_loans.py`
  - documents: `test_documents.py`, `test_attachments.py`, `test_docx_export.py`, `test_print_service.py`
  - notifications: `test_notifications.py`

### X.5 MEDIUM — N+1 query patterns are pervasive across list views
- **Files:** Multiple (`apps/loans/models.py:62`, `apps/banking/services/__init__.py:64`, `apps/inventory/services/stock_dashboard_service.py:22`, `apps/notifications/services.py:115`)
- **Description:** Many list views and properties trigger per-row queries. The common patterns: (a) model properties that iterate `.all()` on related objects, (b) service loops that run one query per iteration, (c) list views that don't `select_related`/`prefetch_related`. See individual findings for specifics.

### X.6 MEDIUM — Cross-module ledger integration is inconsistent
- **Description:** Some modules correctly integrate with the ledger via `VoucherPostingService` (inventory, assets-depreciation, costing). Others create voucher objects but never post them (fx). Others have FK links to `AccountingVoucher` but no service to create the vouchers (loans, guarantees). The maturity spectrum:
  - **Production-ready:** inventory (stock vouchers post to GL), approvals (auto-posts on final approval), recurring (calls real services)
  - **Functional but incomplete:** assets (disposal missing fiscal_year/period), costing (only half the closing entries), fx (computation is wrong)
  - **Stub (models only, no GL integration):** loans, guarantees — models describe GL entries in docstrings but no code implements them

---

## Summary by Module Maturity

| Module | Maturity | Key Issues |
|--------|----------|------------|
| **inventory** | Production-ready | N+1 in dashboard; transfer missing from stock card; opaque status field |
| **assets** | Functional, buggy | Disposal missing fiscal_year/period (will crash); depreciation books to single account pair (wrong GL) |
| **crm** | Production-ready | Lead code not unique; Opportunity FKs are BigInteger (orphan risk) |
| **contracts** | Production-ready | Template contract_type not aligned with Contract types |
| **bidding** | Functional | bid_type has leading-space default; status has no choices |
| **banking** | Production-ready (core) | Upload view duplicates parse logic; auto-reconcile is N+1 and crude |
| **budget** | Functional | range_map prefixes wrong (double-counting/omissions); heuristics arbitrary |
| **costing** | Incomplete | Only creates half the closing entries (no N632/C154) |
| **approvals** | Production-ready | No DB constraint on single-pending-per-object; hook swallows exceptions |
| **fx** | **Broken** | Gain/loss calculation fundamentally wrong (treats FC as VND) |
| **recurring** | Production-ready | Silent failure on runner exceptions |
| **input_docs** | Functional | Auto-posts without review; locale-ambiguous number parsing |
| **projects** | Functional | BigInteger FKs (orphan risk); no auto-creation of transactions |
| **loans** | **Stub** | No service layer; no GL posting; no detail views |
| **guarantees** | **Stub** | No service layer; no GL posting; no create/release views |
| **documents** | Production-ready | VoucherDocument/Attachment overlap |
| **notifications** | Production-ready | Dedup hash non-deterministic; superuser broadcast not company-scoped |

---

## Top Priority Fixes (ordered by impact)

1. **CRITICAL — FX revaluation is broken** (10.1, 10.2) — produces wrong numbers, will misstate financials
2. **CRITICAL — Bidding bid_type leading space** (5.1) — corrupts all new bid records
3. **HIGH — Assets disposal missing fiscal_year/period** (2.2) — will crash at runtime
4. **HIGH — Assets depreciation single account pair** (2.1) — books all depreciation to wrong GL accounts
5. **HIGH — Budget range_map wrong prefixes** (7.1) — budget vs actual analysis is incorrect
6. **HIGH — Costing only creates half the closing entries** (8.2) — WIP accumulates, COGS understated
7. **HIGH — Loans and Guarantees are stubs with no GL integration** (14.2, 15.1) — described but unimplemented
8. **HIGH — Notifications dedup hash is non-deterministic** (17.1) — duplicate reminders sent every run
9. **HIGH — CRM Lead code not unique** (3.1) — duplicate codes allowed
10. **HIGH — Multiple services create vouchers without required fields** (X.1) — runtime crashes
