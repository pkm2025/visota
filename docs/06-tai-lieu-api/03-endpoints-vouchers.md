# 03. Endpoints - Chứng từ

> API cho các loại chứng từ nghiệp vụ.

## 1. Accounting Voucher (Phiếu kế toán)

### GET /api/v1/vouchers/

List voucher với filter.

**Query params**:
- `voucher_type`: journal, cash_receipt, sales_invoice, ...
- `voucher_date_from`, `voucher_date_to`
- `posting_date_from`, `posting_date_to`
- `status`: 0/1/2/3
- `currency_code`
- `fiscal_year`, `period`
- `account_code`: filter voucher có line với TK này
- `object_code`: filter theo đối tượng
- `source`: manual, closing, depreciation, ...
- `search`: search theo voucher_no, description
- `ordering`: -voucher_date, voucher_no, -created_at
- `page`, `page_size`

**Response**:
```json
{
  "data": [
    {
      "id": 123,
      "voucher_no": "BC0001",
      "voucher_type": "sales_invoice",
      "voucher_date": "2026-06-15",
      "posting_date": "2026-06-15",
      "book_code": "BC",
      "status": 2,
      "status_display": "Đã ghi sổ",
      "currency_code": "VND",
      "exchange_rate": 1.0,
      "total_fc": 110000000,
      "total_vnd": 110000000,
      "description": "Bán hàng cho KH A",
      "source": "manual",
      "line_count": 3,
      "created_at": "2026-06-15T10:30:00Z",
      "created_by": {
        "id": 1,
        "username": "admin",
        "full_name": "Admin User"
      },
      "updated_at": "2026-06-15T10:30:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 150
  }
}
```

### POST /api/v1/vouchers/

Tạo voucher mới.

**Request**:
```json
{
  "voucher_type": "journal",
  "voucher_no": "BC0001",
  "voucher_date": "2026-06-15",
  "description": "Bán hàng cho KH A",
  "currency_code": "VND",
  "exchange_rate": 1.0,
  "lines": [
    {
      "account_code": "131",
      "object_type": "customer",
      "object_code": "KH001",
      "debit_vnd": 110000000,
      "credit_vnd": 0,
      "description": "Phải thu KH A"
    },
    {
      "account_code": "5111",
      "debit_vnd": 0,
      "credit_vnd": 100000000,
      "description": "Doanh thu bán hàng"
    },
    {
      "account_code": "33311",
      "debit_vnd": 0,
      "credit_vnd": 10000000,
      "description": "VAT 10%"
    }
  ],
  "status": 2
}
```

**Response (201 Created)**:
```json
{
  "data": {
    "id": 123,
    "voucher_no": "BC0001",
    "voucher_type": "journal",
    "voucher_date": "2026-06-15",
    "status": 2,
    "total_vnd": 110000000,
    "lines": [...]
  }
}
```

### GET /api/v1/vouchers/{id}/

Chi tiết voucher với đầy đủ lines.

### PATCH /api/v1/vouchers/{id}/

Cập nhật voucher (chỉ khi status ≤ 1).

### DELETE /api/v1/vouchers/{id}/

Xóa voucher (chỉ khi status = 0).

### POST /api/v1/vouchers/{id}/post/

Post voucher → status=2.

### POST /api/v1/vouchers/{id}/unpost/

Unpost → status=0.

### POST /api/v1/vouchers/{id}/lock/

Lock voucher → status=3.

### POST /api/v1/vouchers/{id}/reverse/

Tạo reversal voucher.

**Request**:
```json
{
  "reason": "Sai đối tượng",
  "reverse_date": "2026-06-20"
}
```

### GET /api/v1/vouchers/{id}/audit-log/

Lịch sử thay đổi.

### POST /api/v1/vouchers/import/

Import từ Excel.

### GET /api/v1/vouchers/export/

Export ra Excel/PDF.

## 2. Sales Invoices

### GET /api/v1/sales-invoices/

**Query params**:
- `customer_id`
- `invoice_type`: goods, service, export
- `invoice_date_from`, `invoice_date_to`
- `payment_status`: unpaid, partial, paid
- `einvoice_status`: pending, issued, cancelled

### POST /api/v1/sales-invoices/

```json
{
  "invoice_no": "BC0001",
  "invoice_date": "2026-06-15",
  "invoice_type": "goods",
  "customer_id": 1,
  "sales_staff_id": 3,
  "currency_code": "VND",
  "exchange_rate": 1.0,
  "lines": [
    {
      "product_id": 5,
      "description": "Pin AA",
      "quantity": 1000,
      "unit_id": "CAI",
      "unit_price": 100000,
      "discount_rate": 0,
      "vat_rate": 0.10,
      "revenue_account": "5111",
      "cost_account": "632",
      "inventory_account": "156"
    }
  ],
  "auto_post_stock": true,
  "auto_issue_einvoice": false
}
```

### POST /api/v1/sales-invoices/{id}/issue-einvoice/

Phát hành HĐĐT qua BKAV.

### POST /api/v1/sales-invoices/{id}/cancel-einvoice/

Hủy HĐĐT đã phát hành.

### POST /api/v1/sales-invoices/{id}/adjust/

Tạo hóa đơn điều chỉnh.

### POST /api/v1/sales-invoices/{id}/replace/

Tạo hóa đơn thay thế.

### GET /api/v1/sales-invoices/{id}/print/

Tải PDF hóa đơn.

### POST /api/v1/sales-invoices/{id}/payments/

Ghi nhận thanh toán.

```json
{
  "amount": 50000000,
  "payment_date": "2026-06-20",
  "payment_method": "transfer",
  "cash_voucher_id": 456
}
```

## 3. Purchase Invoices

Tương tự Sales Invoices với các điểm khác:
- `vendor_id` thay vì customer_id
- `warehouse_id` (kho nhập)
- Có thêm `import_tax`, `excise_tax` cho nhập khẩu

### POST /api/v1/purchase-invoices/{id}/allocate-expenses/

Phân bổ chi phí mua hàng.

```json
{
  "expense_amount": 5000000,
  "expense_type": "freight",
  "allocation_method": "by_value"
}
```

## 4. Stock Vouchers

### GET /api/v1/stock-vouchers/

**Query params**:
- `voucher_type`: receipt, issue, transfer
- `warehouse_id`
- `product_id`
- `from_date`, `to_date`

### POST /api/v1/stock-vouchers/

```json
{
  "voucher_type": "issue",
  "voucher_no": "PX0001",
  "voucher_date": "2026-06-15",
  "warehouse_id": 1,
  "reason": "Xuất bán",
  "lines": [
    {
      "product_id": 5,
      "quantity": 100,
      "unit_id": "CAI",
      "gl_account_inv": "156",
      "gl_account_offset": "632"
    }
  ]
}
```

Hệ thống tự tính `unit_cost` theo cost_method của product.

### POST /api/v1/stock-vouchers/calculate-cost/

Trigger tính giá cuối kỳ (async).

```json
{
  "period": "2026-06",
  "cost_method": "weighted_avg"
}
```

Returns: job_id để poll.

## 5. Cash Vouchers (Phiếu thu/chi)

### GET /api/v1/cash-vouchers/

### POST /api/v1/cash-vouchers/

```json
{
  "voucher_type": "cash_receipt",
  "voucher_no": "PT0001",
  "voucher_date": "2026-06-15",
  "amount": 50000000,
  "currency_code": "VND",
  "payer_payee": "Công ty ABC",
  "address": "Số 1 Đường A",
  "reason": "Khách thanh toán HĐ BC0001",
  "payment_method": "cash",
  "gl_lines": [
    {
      "account_code": "111",
      "debit_vnd": 50000000
    },
    {
      "account_code": "131",
      "object_type": "customer",
      "object_code": "KH001",
      "credit_vnd": 50000000
    }
  ],
  "allocate_to_invoices": [123, 124]
}
```

## 6. Fixed Assets

### GET /api/v1/fixed-assets/

### POST /api/v1/fixed-assets/

```json
{
  "asset_code": "TSCD001",
  "asset_name": "Xe Toyota Vios",
  "asset_type_id": 1,
  "asset_group_id": 5,
  "using_dept_id": 3,
  "gl_account": "2113",
  "depreciation_account": "2141",
  "expense_account": "642",
  "original_cost": 500000000,
  "currency_code": "VND",
  "depreciation_method": "straight_line",
  "useful_life_months": 60,
  "start_date": "2026-01-01",
  "salvage_value": 50000000
}
```

### POST /api/v1/fixed-assets/{id}/depreciate/

Tính khấu hao định kỳ.

```json
{
  "period": "2026-06"
}
```

### POST /api/v1/fixed-assets/{id}/transfer/

Điều chuyển TSCĐ.

```json
{
  "to_dept_id": 4,
  "effective_date": "2026-07-01",
  "new_expense_account": "641"
}
```

### POST /api/v1/fixed-assets/{id}/dispose/

Thanh lý TSCĐ.

```json
{
  "disposal_date": "2026-06-30",
  "reason_id": 5,
  "disposal_value": 50000000,
  "gl_voucher_no": "TL0001"
}
```

## 7. Period Closing

### POST /api/v1/period-closing/run-closing/

Thực thi kết chuyển cuối kỳ (async).

```json
{
  "fiscal_year": 2026,
  "period": 6,
  "template_codes": ["KC_DT", "KC_CP", "KC_TNDN"]
}
```

### POST /api/v1/period-closing/run-allocation/

Phân bổ chi phí chờ phân bổ.

### POST /api/v1/period-closing/lock-period/

Khóa kỳ.

### POST /api/v1/period-closing/unlock-period/

Mở khóa kỳ (cần quyền đặc biệt).

### POST /api/v1/period-closing/year-end-carry-forward/

Chuyển số dư năm sau (async).

## 8. Year-end Operations

### GET /api/v1/year-end/status/

Trạng thái carry-forward.

### GET /api/v1/year-end/preview/

Preview số dư sẽ chuyển.

### POST /api/v1/year-end/execute/

Execute (async).

## 9. E-Invoice Operations

### GET /api/v1/e-invoices/

List HĐĐT.

### POST /api/v1/e-invoices/pull-from-tct/

Pull HĐĐT đầu vào từ Tổng cục Thuế.

```json
{
  "from_date": "2026-06-01",
  "to_date": "2026-06-30"
}
```

### POST /api/v1/e-invoices/{id}/match/

Match với phiếu nhập mua.

```json
{
  "purchase_invoice_id": 789
}
```

### GET /api/v1/e-invoices/{id}/xml/

Tải XML raw.

## 10. Common voucher patterns

### 10.1. Validate before save

```http
POST /api/v1/vouchers/validate/
{ ... voucher data ... }

HTTP/1.1 200 OK
{
  "valid": true,
  "warnings": [
    "Tài khoản 131 cần có object_code"
  ]
}
```

### 10.2. Copy voucher

```http
POST /api/v1/vouchers/{id}/copy/

HTTP/1.1 201 Created
{ ... new voucher with same data ... }
```

### 10.3. Bulk post

```http
POST /api/v1/vouchers/bulk-post/
{
  "ids": [1, 2, 3, 4, 5]
}
```

### 10.4. Voucher templates

```http
GET /api/v1/voucher-templates/
POST /api/v1/voucher-templates/
POST /api/v1/voucher-templates/{id}/apply/
```

---

**Tiếp theo**: [04. Endpoints Reports](./04-endpoints-reports.md)
