# 01. Quy ước REST API

> Tiêu chuẩn thiết kế API cho PMKetoan.

## 1. Nguyên tắc chung

### 1.1. RESTful

- Resource-based URLs: `/api/v1/vouchers/`, `/api/v1/customers/`
- HTTP methods: GET (read), POST (create), PUT (replace), PATCH (update), DELETE
- Stateless (no session in API, dùng JWT token)

### 1.2. Versioning

- URL versioning: `/api/v1/...`
- Khi breaking change: `/api/v2/...`
- v1 vẫn duy trì trong 12 tháng sau v2 ra mắt

### 1.3. JSON only

- Content-Type: `application/json`
- Charset: UTF-8
- Date format: ISO 8601 (`2026-06-15T10:30:00Z`)
- Number format: number (không string)

## 2. Authentication

### 2.1. JWT Bearer token

```http
GET /api/v1/vouchers/ HTTP/1.1
Host: api.pmketoan.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### 2.2. Token lifecycle

- Access token: 15 phút
- Refresh token: 7 ngày
- Sau khi hết hạn: POST `/api/v1/auth/refresh/` với refresh token

### 2.3. Login flow

```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "secret",
  "company_code": "PKM"
}

HTTP/1.1 200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 900,
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "Admin User",
    "email": "admin@example.com"
  },
  "company": {
    "id": 1,
    "code": "PKM",
    "name": "Công ty PKM"
  }
}
```

## 3. Response envelope

### 3.1. Success - single resource

```json
{
  "data": {
    "id": 123,
    "voucher_no": "BC0001",
    "voucher_date": "2026-06-15",
    "total_vnd": 100000000,
    "status": 2
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-15T10:30:00Z"
  }
}
```

### 3.2. Success - collection (paginated)

```json
{
  "data": [
    { "id": 123, "voucher_no": "BC0001", ... },
    { "id": 124, "voucher_no": "BC0002", ... }
  ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 150,
    "total_pages": 6,
    "request_id": "req_abc123"
  }
}
```

### 3.3. Error

```json
{
  "error": {
    "code": "VOUCHER_NOT_BALANCED",
    "message": "Tổng nợ không bằng tổng có",
    "details": {
      "total_debit": 110000000,
      "total_credit": 100000000,
      "diff": 10000000
    },
    "field_errors": [
      {
        "field": "lines",
        "message": "Tổng nợ phải bằng tổng có"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-15T10:30:00Z"
  }
}
```

## 4. HTTP status codes

| Code | Tên | Use case |
|------|-----|----------|
| 200 | OK | GET, PATCH, PUT success |
| 201 | Created | POST success |
| 204 | No Content | DELETE success |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Token invalid/expired |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource not exists |
| 405 | Method Not Allowed | Wrong HTTP method |
| 409 | Conflict | Duplicate or locked |
| 422 | Unprocessable Entity | Business rule violation |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Server Error | Unhandled exception |
| 502 | Bad Gateway | Upstream failed |
| 503 | Service Unavailable | Maintenance |
| 504 | Gateway Timeout | Timeout |

## 5. Filtering, sorting, pagination

### 5.1. Filtering

```http
GET /api/v1/vouchers/?status=2&voucher_type=sales_invoice&from_date=2026-01-01
```

- Filter theo field: `?field=value`
- Multiple values: `?status=2&status=3` (OR)
- Range: `?amount_min=1000000&amount_max=10000000`
- Null check: `?description__isnull=true`

### 5.2. Sorting

```http
GET /api/v1/vouchers/?ordering=-voucher_date,id
```

- `-` prefix cho DESC
- Multiple fields: comma-separated

### 5.3. Pagination

```http
GET /api/v1/vouchers/?page=2&page_size=25
```

Hoặc cursor-based cho large datasets:

```http
GET /api/v1/vouchers/?cursor=eyJsYXN0X2lkIjoxMjN9&limit=25
```

### 5.4. Sparse fieldset

```http
GET /api/v1/vouchers/?fields=id,voucher_no,voucher_date,total_vnd
```

### 5.5. Embed (include related)

```http
GET /api/v1/vouchers/123/?embed=lines,created_by
```

## 6. Idempotency

Mọi POST/PUT có thể gửi `Idempotency-Key` header:

```http
POST /api/v1/vouchers/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{ "voucher_no": "BC0001", ... }
```

- Server cache key trong 24 giờ
- Nếu trùng key + same payload → trả response cũ
- Nếu trùng key + different payload → 422 error

## 7. Rate limiting

Headers trả về:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1625000000
```

Khi exceeded (429):

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1625000000
```

## 8. Bulk operations

### 8.1. Bulk create

```http
POST /api/v1/vouchers/bulk/
Content-Type: application/json

{
  "vouchers": [
    { ... },
    { ... },
    { ... }
  ]
}

HTTP/1.1 207 Multi-Status
{
  "results": [
    { "index": 0, "status": 201, "data": {...} },
    { "index": 1, "status": 400, "error": {...} },
    { "index": 2, "status": 201, "data": {...} }
  ]
}
```

### 8.2. Bulk update

```http
PATCH /api/v1/vouchers/bulk/
{
  "updates": [
    { "id": 1, "status": 2 },
    { "id": 2, "status": 2 }
  ]
}
```

### 8.3. Bulk delete

```http
POST /api/v1/vouchers/bulk-delete/
{
  "ids": [1, 2, 3, 4, 5]
}
```

## 9. File upload

### 9.1. Single file

```http
POST /api/v1/files/
Content-Type: multipart/form-data; boundary=...

------boundary
Content-Disposition: form-data; name="file"; filename="invoice.pdf"
Content-Type: application/pdf

(binary data)
------boundary--
```

### 9.2. Multipart with metadata

```http
POST /api/v1/sales-invoices/123/attachments/
Content-Type: multipart/form-data

file: (binary)
description: "Hợp đồng nguyên tắc"
```

### 9.3. Resumable upload (cho file lớn)

Chunk upload qua `Content-Range` header.

## 10. File download

```http
GET /api/v1/sales-invoices/123/print/?format=pdf
Accept: application/pdf

HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="BC0001.pdf"
Content-Length: 45678

(binary data)
```

## 11. Webhooks (outbound)

Hệ thống gửi webhook khi có event:

```http
POST https://partner.example.com/webhook
X-PMKetoan-Event: voucher.posted
X-PMKetoan-Signature: sha256=abc123...
Content-Type: application/json

{
  "event": "voucher.posted",
  "timestamp": "2026-06-15T10:30:00Z",
  "data": {
    "voucher_id": 123,
    "voucher_no": "BC0001",
    ...
  }
}
```

Partner verify signature bằng HMAC SHA-256.

## 12. Long-running operations

### 12.1. Async job creation

```http
POST /api/v1/period-closing/
{
  "fiscal_year": 2026,
  "period": 6
}

HTTP/1.1 202 Accepted
{
  "job_id": "job_xyz789",
  "status": "queued",
  "estimated_duration_seconds": 120,
  "status_url": "/api/v1/jobs/job_xyz789/"
}
```

### 12.2. Poll status

```http
GET /api/v1/jobs/job_xyz789/

HTTP/1.1 200 OK
{
  "job_id": "job_xyz789",
  "status": "running",
  "progress": 65,
  "started_at": "2026-06-15T10:30:00Z",
  "estimated_remaining_seconds": 40
}
```

### 12.3. Webhook callback khi hoàn thành

```http
POST https://app.example.com/webhooks
{
  "event": "job.completed",
  "job_id": "job_xyz789",
  "result": {...}
}
```

## 13. OpenAPI documentation

django-ninja auto-generate:

- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI JSON**: `/api/openapi.json`

Tài liệu này là nguồn sự thật chính thức cho API.

## 14. SDK / Client libraries

Khuyến nghị provide:

- **Python**: `pmketoan-python` (PyPI)
- **JavaScript**: `@pmketoan/js` (npm)
- **PHP**: `pmketoan/php` (Composer)

SDK tự sinh từ OpenAPI spec (dùng `openapi-generator`).

---

**Tiếp theo**: [02. Endpoints Master Data](./02-endpoints-master-data.md)
