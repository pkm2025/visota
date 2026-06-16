# 02. Endpoints - Master Data

> Chi tiết API cho các entity master data.

## 1. Chart of Accounts

### GET /api/v1/chart-of-accounts/

List accounts, hỗ trợ filter theo parent, level.

**Query params**:
- `parent_code`: filter theo TK mẹ
- `level`: filter theo cấp (1, 2, 3, ...)
- `is_active`: true/false
- `is_posting_account`: true/false (chỉ TK được hạch toán)
- `search`: search theo code hoặc name

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "account_code": "111",
      "account_name": "Tiền mặt",
      "parent_account_code": null,
      "account_level": 1,
      "account_type": "asset",
      "balance_type": "debit",
      "currency_code": "VND",
      "is_posting_account": false,
      "is_general_ledger_account": true,
      "allows_object_code": false,
      "allows_cost_center": false,
      "allows_project": false,
      "is_active": true,
      "children_count": 2
    }
  ]
}
```

### POST /api/v1/chart-of-accounts/

Tạo mới TK.

**Request**:
```json
{
  "account_code": "11211",
  "account_name": "TGNH VCB Hà Nội",
  "parent_account_code": "1121",
  "currency_code": "VND",
  "is_posting_account": true,
  "is_general_ledger_account": true,
  "allows_object_code": false,
  "allows_cost_center": false
}
```

### GET /api/v1/chart-of-accounts/tree/

Trả về cấu trúc cây (nested).

**Response**:
```json
{
  "data": [
    {
      "account_code": "1",
      "account_name": "Tài sản ngắn hạn",
      "children": [
        {
          "account_code": "111",
          "account_name": "Tiền mặt",
          "children": [
            { "account_code": "1111", "account_name": "Tiền Việt Nam", "children": [] },
            { "account_code": "1112", "account_name": "Ngoại tệ", "children": [] }
          ]
        }
      ]
    }
  ]
}
```

### POST /api/v1/chart-of-accounts/import/

Import từ Excel/CSV.

**Request**: multipart/form-data với file `.xlsx`

**Response**:
```json
{
  "imported": 120,
  "skipped": 5,
  "errors": [
    { "row": 12, "error": "Duplicate account_code: 1111" }
  ]
}
```

## 2. Customers

### GET /api/v1/customers/

**Query params**:
- `search`: search theo code/name/tax_code
- `customer_group_id`: filter theo nhóm
- `sales_staff_id`: filter theo NV phụ trách
- `is_active`: true/false
- `has_balance`: chỉ KH có công nợ
- `ordering`: code, name, -created_at, ...

**Response**:
```json
{
  "data": [
    {
      "id": 1,
      "code": "KH001",
      "name": "Công ty ABC",
      "name_en": "ABC Co., Ltd",
      "tax_code": "0101234567",
      "address": "Số 1 Đường A, Hà Nội",
      "phone": "0241234567",
      "email": "contact@abc.com",
      "customer_group_id": 5,
      "customer_group_name": "Khách VIP",
      "sales_staff_id": 3,
      "payment_terms": "30 days",
      "credit_limit": 1000000000,
      "currency_code": "VND",
      "gl_account_receivable": "131",
      "current_balance": 50000000,
      "is_active": true,
      "created_at": "2026-01-15T10:30:00Z",
      "updated_at": "2026-06-15T08:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 150
  }
}
```

### POST /api/v1/customers/

```json
{
  "code": "KH001",
  "name": "Công ty ABC",
  "tax_code": "0101234567",
  "address": "Số 1 Đường A, Hà Nội",
  "phone": "0241234567",
  "email": "contact@abc.com",
  "customer_group_id": 5,
  "payment_terms": "30 days",
  "credit_limit": 1000000000,
  "currency_code": "VND"
}
```

### GET /api/v1/customers/{id}/balance/

Real-time customer balance.

**Response**:
```json
{
  "data": {
    "customer_id": 1,
    "opening_balance": 50000000,
    "debit_period": 100000000,
    "credit_period": 80000000,
    "closing_balance": 70000000,
    "currency_code": "VND",
    "as_of_date": "2026-06-15",
    "aging": {
      "current": 50000000,
      "1-30": 10000000,
      "31-60": 5000000,
      "61-90": 3000000,
      "over_90": 2000000
    }
  }
}
```

### GET /api/v1/customers/{id}/aging/

AR aging chi tiết.

**Response**:
```json
{
  "data": {
    "customer_id": 1,
    "as_of_date": "2026-06-15",
    "buckets": [
      {
        "bucket": "current",
        "amount": 50000000,
        "invoice_count": 3,
        "invoices": [
          { "invoice_id": 123, "invoice_no": "BC0001", "invoice_date": "2026-06-10", "amount": 20000000 },
          ...
        ]
      },
      ...
    ]
  }
}
```

## 3. Vendors

Tương tự Customers, endpoint: `/api/v1/vendors/`

### Đặc biệt:

- `is_supplier`: boolean (cung cấp HH)
- `is_contractor`: boolean (cung cấp dịch vụ)
- `gl_account_payable`: default '331'

### GET /api/v1/vendors/{id}/balance/

AP balance, tương tự customer balance.

## 4. Products

### GET /api/v1/products/

**Query params**:
- `product_type`: raw_material, finished, goods, ...
- `group_id`: filter theo nhóm
- `barcode`: search theo barcode
- `is_active`: true/false
- `low_stock`: chỉ HH tồn dưới min_stock

### GET /api/v1/products/{id}/stock/

Tồn kho hiện tại theo warehouse.

**Response**:
```json
{
  "data": {
    "product_id": 1,
    "total_quantity": 1500,
    "total_amount": 16500000,
    "avg_cost": 11000,
    "by_warehouse": [
      {
        "warehouse_id": 1,
        "warehouse_code": "KHO_HN",
        "quantity": 1000,
        "amount": 11000000,
        "avg_cost": 11000
      },
      {
        "warehouse_id": 2,
        "warehouse_code": "KHO_HCM",
        "quantity": 500,
        "amount": 5500000,
        "avg_cost": 11000
      }
    ]
  }
}
```

### GET /api/v1/products/{id}/cost-history/

Lịch sử đơn giá (cho moving average).

## 5. Warehouses

```http
GET /api/v1/warehouses/
POST /api/v1/warehouses/
GET /api/v1/warehouses/{id}/
PATCH /api/v1/warehouses/{id}/
```

### GET /api/v1/warehouses/{id}/inventory/

Tồn kho toàn bộ product trong kho.

## 6. Currencies & Exchange Rates

### GET /api/v1/currencies/

```json
{
  "data": [
    { "code": "VND", "name": "Vietnamese Dong", "symbol": "₫", "decimal_places": 0 },
    { "code": "USD", "name": "US Dollar", "symbol": "$", "decimal_places": 2 },
    { "code": "EUR", "name": "Euro", "symbol": "€", "decimal_places": 2 }
  ]
}
```

### GET /api/v1/exchange-rates/

```http
GET /api/v1/exchange-rates/?currency_code=USD&date=2026-06-15
```

```json
{
  "data": [
    {
      "currency_code": "USD",
      "rate_date": "2026-06-15",
      "rate": 24500,
      "rate_type": "average"
    }
  ]
}
```

### POST /api/v1/exchange-rates/

Update rate hàng ngày (có thể auto-import từ ngân hàng).

## 7. Cost Centers (Bộ phận hạch toán)

```http
GET /api/v1/cost-centers/
POST /api/v1/cost-centers/
```

```json
{
  "code": "BP_BH",
  "name": "Bộ phận Bán hàng",
  "parent_id": null,
  "gl_account": "641",
  "manager_id": 5
}
```

## 8. Bank Accounts

```http
GET /api/v1/bank-accounts/
POST /api/v1/bank-accounts/
```

```json
{
  "bank_id": "VCB",
  "bank_name": "Vietcombank",
  "branch": "Hà Nội",
  "account_no": "0011001234567",
  "account_holder": "Công ty ABC",
  "currency_code": "VND",
  "gl_account": "11211"
}
```

## 9. Loan Agreements

```http
GET /api/v1/loan-agreements/
POST /api/v1/loan-agreements/
GET /api/v1/loan-agreements/{id}/schedule/
```

Lịch trả nợ (principal + interest).

## 10. Sales Staff

```http
GET /api/v1/sales-staff/
POST /api/v1/sales-staff/
```

## 11. Tax Rates

```http
GET /api/v1/tax-rates/?rate_type=vat_output
```

```json
{
  "data": [
    { "code": "VAT0", "name": "VAT 0%", "rate": 0.0, "rate_type": "vat_output" },
    { "code": "VAT5", "name": "VAT 5%", "rate": 0.05, "rate_type": "vat_output" },
    { "code": "VAT8", "name": "VAT 8%", "rate": 0.08, "rate_type": "vat_output" },
    { "code": "VAT10", "name": "VAT 10%", "rate": 0.10, "rate_type": "vat_output" },
    { "code": "VATN", "name": "Không chịu thuế", "rate": -1, "rate_type": "vat_output" }
  ]
}
```

## 12. Asset Categories

```http
GET /api/v1/asset-categories/?level=group&is_for_tool=false
```

Tree structure với type/group/subgroup.

## 13. HR Master Data

Rất nhiều endpoints cho ~35 danh mục HR:

```http
GET /api/v1/hr/departments/
GET /api/v1/hr/positions/
GET /api/v1/hr/titles/
GET /api/v1/hr/provinces/
GET /api/v1/hr/districts/?province_id=1
GET /api/v1/hr/wards/?district_id=1
GET /api/v1/hr/ethnicities/
GET /api/v1/hr/religions/
GET /api/v1/hr/education-levels/
...
```

Tất cả đều có CRUD endpoints tương tự.

## 14. Common patterns

### 14.1. Bulk activate/deactivate

```http
POST /api/v1/customers/bulk-activate/
{
  "ids": [1, 2, 3, 4],
  "is_active": true
}
```

### 14.2. Merge duplicates

```http
POST /api/v1/customers/merge/
{
  "source_ids": [2, 3],
  "target_id": 1,
  "merge_strategy": "prefer_target"
}
```

### 14.3. Export

```http
GET /api/v1/customers/export/?format=xlsx&filter=...
```

Returns binary file.

---

**Tiếp theo**: [03. Endpoints Vouchers](./03-endpoints-vouchers.md)
