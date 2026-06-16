# 03. Lớp API django-ninja

> REST API + OpenAPI bằng django-ninja. Dùng cho: integrations, mobile, JS-heavy pages.

## 1. Tổng quan

django-ninja được dùng cho:
- **Mobile app** (nếu có)
- **Integrations** với hệ thống ngoài (BKAV, TCT, EBanking, mobile apps)
- **Vue/React SPA** (nếu sau này cần rebuild phần nào đó)
- **Public API** cho partner

Lưu ý: phần lớn UI sẽ dùng **HTML rendering cho HTMX** chứ không phải JSON API. API JSON chỉ dùng khi cần.

## 2. Cấu trúc API

```
/api/v1/
├── /auth/
│   ├── POST /login/                          (username, password → token)
│   ├── POST /logout/
│   ├── POST /refresh/                        (refresh JWT)
│   ├── GET  /me/                             (current user info)
│   └── POST /2fa/verify/
│
├── /companies/
│   ├── GET /                                 (list companies for current user)
│   ├── POST /                                (create)
│   ├── GET /{id}/
│   ├── PATCH /{id}/
│   └── POST /{id}/switch/                    (switch current company)
│
├── /chart-of-accounts/
│   ├── GET /                                 (list, filter by parent, level)
│   ├── POST /
│   ├── GET /{code}/
│   ├── PATCH /{code}/
│   ├── DELETE /{code}/
│   └── GET /tree/                            (tree structure)
│
├── /customers/
│   ├── GET /                                 (paginated, search, filter)
│   ├── POST /
│   ├── GET /{id}/
│   ├── PATCH /{id}/
│   ├── DELETE /{id}/
│   ├── GET /{id}/balance/                    (current AR balance)
│   ├── GET /{id}/aging/                      (AR aging)
│   └── POST /import/                         (CSV/Excel)
│
├── /vendors/                                 (similar)
│
├── /products/                                (similar)
│   ├── GET /{id}/stock/                      (current stock by warehouse)
│   └── GET /{id}/cost/                       (current unit cost)
│
├── /vouchers/                                (Accounting voucher)
│   ├── GET /                                 (paginated, filter by type/date/status)
│   ├── POST /
│   ├── GET /{id}/
│   ├── PATCH /{id}/
│   ├── DELETE /{id}/
│   ├── POST /{id}/post/                      (status=2)
│   ├── POST /{id}/unpost/                    (status=2→0)
│   ├── POST /{id}/lock/                      (status=3)
│   ├── POST /{id}/reverse/                   (reversal voucher)
│   └── GET /{id}/audit-log/
│
├── /sales-invoices/
│   ├── GET / POST / PATCH / DELETE (similar)
│   ├── POST /{id}/issue-einvoice/            (issue BKAV e-invoice)
│   ├── POST /{id}/cancel-einvoice/
│   └── GET /{id}/printable/                  (PDF link)
│
├── /purchase-invoices/                       (similar)
│
├── /stock-vouchers/                          (similar)
│   ├── POST /{id}/post/                      (post + update stock_ledger)
│   └── POST /calculate-cost/                 (trigger costing job)
│
├── /fixed-assets/
│   ├── CRUD
│   ├── POST /{id}/depreciate/                (depreciate period)
│   ├── POST /{id}/transfer/                  (transfer to another dept)
│   └── POST /{id}/dispose/                   (liquidate)
│
├── /employees/                               (CRUD)
├── /attendance/
├── /payroll-runs/
│
├── /period-closing/
│   ├── POST /allocate/                       (run allocation)
│   ├── POST /close/                          (run closing templates)
│   ├── POST /lock-period/                    (lock month)
│   └── POST /year-end-carry-forward/
│
├── /reports/
│   ├── GET /trial-balance/
│   ├── GET /balance-sheet/
│   ├── GET /pnl/
│   ├── GET /cash-flow/
│   ├── GET /vat-return/
│   ├── GET /ar-aging/
│   ├── GET /stock-card/
│   └── GET /{report_code}/export/?format=pdf|xlsx
│
├── /e-invoices/
│   ├── GET /                                 (list pulled from TCT)
│   ├── POST /pull-from-tct/                  (sync from tax portal)
│   ├── POST /match/                          (match with purchase invoice)
│
└── /system/
    ├── /users/                               (CRUD)
    ├── /roles/
    ├── /permissions/
    ├── /fiscal-years/
    ├── /voucher-books/
    └── /parameters/
```

## 3. Convention

### 3.1. URL convention

- Plural nouns: `/vouchers/`, `/customers/`
- Use kebab-case: `/sales-invoices/`
- Filters as query params: `?status=2&from_date=2026-01-01`
- Pagination: `?page=1&page_size=25` hoặc `?limit=50&offset=0`
- Sorting: `?ordering=-voucher_date` (tiền tố `-` cho DESC)
- Search: `?search=khách+A`
- Field selection: `?fields=id,voucher_no,voucher_date` (sparse fieldset)

### 3.2. HTTP methods

| Method | Use case | Idempotent |
|--------|----------|------------|
| GET | Read | Yes |
| POST | Create | No (need Idempotency-Key) |
| PUT | Full replace | Yes |
| PATCH | Partial update | Yes |
| DELETE | Delete | Yes |

### 3.3. Status codes

| Code | Meaning |
|------|---------|
| 200 OK | Success (GET, PATCH) |
| 201 Created | Resource created (POST) |
| 204 No Content | Deleted (DELETE) |
| 400 Bad Request | Validation error |
| 401 Unauthorized | Not authenticated |
| 403 Forbidden | No permission |
| 404 Not Found | |
| 409 Conflict | Duplicate / locked |
| 422 Unprocessable Entity | Business rule violation |
| 429 Too Many Requests | Rate limited |
| 500 Server Error | |

### 3.4. Response envelope

```json
// Success
{
  "data": { ... } hoặc [ ... ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 150
  }
}

// Error
{
  "error": {
    "code": "VOUCHER_NOT_BALANCED",
    "message": "Tổng nợ không bằng tổng có",
    "details": {
      "total_debit": 110000000,
      "total_credit": 100000000,
      "diff": 10000000
    }
  },
  "trace_id": "abc123"
}
```

### 3.5. Error codes (Vietnamese business)

| Code | Mô tả |
|------|------|
| `VOUCHER_NOT_BALANCED` | Chứng từ không cân đối N=C |
| `PERIOD_LOCKED` | Kỳ đã khóa, không sửa được |
| `INSUFFICIENT_STOCK` | Tồn kho không đủ |
| `DUPLICATE_VOUCHER_NO` | Số chứng từ đã tồn tại |
| `FISCAL_YEAR_CLOSED` | Năm tài chính đã đóng |
| `ACCOUNT_NOT_FOUND` | TK không tồn tại |
| `OBJECT_NOT_FOUND` | Đối tượng không tồn tại |
| `EINVOICE_ALREADY_ISSUED` | HĐĐT đã phát hành |
| `PERMISSION_DENIED` | Không có quyền |

## 4. Setup django-ninja

```python
# config/api.py
from ninja import NinjaAPI
from ninja.security import HttpBearer
from ninja.orm import create_schema
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        jwt_auth = JWTAuthentication()
        user = jwt_auth.get_validated_token(token)
        if user:
            request.user = user
            return user
        return None


api = NinjaAPI(
    title='PMKetoan API',
    version='1.0.0',
    auth=JWTAuth(),
    docs_url='/api/docs/',
    openapi_url='/api/openapi.json',
)

# Mount routers
api.add_router('/auth/', 'apps.identity.api.auth_router')
api.add_router('/companies/', 'apps.core.api.company_router')
api.add_router('/chart-of-accounts/', 'apps.master_data.api.account_router')
api.add_router('/customers/', 'apps.master_data.api.customer_router')
api.add_router('/vendors/', 'apps.master_data.api.vendor_router')
api.add_router('/products/', 'apps.master_data.api.product_router')
api.add_router('/vouchers/', 'apps.ledger.api.voucher_router')
api.add_router('/sales-invoices/', 'apps.sales.api.invoice_router')
api.add_router('/purchase-invoices/', 'apps.purchasing.api.invoice_router')
api.add_router('/stock-vouchers/', 'apps.inventory.api.voucher_router')
api.add_router('/fixed-assets/', 'apps.assets.api.asset_router')
api.add_router('/employees/', 'apps.hr.api.employee_router')
api.add_router('/reports/', 'apps.reporting.api.report_router')
api.add_router('/period-closing/', 'apps.ledger.api.closing_router')
api.add_router('/system/', 'apps.system.api.system_router')
```

## 5. Pydantic schemas

```python
# apps/ledger/api/schemas.py
from decimal import Decimal
from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field, validator


class VoucherLineCreate(BaseModel):
    account_code: str = Field(..., max_length=20)
    object_type: Optional[Literal['customer','vendor','employee','bank','other']] = None
    object_code: Optional[str] = None
    debit_vnd: Decimal = Field(default=Decimal('0'), ge=0)
    credit_vnd: Decimal = Field(default=Decimal('0'), ge=0)
    description: Optional[str] = None
    
    @validator('credit_vnd')
    def both_not_zero(cls, v, values):
        if v == 0 and values.get('debit_vnd') == 0:
            raise ValueError('Phải có nợ hoặc có')
        if v > 0 and values.get('debit_vnd') > 0:
            raise ValueError('Không được có cả nợ và có')
        return v


class VoucherCreate(BaseModel):
    voucher_type: Literal[
        'journal', 'cash_receipt', 'cash_payment',
        'sales_invoice', 'purchase_invoice', ...
    ]
    voucher_no: Optional[str] = None  # auto if not provided
    voucher_date: date
    description: str
    currency_code: str = 'VND'
    exchange_rate: Decimal = Decimal('1')
    lines: list[VoucherLineCreate]
    
    @validator('lines')
    def at_least_two_lines(cls, v):
        if len(v) < 2:
            raise ValueError('Phải có ít nhất 2 dòng bút toán')
        return v


class VoucherLineResponse(BaseModel):
    id: int
    line_no: int
    account_code: str
    object_code: Optional[str]
    debit_vnd: Decimal
    credit_vnd: Decimal
    description: Optional[str]
    
    class Config:
        from_attributes = True


class VoucherResponse(BaseModel):
    id: int
    voucher_no: str
    voucher_type: str
    voucher_date: date
    posting_date: Optional[date]
    status: int
    currency_code: str
    exchange_rate: Decimal
    total_vnd: Decimal
    description: str
    lines: list[VoucherLineResponse]
    
    class Config:
        from_attributes = True
```

## 6. Endpoints example

```python
# apps/ledger/api/vouchers.py
from ninja import Router, Query, PatchDict, File, Form
from ninja.pagination import paginate, PageNumberPagination
from ninja.files import UploadedFile
from django.db import transaction
from apps.ledger.models import AccountingVoucher
from apps.ledger.services import VoucherService, VoucherPostingService
from apps.identity.permissions import require_permission
from .schemas import (
    VoucherCreate, VoucherResponse,
    VoucherFilter, VoucherLineResponse,
)

router = Router(tags=['vouchers'])


@router.get('/', response=list[VoucherResponse])
@paginate(PageNumberPagination)
@require_permission('ledger.voucher.view')
def list_vouchers(
    request,
    filters: VoucherFilter = Query(...),
):
    qs = (
        AccountingVoucher.objects
        .for_company(request.company_id)
        .select_related('created_by')
        .prefetch_related('lines')
    )
    return filters.filter(qs)


@router.get('/{int:voucher_id}/', response=VoucherResponse)
@require_permission('ledger.voucher.view')
def get_voucher(request, voucher_id: int):
    return get_object_or_404(
        AccountingVoucher.objects
        .for_company(request.company_id)
        .prefetch_related('lines'),
        pk=voucher_id
    )


@router.post('/', response={201: VoucherResponse})
@require_permission('ledger.voucher.create')
@transaction.atomic
def create_voucher(request, payload: VoucherCreate):
    service = VoucherService(
        company_id=request.company_id,
        user=request.user,
    )
    voucher = service.create(payload)
    return 201, voucher


@router.patch('/{int:voucher_id}/', response=VoucherResponse)
@require_permission('ledger.voucher.edit')
@transaction.atomic
def update_voucher(request, voucher_id: int, payload: PatchDict[VoucherCreate]):
    voucher = get_object_or_404(
        AccountingVoucher,
        pk=voucher_id, company_id=request.company_id
    )
    if voucher.is_locked:
        raise HttpError(409, 'PERIOD_LOCKED: Voucher is locked')
    
    service = VoucherService(
        company_id=request.company_id,
        user=request.user,
    )
    return service.update(voucher, payload)


@router.delete('/{int:voucher_id}/', response={204: None})
@require_permission('ledger.voucher.delete')
def delete_voucher(request, voucher_id: int):
    voucher = get_object_or_404(
        AccountingVoucher, pk=voucher_id, company_id=request.company_id
    )
    if voucher.is_posted:
        raise HttpError(409, 'Cannot delete posted voucher')
    voucher.delete()
    return 204


@router.post('/{int:voucher_id}/post/', response=VoucherResponse)
@require_permission('ledger.voucher.post')
@transaction.atomic
def post_voucher(request, voucher_id: int):
    voucher = get_object_or_404(
        AccountingVoucher, pk=voucher_id, company_id=request.company_id
    )
    service = VoucherPostingService()
    service.post(voucher)
    return voucher


@router.post('/{int:voucher_id}/unpost/', response=VoucherResponse)
@require_permission('ledger.voucher.unpost')
@transaction.atomic
def unpost_voucher(request, voucher_id: int):
    voucher = get_object_or_404(
        AccountingVoucher, pk=voucher_id, company_id=request.company_id
    )
    service = VoucherPostingService()
    service.unpost(voucher)
    return voucher


@router.post('/import/', response={201: dict})
@require_permission('ledger.voucher.import')
def import_vouchers(request, file: UploadedFile = File(...)):
    service = VoucherService(
        company_id=request.company_id,
        user=request.user,
    )
    result = service.import_from_excel(file)
    return 201, result
```

## 7. OpenAPI documentation

django-ninja tự sinh OpenAPI spec tại `/api/openapi.json` và Swagger UI tại `/api/docs/`.

Có thể export ra làm tài liệu API tự động.

---

**Tiếp theo**: [04. HTMX + Alpine frontend](./04-htmx-alpine-frontend.md)
