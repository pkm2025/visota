# T4 — REST API

> Tài liệu API cho tích hợp hệ thống ngoài.

## Tổng quan

Visota ERP hiện chưa có REST API công khai đầy đủ — django-ninja đã config nhưng
chưa xây endpoints. Tài liệu này mô tả **API contract planned** và hướng dẫn
contributing.

> **Status**: Planned (Q3 2026 roadmap). Hiện chỉ có HTML UI.

## Authentication

### JWT (planned)

```
POST /api/auth/token
  Body: { username, password }
  Response: { access: "eyJ...", refresh: "eyJ..." }

POST /api/auth/refresh
  Body: { refresh: "..." }
  Response: { access: "..." }
```

### API Key (planned)

Cho service-to-service integration:

```
Header: X-API-Key: pmk_xxxxxxxxxxxxxxxxxxxxxxxx
```

API Key tied to a User + scopes (e.g. `read:vouchers`, `write:einvoice`).

## Endpoints planned

### Accounting (`/api/v1/vouchers/`)

```
GET    /api/v1/vouchers/                       List
POST   /api/v1/vouchers/                       Create
GET    /api/v1/vouchers/{id}/                  Detail
PUT    /api/v1/vouchers/{id}/                  Update (draft only)
DELETE /api/v1/vouchers/{id}/                  Delete (draft only)
POST   /api/v1/vouchers/{id}/post/             Post (status → ledger)
POST   /api/v1/vouchers/{id}/unpost/           Unpost
GET    /api/v1/vouchers/{id}/print/            PDF
GET    /api/v1/vouchers/export/                Excel export
```

### Sales (`/api/v1/sales/`)

```
GET    /api/v1/sales/invoices/                 List
POST   /api/v1/sales/invoices/                 Create (auto-voucher)
GET    /api/v1/sales/invoices/{id}/            Detail
PUT    /api/v1/sales/invoices/{id}/            Update
DELETE /api/v1/sales/invoices/{id}/            Cancel
GET    /api/v1/sales/customers/
POST   /api/v1/sales/customers/
```

### Purchasing (`/api/v1/purchasing/`)

Tương tự sales — `/api/v1/purchasing/invoices/`, `/vendors/`.

### E-Invoice (`/api/v1/einvoice/`)

```
POST   /api/v1/einvoice/issue/{sales_invoice_id}/   Issue from sales
POST   /api/v1/einvoice/{id}/publish/               Assign number
POST   /api/v1/einvoice/{id}/cancel/                Cancel
GET    /api/v1/einvoice/{id}/xml/                   Download XML
GET    /api/v1/einvoice/{id}/json/                  Download JSON
GET    /api/v1/einvoice/bc01/{year}/{month}/        Generate BC01
```

### Banking (`/api/v1/banking/`)

```
GET    /api/v1/banking/accounts/                  List bank accounts
POST   /api/v1/banking/statements/import/         Import statement CSV
POST   /api/v1/banking/reconcile/                 Run auto-reconcile
GET    /api/v1/banking/transactions/unreconciled/ Unreconciled list
```

### Reports (`/api/v1/reports/`)

```
GET    /api/v1/reports/trial-balance/?year=2026&month=6
GET    /api/v1/reports/balance-sheet/?year=2026&period=6
GET    /api/v1/reports/pnl/?year=2026&period=6
GET    /api/v1/reports/vat-return/?year=2026&period=6
```

### Approvals (`/api/v1/approvals/`)

```
GET    /api/v1/approvals/pending/                 Queue for current user
POST   /api/v1/approvals/{id}/approve/            Approve
POST   /api/v1/approvals/{id}/reject/             Reject
```

### Notifications (`/api/v1/notifications/`)

```
GET    /api/v1/notifications/                     List
GET    /api/v1/notifications/unread-count/        For polling
POST   /api/v1/notifications/{id}/read/           Mark as read
```

## Request/Response format

### JSON

```http
GET /api/v1/vouchers/?page=1&per_page=25 HTTP/1.1
Authorization: Bearer eyJ...
Accept: application/json
```

```json
{
  "results": [
    {
      "id": 1,
      "voucher_no": "HĐSEC001",
      "voucher_type": "sales_receipt",
      "voucher_date": "2026-06-19",
      "total_vnd": "972000000",
      "status": "ledger_posted",
      "description": "Hóa đơn bán HĐSEC001 - Bao Viet",
      "lines": [
        {
          "line_no": 1,
          "account_code": "131",
          "debit_vnd": "972000000",
          "credit_vnd": "0",
          "description": "Phải thu KH"
        }
      ],
      "url": "https://erp.pkm.vn/api/v1/vouchers/1/"
    }
  ],
  "count": 25,
  "next": "https://erp.pkm.vn/api/v1/vouchers/?page=2",
  "previous": null
}
```

### Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Voucher not balanced",
    "details": {
      "total_debit": 972000000,
      "total_credit": 970000000,
      "diff": 2000000
    }
  }
}
```

HTTP status codes:
- 200 OK
- 201 Created
- 204 No Content
- 400 Bad Request (validation)
- 401 Unauthorized
- 403 Forbidden (no permission)
- 404 Not Found
- 405 Method Not Allowed
- 409 Conflict (e.g. duplicate)
- 422 Unprocessable Entity
- 429 Too Many Requests (rate limit)
- 500 Internal Server Error

## Rate limiting

```python
# Planned via django-ratelimit
@ratelimit(key='user', rate='100/m')
def voucher_list(request):
    ...
```

- Authenticated: 100 req/min
- Anonymous: 10 req/min
- Heavy endpoints (exports): 5 req/min

## Webhooks (planned)

Đăng ký nhận event:

```
POST /api/v1/webhooks/
{
  "url": "https://your-app.com/webhook",
  "events": ["voucher.posted", "einvoice.issued", "payment.received"],
  "secret": "whsec_xxx"
}
```

Hệ thống gửi POST khi event xảy ra:

```http
POST /webhook HTTP/1.1
X-PMK-Signature: sha256=abc123...
Content-Type: application/json

{
  "event": "voucher.posted",
  "timestamp": "2026-06-23T10:00:00Z",
  "data": { "voucher_id": 1, "voucher_no": "HĐSEC001", ... }
}
```

Verify signature:

```python
import hmac, hashlib

def verify(payload, signature, secret):
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## SDK (planned)

```bash
pip install pmketoan-sdk
```

```python
from pmketoan import Client

client = Client(api_key="pmk_xxx", base_url="https://erp.pkm.vn")

# List vouchers
vouchers = client.vouchers.list(year=2026, month=6)

# Create voucher
v = client.vouchers.create(
    voucher_type="journal",
    voucher_date="2026-06-23",
    description="Test API",
    lines=[
        {"account_code": "131", "debit_vnd": 1000000},
        {"account_code": "111", "credit_vnd": 1000000},
    ],
)
```

## Integration examples

### Tích hợp CRM ngoài

```python
# Pull customers every hour
import requests
resp = requests.get("https://erp.pkm.vn/api/v1/sales/customers/",
                    headers={"Authorization": "Bearer ..."})
for cust in resp.json()["results"]:
    sync_to_crm(cust)
```

### Tích hợp bank API

```python
# When bank sends payment notification, sync to Visota ERP
@app.route('/webhook/bank', methods=['POST'])
def bank_webhook():
    txn = request.json
    # Find matching voucher by amount + counterparty
    pmk.vouchers.find_and_match(txn)
```

### Tích hợp e-invoice provider

```python
# Listen for einvoice.issued event
@app.route('/webhook/pmk', methods=['POST'])
def pmk_webhook():
    event = request.json
    if event["event"] == "einvoice.issued":
        send_to_customer(event["data"])
```

## Roadmap

| Phase | Features | Target |
|-------|----------|--------|
| **Q3 2026** | Auth (JWT + API key), Vouchers CRUD, Reports | Foundation |
| **Q4 2026** | Sales, Purchasing, E-Invoice, Webhooks | Core integrations |
| **Q1 2027** | Banking, Payroll, HR | Full coverage |
| **Q2 2027** | SDK (Python/JS/PHP), Public docs | Self-serve integrators |

## Contributing

Khi xây API endpoint:

1. **Definition of Done**:
   - Endpoint exists và tested
   - API doc (OpenAPI/Swagger)
   - Authentication + permission check
   - Rate limit
   - Logging
   - 5+ test cases (happy + edge)

2. **Pattern**:

```python
# apps/api/v1/vouchers.py
from ninja import Router, Schema
from ninja.security import HttpBearer

router = Router()

class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        # Verify JWT
        return user

@router.get("/", auth=BearerAuth())
def list_vouchers(request, year: int = None, month: int = None):
    qs = AccountingVoucher.objects.filter(company=request.company)
    if year:
        qs = qs.filter(fiscal_year=year)
    return {"results": [serialize(v) for v in qs]}
```

3. **Documentation**: dùng `django-ninja` auto-schema → Swagger UI tại `/api/docs/`

---

Tài liệu liên quan:
- [T1-architecture](01-architecture.md) — Tổng quan
- [T3-data-model](03-data-model.md) — Cấu trúc dữ liệu
- [W1-procure-to-pay](../workflows/01-procure-to-pay.md) — Workflow để hiểu business logic
