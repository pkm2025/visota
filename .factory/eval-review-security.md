# Security & Multi-Tenant Isolation Review — Visota ERP

**Date:** 2026-07-16
**Scope:** `apps/core/` (middleware, models, module_config), `apps/identity/` (middleware, models, auth, backends), `apps/ui_modern/templatetags/perm_tags.py`, `apps/core/api.py`, `apps/pkm/api.py`, `apps/ledger/dnsn_api.py`, session handling, CSRF/CORS config, all `ui_modern/views/`, `public/views.py`.

---

## Executive Summary

The application has a reasonable security foundation: Django's built-in CSRF middleware, Axes brute-force protection, structured logging with PII scrubbing, and a module-permission middleware layer. However, there is a **systemic multi-tenant isolation failure**: the vast majority of list views and many detail/create views do NOT filter querysets by `request.current_company`, instead falling back to `Company.objects.first()`. This means any authenticated user can read and modify data belonging to any company (tenant) in the system. Several API endpoints have missing authentication. Object-level access control (IDOR) is inconsistent. The severity ranges from Critical to Medium.

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High     | 8 |
| Medium   | 7 |
| Low      | 5 |
| **Total** | **24** |

---

## 1. Multi-Tenant Isolation

### CRITICAL-01: Systemic queryset missing company filter in list views

**Severity:** Critical
**Files:** Multiple list views across `apps/ui_modern/views/`

**Description:**
The following `ListView` classes return objects from ALL companies instead of scoping to `request.current_company`. Any authenticated user can see every tenant's data.

| View | File | Line | Missing Filter |
|------|------|------|----------------|
| `VoucherListView` | `ledger_views.py` | ~38 | `AccountingVoucher.objects.select_related("company")` — no `.filter(company=...)` |
| `ContractListView` | `contract_views.py` | ~20 | `Contract.objects.select_related("company")` — no company filter |
| `ProjectListView` | `project_views.py` | ~30 | `Project.objects.select_related(...)` — no company filter |
| `LeadListView` | `crm_views.py` | ~25 | `CRMLead.objects.select_related(...)` — no company filter |
| `AssetListView` | `asset_views.py` | ~22 | `FixedAsset.objects.select_related(...)` — no company filter |
| `InputInvoiceListView` | `input_invoice_views.py` | ~17 | `InputInvoice.objects...` — no company filter |
| `ContractTemplateListView` | `contract_template_views.py` | ~16 | `ContractTemplate.objects.all()` — global (see CRITICAL-03) |
| `ChartOfAccountsListView` | `chart_of_accounts_views.py` | ~19 | `ChartOfAccounts.objects...` — no company filter |

**Fix:** Every `get_queryset()` must include `.filter(company=request.current_company)` or use the `for_company()` manager method:
```python
def get_queryset(self):
    company = self.request.current_company
    return AccountingVoucher.objects.filter(company=company).select_related("company")
```

---

### CRITICAL-02: `Company.objects.first()` fallback breaks tenant isolation in 60+ views

**Severity:** Critical
**Files:** Nearly all views in `apps/ui_modern/views/` (60+ occurrences)

**Description:**
The pattern `company = Company.objects.first()` or `company = getattr(request, "current_company", None) or Company.objects.first()` is used pervasively. When `current_company` is `None` (which happens whenever `session["current_company_id"]` is unset), the code silently operates on the first company in the database (lowest PK), which is arbitrary. This affects:

- All create operations (`form.instance.company = Company.objects.first()`)
- All report generation (`company = Company.objects.first()`)
- All service calls (`SalesInvoiceService(company=company)`, etc.)
- Dashboard metrics
- Treasury, stock, payroll, HR, closing, CTGS, costing views

**Representative examples:**
- `vendor_views.py`: `form.instance.company = Company.objects.first()`
- `sales_views.py`: `company = Company.objects.first()`
- `payroll_views.py`: `company = Company.objects.first()`
- `hr_views.py`: `company = Company.objects.first()`
- `tool_views.py`: 6 occurrences
- `report_views.py`: 10 occurrences

**Fix:** Enforce `request.current_company` with a hard error if missing. Add a mixin or decorator:
```python
class CompanyRequiredMixin:
    def get_company(self):
        company = getattr(self.request, "current_company", None)
        if not company:
            raise PermissionDenied("No company context")
        return company
```
All views should use `self.get_company()` instead of `Company.objects.first()`.

---

### CRITICAL-03: `ContractTemplate` model has no company isolation (global model)

**Severity:** Critical (design flaw)
**File:** `apps/contracts/models.py:64`

**Description:**
`ContractTemplate` extends `models.Model` directly, NOT `CompanyOwnedModel`. It is a shared global table. All CRUD views (`ContractTemplateCreateView`, `ContractTemplateEditView`, `ContractTemplateDeleteView`) in `contract_template_views.py` allow ANY authenticated user to create, edit, or delete templates visible to ALL tenants. Any user can also see all templates via `ContractTemplateListView`.

**Fix:** Either:
1. Add `company` FK and inherit `CompanyOwnedModel`, OR
2. Mark system templates as read-only and restrict create/edit/delete to superusers, OR
3. At minimum, scope queries by company in views.

---

### CRITICAL-04: IDOR — Detail/update/delete views fetch by PK without company scope

**Severity:** Critical
**Files:** Multiple views

**Description:**
Several `get_object_or_404()` calls retrieve objects by primary key without filtering by company, allowing cross-tenant access via direct URL:

| View | File | Line | Code |
|------|------|------|------|
| `VoucherDetailView` | `ledger_views.py` | — | `AccountingVoucher.objects.select_related(...)` (no company filter in `get_queryset`) |
| `ContractDetailView` | `contract_views.py` | ~45 | `Contract.objects.select_related("company", "linked_voucher")` — no company filter |
| `VoucherPrintView` | `document_views.py` | ~19 | `get_object_or_404(AccountingVoucher, pk=pk)` — no company |
| `VoucherUploadView` | `document_views.py` | ~37 | `get_object_or_404(AccountingVoucher, pk=pk)` — no company |
| `VoucherDeleteView` | `document_views.py` | — | Same pattern |
| `MasterDataDeleteView` | `_delete_views.py` | ~27 | `get_object_or_404(self.model, pk=pk)` — no company (affects Customer, Vendor, Product deletes) |
| `AttachmentDownloadView` | `attachment_views.py` | ~73 | `get_object_or_404(Attachment, pk=pk)` — no company/user scope |
| `AttachmentDeleteView` | `attachment_views.py` | ~58 | Same — any user can delete any attachment |
| `AssetDisposeView` | `asset_views.py` | — | `get_object_or_404(FixedAsset, pk=pk)` — no company |
| `OpportunityDetailView` | `crm_views.py` | — | `get_object_or_404(Opportunity, pk=pk)` — no company |
| `AdminRoleEditView` | `admin_views.py` | ~91,108 | `get_object_or_404(Role, pk=pk)` — no company (see HIGH-01) |

**Fix:** All object fetches must include `company=request.current_company`:
```python
voucher = get_object_or_404(AccountingVoucher, pk=pk, company=request.current_company)
```

---

### HIGH-01: `AdminRoleEditView` allows cross-tenant role editing

**Severity:** High
**File:** `apps/ui_modern/views/admin_views.py:91,108`

**Description:**
```python
role = get_object_or_404(Role, pk=pk)  # No company filter!
```
A staff user from company A can edit the permissions of any role belonging to company B by visiting `/modern/admin/roles/<pk>/edit/` with a cross-tenant role PK. This allows privilege escalation: the attacker can grant their user all permissions in the target company by editing that company's role, or strip permissions to cause denial of service.

**Fix:**
```python
company = self.request.current_company
role = get_object_or_404(Role, pk=pk, company=company)
```

---

### HIGH-02: `CompanyProfileView` does not verify the user belongs to the company being edited

**Severity:** High
**File:** `apps/ui_modern/views/company_views.py:21`

**Description:**
```python
def get_company(self, request):
    return getattr(request, "current_company", None) or Company.objects.first()
```
The POST handler allows editing the company profile (name, tax_code, branding, module visibility, bank accounts) but does not verify the user has an admin/staff role for that company. Combined with the `Company.objects.first()` fallback, any authenticated user could potentially edit the first company's profile if their session doesn't have `current_company_id` set.

Additionally, the view does NOT require `is_staff` or `is_superuser` — any `LoginRequiredMixin` user can access it.

**Fix:** Add `StaffRequiredMixin` and enforce `company = request.current_company` without fallback.

---

### HIGH-03: `ChartOfAccountsChangeCodeView` cascades VoucherLine updates across ALL companies

**Severity:** High
**File:** `apps/ui_modern/views/chart_of_accounts_views.py:91`

**Description:**
```python
VoucherLine.objects.filter(account_code=old_code).update(account_code=new_code)
```
This bulk update does NOT include a `company` filter. When an account code is changed for one company, ALL voucher lines with the same account code across ALL tenants are updated. This corrupts the accounting data of every other company that happens to use the same account code (which is extremely common under TT133 since companies share the same chart of accounts structure).

**Fix:**
```python
VoucherLine.objects.filter(
    voucher__company_id=account.company_id,
    account_code=old_code,
).update(account_code=new_code)
```

---

### MEDIUM-01: `CompanyOwnedModel` manager does not auto-filter by tenant

**Severity:** Medium
**File:** `apps/core/managers.py:8-16`

**Description:**
The `CompanyManager` has a `for_company()` method but does NOT use thread-local context to auto-filter. The `CompanyOwnedModel` base class provides the `company` FK but the default `objects` manager returns all rows across all tenants. Every caller must manually `.filter(company=...)`.

This is a "secure by default" design problem. The current architecture relies on every developer remembering to filter in every query, which has already failed in dozens of places (see CRITICAL-01, CRITICAL-04).

**Fix:** Implement a tenant-aware manager using a context manager or middleware-set thread-local:
```python
import threading
_tenant = threading.local()

class TenantManager(models.Manager.from_queryset(CompanyQuerySet)):
    def get_queryset(self):
        qs = super().get_queryset()
        company_id = getattr(_tenant, 'company_id', None)
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs
```

---

### MEDIUM-02: `AttachmentUploadView` allows attaching to any object in any tenant

**Severity:** Medium
**File:** `apps/ui_modern/views/attachment_views.py:41`

**Description:**
```python
obj = get_object_or_404(model_class, pk=object_id)
company = getattr(obj, "company", None)
```
The view resolves any content type + object ID without verifying the object belongs to the current company. An attacker could attach files to objects in other companies. The company is derived from the target object itself rather than validated against the user's session.

**Fix:** After fetching the object, verify `obj.company == request.current_company` before proceeding.

---

### MEDIUM-03: `ContractTemplatePreviewRawView` renders user-supplied Django template HTML

**Severity:** Medium
**File:** `apps/ui_modern/views/contract_template_views.py:152-169`

**Description:**
```python
rendered = engines["django"].from_string(html).render(ctx)
```
User-supplied HTML is rendered as a Django template. While this is a template editor by design, any authenticated user can submit template code that executes arbitrary Python via `{% load %}` tags or template tag abuse. The Django template engine is sandboxed but not perfectly — custom template tags or filters in the project could be exploited.

**Fix:** Restrict template editing to admin/superuser users. Consider using a restricted template sandbox or a markup language (Markdown, Jinja2 sandboxed environment) instead of raw Django templates.

---

## 2. Permission Gaps

### CRITICAL-04 (also listed above): API endpoint missing authentication

**Severity:** Critical
**File:** `apps/core/api.py:166-173`

**Description:**
```python
@api.get(
    "/sales/invoices/{invoice_id}",
    response=SalesInvoiceDetailSchema,
    tags=["Sales"],
    # NO auth= parameter!
)
def get_sales_invoice(request, invoice_id: int):
```
This endpoint is missing the `auth=get_current_user` parameter that all other endpoints have. Any unauthenticated user can retrieve sales invoice details (including customer info, line items, amounts) by ID. While the ninja API may have a default auth, the `NinjaAPI()` constructor does not set one, so this endpoint is truly open.

**Fix:** Add `auth=get_current_user`:
```python
@api.get(
    "/sales/invoices/{invoice_id}",
    response=SalesInvoiceDetailSchema,
    tags=["Sales"],
    auth=get_current_user,
)
```

---

### HIGH-04: All `/modern/` views use only `login_required` — no per-action permission checks

**Severity:** High
**File:** `apps/ui_modern/urls.py` (all URL patterns)

**Description:**
Every URL pattern uses `login_required(SomeView.as_view())`. No view uses `permission_required`, `user_passes_test`, or any per-action permission decorator. The only permission enforcement is the `ModulePermissionMiddleware` which checks `<module>.access` (module-level visibility) but does NOT enforce finer-grained permissions like `voucher.create`, `voucher.delete`, `report.view`, etc.

This means:
- Any user with `ledger.access` can delete any voucher (no `voucher.delete` check).
- Any user with `hr.access` can run payroll.
- Any user with `reporting.access` can see all financial reports including salary data.
- The `has_perm` template tag exists and is used in templates to show/hide UI elements, but the backend views never enforce these same permissions.

**Fix:** Add permission checks to write operations:
```python
from apps.identity.services import UserService

class VoucherDeleteView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        service = UserService(request.user, request.current_company)
        if not service.has_permission("ledger.voucher.delete"):
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)
```

---

### HIGH-05: `ContactUpdateStatusView` in public app has no staff check

**Severity:** High
**File:** `apps/public/views.py:345-361` (accessed via `apps/public/urls.py`)

**Description:**
The public app has its own URL route `/admin/contacts/<pk>/status/` mapped to `ContactUpdateStatusView` which only requires `LoginRequiredMixin`. Any authenticated user can update contact request statuses. This is separate from the `ui_modern` version at `ContactListAdminView`.

Additionally, the `ContactListAdminView` in `public/views.py` also only requires login — any user can see all contact requests (which contain names, emails, phone numbers, company names from the public signup form).

**Fix:** Add `StaffRequiredMixin` or `UserPassesTestMixin` to both views.

---

### MEDIUM-04: `AdminUserListView` shows ALL users across ALL companies

**Severity:** Medium
**File:** `apps/ui_modern/views/admin_views.py:83`

**Description:**
```python
def get_queryset(self):
    return User.objects.all().order_by("-is_superuser", "username")
```
Any staff user can see all users in the system, not just users in their company. This leaks usernames, emails, full names, and phone numbers of users from all tenants.

**Fix:**
```python
def get_queryset(self):
    company = self.request.current_company
    return User.objects.filter(company_roles__company=company).distinct()
```

---

## 3. Guardian / Object Permissions

### LOW-01: Guardian is NOT used — no object-level permissions exist

**Severity:** Low (informational)
**File:** N/A

**Description:**
The review scope mentions "guardian/perm_tags" but django-guardian is NOT installed (not in `INSTALLED_APPS`, not in `requirements.txt`). The permission system is entirely custom (code-based via `Permission`, `Role`, `UserCompanyRole` models). The `perm_tags.py` template tags provide `has_module_access` and `user_permissions_for` which check code-level permissions.

There are no object-level permissions at all. Access control to individual records relies solely on company scoping (which is broken per findings above). There is no mechanism to restrict a user to a subset of objects within a company.

**Recommendation:** If fine-grained object-level access is needed (e.g., a user can only see vouchers they created), either:
1. Add django-guardian and assign permissions on object creation, OR
2. Add an `owner` / `created_by` field and filter querysets accordingly.

---

## 4. Module Visibility

### HIGH-06: Module middleware only checks `/modern/` paths — API endpoints bypass module permissions entirely

**Severity:** High
**File:** `apps/identity/middleware.py:14,40-41`

**Description:**
The `ModulePermissionMiddleware` explicitly exempts `/api/` from permission checks:
```python
EXEMPT_PREFIXES = (
    "/api/",  # ← API endpoints bypass ALL module permission checks
    ...
)
```
A user without `ledger.access` (module hidden from their sidebar) can still access `/api/v1/vouchers/` and all voucher CRUD via the REST API. Similarly, all PKM, DNSN, e-invoice, and reporting API endpoints are accessible regardless of module visibility.

**Fix:** Either:
1. Remove `/api/` from `EXEMPT_PREFIXES` and extend `_resolve_module()` to map API paths, OR
2. Add per-endpoint permission checks in the API functions.

---

### MEDIUM-05: Unmapped URL paths under `/modern/` bypass module checks

**Severity:** Medium
**File:** `apps/identity/middleware.py:78-80`

**Description:**
The `_resolve_module()` function returns `None` (no permission required) for any path under `/modern/` that is not in `PATH_MODULE_MAP`. This means:
- `/modern/admin/` paths (company profile, roles, users, migration) have NO module permission requirement.
- `/modern/attachments/` has no module check.
- `/modern/search/` has no module check.
- `/modern/me/permissions/` — fine, but adjacent admin paths are exposed.
- `/modern/ctgs/` — missing from `PATH_MODULE_MAP` (CTGS create/register/check/schedule).
- `/modern/tools/` — period tools (year-end carry forward, period allocation, closing entry) are not mapped.
- `/modern/departments/` — department master is not mapped.
- `/modern/dnsn-vouchers/` and `/modern/dnsn-ledgers/` and `/modern/dnsn-reports/` — TT58 voucher paths not in map (though these are sub-paths, they should map to ledger).

Any user can access these admin/tools paths regardless of their role.

**Fix:** Add all module paths to `PATH_MODULE_MAP`, and add a catch-all for `/modern/admin/` that requires staff/superuser.

---

## 5. Session Security

### MEDIUM-06: No session rotation on login or company switch

**Severity:** Medium
**File:** `apps/ui_modern/views/auth_views.py`, `apps/ui_modern/views/company_switch.py`

**Description:**
- `VisotaLoginView` uses Django's default `LoginView` which does call `login()` (which rotates the session key via `cycle_key()` in Django's `login()`). This is correct.
- However, `CompanySwitchView` changes `request.session["current_company_id"]` without rotating the session key. While this doesn't enable session fixation per se, it means the permission cache (`user_perms_{user_id}_{company_id}`) could be stale for up to 5 minutes if the old company's cache entry persists.
- `SignupView` in `public/views.py` calls `login(request, user, backend=...)` which does rotate the key. Correct.

**Fix:** After switching company, invalidate the user's permission cache:
```python
UserService(request.user, Company.objects.get(id=company_id)).invalidate_cache()
```

---

### LOW-02: No `SESSION_COOKIE_HTTPONLY` or `SESSION_COOKIE_SAMESITE` explicitly set

**Severity:** Low
**File:** `config/settings/base.py:160`

**Description:**
Django defaults `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE='Lax'`, so these are secure by default. However, they are not explicitly set, meaning a future settings change could inadvertently weaken them. `CSRF_COOKIE_HTTPONLY` is also not set (defaults to `False`).

**Fix:** Explicitly set in `base.py`:
```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True  # Requires JS to read CSRF from DOM meta tag instead
```

---

## 6. CSRF / CORS

### LOW-03: No CORS configuration — acceptable for session-cookie app

**Severity:** Low (informational)
**File:** N/A

**Description:**
No CORS headers are configured (no `django-cors-headers` in installed apps). This is actually secure for a session-cookie-based application — the API uses the same session cookie, and cross-origin requests are blocked by the browser's default SOP. The `CsrfViewMiddleware` is properly in the middleware stack.

The API key auth path (`X-API-Key` header) would need CORS if used from browsers, but since that path is broken (see MEDIUM-07), this is moot.

**Status:** Acceptable as-is.

---

### LOW-04: CSRF exemption not present — good

**Severity:** Low (positive finding)
**File:** All views

**Description:**
No `@csrf_exempt` decorators found anywhere in the codebase. All POST operations properly require CSRF tokens. The HTMX-based interactions correctly include the CSRF token via the `X-CSRFToken` header (standard Django + HTMX pattern).

---

## 7. SQL Injection

### LOW-05: Raw SQL in vector_store.py uses parameterized queries — safe

**Severity:** Low (positive finding)
**File:** `apps/pkm/services/vector_store.py`

**Description:**
The only raw SQL in the codebase is in `vector_store.py` for MariaDB VECTOR operations. All queries use parameterized cursors:
```python
cursor.execute(
    "INSERT INTO pkm_embedding (...) VALUES (%s, %s, %s, ...)",
    [chunk_id, user_id, company_id, content, vec_str, model_name],
)
```
No string interpolation (`f"{var}"` or `%` formatting) is used in SQL construction. This is safe against SQL injection.

**Status:** No SQL injection vulnerabilities found.

---

## 8. PII Exposure

### HIGH-07: API schemas expose tax codes, phone numbers, and addresses

**Severity:** High
**File:** `apps/core/api.py:83-100`

**Description:**
The `CustomerSchema` and `VendorSchema` expose `tax_code`, `address`, `phone`, `email` in API responses. Combined with CRITICAL-04 (missing auth on `get_sales_invoice`) and the lack of company scoping in `list_customers`/`list_vendors`, this PII is accessible to any user.

The `CustomerSchema` includes:
```python
class CustomerSchema(Schema):
    tax_code: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
```

Additionally, salary-related report endpoints (`SalaryFundReportView`, `PITMonthlyReportView`, `LaborUsageReportView`) expose employee compensation data to any user with `reporting.access` — no separate HR permission is required.

**Fix:**
1. Fix the missing auth on the sales invoice endpoint.
2. Ensure all list endpoints are company-scoped.
3. Add a separate `hr.payroll.view` permission check on salary-related report views.

---

### MEDIUM-07: Structured logging PII scrubbing is incomplete

**Severity:** Medium
**File:** `apps/core/logging_utils.py:14-18`

**Description:**
The PII pattern matching has gaps:

1. **Tax code regex is overly broad:** `\b\d{9,12}\b` matches any 9-12 digit number, including legitimate financial amounts (e.g., VND amounts in the billions have 10+ digits). This causes false positives, redacting valid data while potentially missing actual tax codes in non-standard formats.

2. **No salary/income scrubbing:** The `PII_KEYS` set includes `tax_code` but not salary-related field names like `salary`, `base_salary`, `gross_pay`, `net_pay`, `bonus`, `allowance`.

3. **Phone regex misses Vietnamese formats:** `\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4,5}\b` doesn't match Vietnamese mobile formats like `09xx.xxx.xxx` (10 digits) or `+84 9xx xxx xxx`.

4. **Only scrubs extra fields, not main message:** The `StructuredJSONFormatter.format()` method scrubs `user_id`, `path`, `method`, etc. but does NOT scrub the `message` field itself, which could contain PII if logged directly.

**Fix:**
- Add salary-related keys to `PII_KEYS`.
- Apply `scrub_value()` to the `message` field as well.
- Adjust the phone regex for Vietnamese formats: `r'(?:\+84|0)\d{9,10}'`.

---

## 9. Branding Middleware

### MEDIUM-08: `hide_visota_branding` has no bypass path but depends on correct company resolution

**Severity:** Medium
**File:** `apps/core/middleware.py:53-70`

**Description:**
The `BrandingMiddleware` correctly reads `hide_visota_branding` from the company. However, when `current_company` is `None` (no session company set), it falls back to `DEFAULT_BRAND` which has `hide_visota_branding: False`. This means:

1. If a company has hidden branding, but a user's session doesn't have `current_company_id`, the Visota branding is shown — potentially violating the white-label agreement.
2. The `ModulePermissionMiddleware` has a fallback at line 51-55 that sets `request.current_company = Company.objects.first()` if not set — this means the branding shown could be for the wrong company.

There is no direct "bypass" per se, but the fallback behavior is incorrect for white-label customers.

**Fix:** Ensure `current_company` is always set (require company selection after login). The `TenantMiddleware` should redirect to a company-selection page if no `current_company_id` is in the session.

---

## 10. Audit Trail

### HIGH-08: Sensitive operations lack audit logging

**Severity:** High
**Files:** Multiple views

**Description:**
The only audit logging is in `apps/identity/audit.py:record_login()` which records `last_login_ip` on successful login. There is no audit trail for:

1. **Voucher creation/deletion/posting** — financial entries are created and posted without any log of who did it. The `AccountingVoucher` model has no `created_by` or `posted_by` field.
2. **Company profile changes** — branding, tax configuration, bank accounts are modified without logging.
3. **Role/permission changes** — `AdminRoleEditView` changes role permissions without any audit record.
4. **Company switching** — no log of when a user switches between companies.
5. **User role assignments** — `AdminUserAssignView` grants/revokes roles without logging.
6. **E-invoice issuance** — financial documents published to tax authorities without audit trail.
7. **Payroll runs** — salary calculations executed without recording who ran them.
8. **Data deletion** — master data records (customers, vendors, products) deleted without soft-delete or audit log.

For a Vietnamese accounting ERP subject to TT133/TT200 regulations, this is a significant compliance gap. Vietnamese accounting law requires maintaining an audit trail of all accounting entries.

**Fix:** Add an `AuditLog` model and record all sensitive operations:
```python
class AuditLog(CompanyOwnedModel):
    user = models.ForeignKey("identity.User", on_delete=SET_NULL, null=True)
    action = models.CharField(max_length=100)  # "voucher.create", "role.edit"
    entity_type = models.CharField(max_length=100)
    entity_id = models.BigIntegerField(null=True)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```
Add `created_by` / `updated_by` fields to all accounting models. Use Django signals or service-layer logging to capture all mutations.

---

## Additional Findings

### MEDIUM-09: Broken API key authentication path

**Severity:** Medium
**File:** `apps/core/api.py:43-47`

**Description:**
```python
api_key = request.headers.get("X-API-Key", "")
if api_key.startswith("pmk_"):
    user = User.objects.filter(api_key=api_key[4:]).first()
```
The `User` model has NO `api_key` field (confirmed by reading `apps/identity/models.py` and all migrations). This query will raise a `FieldError` at runtime, causing a 500 error for any request using `X-API-Key`. The API key authentication is dead code — it has never worked and would crash if attempted.

This is not directly exploitable (it fails closed with a 500), but it represents a false sense of security: developers may believe API key auth is functional.

**Fix:** Either remove the API key auth path entirely, or add an `api_key` field to the User model with proper generation and hashing.

---

### LOW-06: `SECURE_BROWSER_XSS_FILTER` is deprecated

**Severity:** Low
**File:** `config/settings/prod.py:17`

**Description:**
```python
SECURE_BROWSER_XSS_FILTER = True
```
This setting was deprecated in Django 3.0 and removed in Django 4.0. The `X-XSS-Protection` header it sets is deprecated by modern browsers. It has no effect in Django 5.2.

**Fix:** Remove the setting. Rely on `SECURE_CONTENT_TYPE_NOSNIFF` and CSP (consider adding `django-csp` for Content-Security-Policy headers).

---

### LOW-07: Axes brute-force protection disabled in dev

**Severity:** Low
**File:** `config/settings/dev.py:23-26`

**Description:**
```python
AXES_FAILURE_LIMIT = 10000
```
Brute-force protection is effectively disabled in dev. If the dev settings are accidentally used in production (misconfigured `DJANGO_SETTINGS_MODULE`), the system would be vulnerable to credential stuffing.

**Fix:** Document clearly that dev settings must never be used in production. Consider adding a startup check that fails if `DEBUG=True` and `ALLOWED_HOSTS` contains public domains.

---

### LOW-08: `SignupView` has no rate limiting

**Severity:** Low
**File:** `apps/public/views.py:239-330`

**Description:**
The public signup endpoint (`/signup/`) has no rate limiting. An attacker could:
1. Mass-create user accounts and companies, filling the database.
2. Enumerate which emails are already registered (the error "Email đã được sử dụng" reveals existing accounts).

The Axes configuration only protects the login endpoint, not signup.

**Fix:** Add `django-ratelimit` or use Axes to protect the signup endpoint:
```python
from django_ratelimit.decorators import ratelimit

@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class SignupView(View):
    ...
```

---

## Summary of Recommendations (Priority Order)

1. **CRITICAL — Fix company scoping in ALL views:** Replace every `Company.objects.first()` with `request.current_company` (with a hard error if missing). Add `.filter(company=...)` to every `get_queryset()` and `get_object_or_404()`. This is the single highest-impact fix.

2. **CRITICAL — Add `auth=get_current_user` to the sales invoice detail API endpoint.**

3. **CRITICAL — Add company isolation to `ContractTemplate` or restrict to superusers.**

4. **CRITICAL — Fix the `VoucherLine` cross-tenant update in `ChartOfAccountsChangeCodeView`.**

5. **HIGH — Add per-action permission checks** (not just module-level) to write operations (create, update, delete, post).

6. **HIGH — Add `StaffRequiredMixin` to `CompanyProfileView` and public `ContactUpdateStatusView`.**

7. **HIGH — Remove `/api/` from `EXEMPT_PREFIXES`** in module middleware, or add per-endpoint permission checks.

8. **HIGH — Implement audit logging** for all sensitive operations (voucher CRUD, role changes, payroll, e-invoice).

9. **MEDIUM — Fix the broken API key auth path** (add field or remove dead code).

10. **MEDIUM — Improve PII scrubbing** in structured logging (salary fields, message field, Vietnamese phone formats).

11. **MEDIUM — Consider a tenant-aware manager** that auto-filters by company to prevent future regressions.
