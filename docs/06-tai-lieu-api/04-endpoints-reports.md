# 04. Endpoints - Reports

> API cho các loại báo cáo tài chính, thuế, quản trị.

## 1. Trial Balance (Bảng cân đối tài khoản)

### GET /api/v1/reports/trial-balance/

**Query params**:
- `fiscal_year`: required (vd: 2026)
- `from_period`: 1-12 (mặc định 1)
- `to_period`: 1-12 (mặc định 12)
- `account_pattern`: filter theo mã TK (vd: `1%` cho tất cả TK loại 1)
- `level`: filter theo cấp TK
- `show_zero_balance`: true/false (mặc định false)
- `format`: json (default), xlsx, pdf, csv

**Response (JSON)**:
```json
{
  "data": {
    "company": {
      "code": "PKM",
      "name": "Công ty PKM",
      "tax_code": "0101218690"
    },
    "fiscal_year": 2026,
    "from_period": 1,
    "to_period": 6,
    "generated_at": "2026-06-16T15:30:00Z",
    "totals": {
      "opening_debit": 2300000000,
      "opening_credit": 2300000000,
      "period_debit": 1030000000,
      "period_credit": 1030000000,
      "closing_debit": 2545000000,
      "closing_credit": 2545000000
    },
    "rows": [
      {
        "account_code": "111",
        "account_name": "Tiền mặt",
        "opening_debit": 100000000,
        "opening_credit": 0,
        "period_debit": 50000000,
        "period_credit": 30000000,
        "closing_debit": 120000000,
        "closing_credit": 0
      },
      ...
    ]
  },
  "meta": {
    "request_id": "req_abc123"
  }
}
```

**Response (Excel)**:
Returns binary file với `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

## 2. Balance Sheet (B01-DN)

### GET /api/v1/reports/balance-sheet/

**Query params**:
- `fiscal_year`: required
- `period`: 1-12 (mặc định 12)
- `regime`: tt133, tt200 (mặc định theo company config)
- `comparison`: 'previous_year' (so sánh với năm trước)
- `format`: json, xlsx, pdf

**Response**:
```json
{
  "data": {
    "company": {...},
    "fiscal_year": 2026,
    "period": 6,
    "as_of_date": "2026-06-30",
    "assets": {
      "total": 1825000000,
      "sections": [
        {
          "code": "A",
          "name": "TÀI SẢN",
          "subsections": [
            {
              "code": "I",
              "name": "Tài sản ngắn hạn",
              "amount": 950000000,
              "items": [
                {
                  "code": "I.1",
                  "name": "Tiền và tương đương tiền",
                  "amount": 120000000,
                  "formula": "=111+112+113"
                },
                {
                  "code": "I.3",
                  "name": "Các khoản phải thu",
                  "amount": 250000000
                },
                ...
              ]
            },
            {
              "code": "II",
              "name": "Tài sản dài hạn",
              "amount": 875000000,
              "items": [...]
            }
          ]
        }
      ]
    },
    "liabilities_and_equity": {
      "total": 1825000000,
      "sections": [
        {
          "code": "B",
          "name": "NGUỒN VỐN",
          "subsections": [
            {
              "code": "C",
              "name": "Nợ phải trả",
              "amount": 930000000,
              "items": [...]
            },
            {
              "code": "D",
              "name": "Vốn chủ sở hữu",
              "amount": 895000000,
              "items": [...]
            }
          ]
        }
      ]
    },
    "validation": {
      "balanced": true,
      "assets_total": 1825000000,
      "liabilities_equity_total": 1825000000,
      "difference": 0
    }
  }
}
```

## 3. P&L Statement (B02-DN)

### GET /api/v1/reports/profit-and-loss/

**Query params**:
- `fiscal_year`
- `from_period`, `to_period`
- `comparison`: 'previous_year', 'previous_period'
- `format`: json, xlsx, pdf

**Response**:
```json
{
  "data": {
    "company": {...},
    "fiscal_year": 2026,
    "from_period": 1,
    "to_period": 6,
    "rows": [
      { "code": "1", "name": "Doanh thu", "amount": 350000000, "account": "511" },
      { "code": "2", "name": "Các khoản giảm trừ DT", "amount": 0, "account": "521" },
      { "code": "3", "name": "Doanh thu thuần", "amount": 350000000, "formula": "=1-2" },
      { "code": "4", "name": "Giá vốn hàng bán", "amount": 150000000, "account": "632" },
      { "code": "5", "name": "Lợi nhuận gộp", "amount": 200000000, "formula": "=3-4" },
      { "code": "6", "name": "DT HĐTC", "amount": 0, "account": "515" },
      { "code": "7", "name": "CP Tài chính", "amount": 20000000, "account": "635" },
      { "code": "8", "name": "CP bán hàng", "amount": 30000000, "account": "641" },
      { "code": "9", "name": "CP QLDN", "amount": 75000000, "account": "642" },
      { "code": "10", "name": "LN từ HĐKD", "amount": 75000000, "formula": "=5+6-7-8-9" },
      { "code": "11", "name": "Thu nhập khác", "amount": 0, "account": "711" },
      { "code": "12", "name": "Chi phí khác", "amount": 0, "account": "811" },
      { "code": "13", "name": "LN khác", "amount": 0, "formula": "=11-12" },
      { "code": "14", "name": "Tổng LN trước thuế", "amount": 75000000, "formula": "=10+13" },
      { "code": "15", "name": "CP thuế TNDN", "amount": 15000000, "account": "821" },
      { "code": "16", "name": "LN sau thuế", "amount": 60000000, "formula": "=14-15" }
    ]
  }
}
```

## 4. Cash Flow Statement (B03-DN)

### GET /api/v1/reports/cash-flow/?method=direct

**Query params**:
- `method`: direct, indirect
- `fiscal_year`, `from_period`, `to_period`

**Response (Direct method)**:
```json
{
  "data": {
    "method": "direct",
    "sections": [
      {
        "code": "I",
        "name": "Dòng tiền từ HĐKD",
        "items": [
          { "code": "1", "name": "Tiền thu từ KH", "amount": 280000000 },
          { "code": "2", "name": "Tiền trả NCC", "amount": -200000000 },
          { "code": "3", "name": "Tiền thu khác HĐKD", "amount": 0 },
          { "code": "4", "name": "Tiền chi khác HĐKD", "amount": -105000000 }
        ],
        "net_cash": -25000000
      },
      {
        "code": "II",
        "name": "Dòng tiền từ HĐ đầu tư",
        "net_cash": 0
      },
      {
        "code": "III",
        "name": "Dòng tiền từ HĐ tài chính",
        "net_cash": 0
      }
    ],
    "net_change": -25000000,
    "opening_cash": 145000000,
    "closing_cash": 120000000
  }
}
```

## 5. Account Detail (Sổ cái / Sổ chi tiết)

### GET /api/v1/reports/account-ledger/

**Query params**:
- `account_code`: required (vd: `131`)
- `object_type`, `object_code`: optional cho sổ chi tiết đối tượng
- `from_date`, `to_date`
- `format`: json, xlsx, pdf

**Response**:
```json
{
  "data": {
    "account_code": "131",
    "account_name": "Phải thu khách hàng",
    "object_type": "customer",
    "object_code": "KH001",
    "object_name": "Công ty ABC",
    "from_date": "2026-01-01",
    "to_date": "2026-06-30",
    "opening_debit": 50000000,
    "opening_credit": 0,
    "transactions": [
      {
        "voucher_id": 123,
        "voucher_no": "BC0001",
        "voucher_date": "2026-06-15",
        "voucher_type": "sales_invoice",
        "description": "Bán hàng",
        "debit": 110000000,
        "credit": 0,
        "balance": 160000000
      },
      {
        "voucher_id": 456,
        "voucher_no": "PT0001",
        "voucher_date": "2026-06-20",
        "voucher_type": "cash_receipt",
        "description": "KH thanh toán",
        "debit": 0,
        "credit": 50000000,
        "balance": 110000000
      }
    ],
    "closing_debit": 110000000,
    "closing_credit": 0
  }
}
```

## 6. AR Aging

### GET /api/v1/reports/ar-aging/

**Query params**:
- `as_of_date`: mặc định hôm nay
- `customer_id`: optional
- `bucket_size`: 30 (default), 60, 90

**Response**:
```json
{
  "data": {
    "as_of_date": "2026-06-30",
    "total": 1200000000,
    "buckets": [
      {
        "name": "0-30 days",
        "amount": 500000000,
        "percentage": 41.67,
        "customer_count": 12
      },
      {
        "name": "31-60 days",
        "amount": 300000000,
        "percentage": 25,
        "customer_count": 8
      },
      ...
    ],
    "by_customer": [
      {
        "customer_id": 1,
        "customer_code": "KH001",
        "customer_name": "Công ty ABC",
        "total": 50000000,
        "buckets": {
          "0-30": 50000000,
          "31-60": 0,
          "61-90": 0,
          "over_90": 0
        }
      }
    ]
  }
}
```

## 7. AP Aging

Tương tự AR Aging, endpoint: `/api/v1/reports/ap-aging/`

## 8. Stock Card (Thẻ kho)

### GET /api/v1/reports/stock-card/

**Query params**:
- `product_id`: required
- `warehouse_id`: optional (default = all)
- `from_date`, `to_date`
- `lot_id`: optional

**Response**:
```json
{
  "data": {
    "product": {
      "id": 5,
      "code": "SP001",
      "name": "Pin AA",
      "unit": "CAI"
    },
    "warehouse": {
      "id": 1,
      "code": "KHO_HN",
      "name": "Kho Hà Nội"
    },
    "period": "2026-06",
    "opening": {
      "quantity": 1000,
      "amount": 10000000,
      "avg_cost": 10000
    },
    "transactions": [
      {
        "date": "2026-06-05",
        "voucher_no": "PN01",
        "type": "receipt",
        "description": "Nhập từ NCC",
        "in_quantity": 500,
        "in_amount": 5500000,
        "out_quantity": 0,
        "out_amount": 0,
        "balance_quantity": 1500,
        "balance_amount": 15500000
      },
      {
        "date": "2026-06-10",
        "voucher_no": "PX01",
        "type": "issue",
        "description": "Xuất bán",
        "in_quantity": 0,
        "in_amount": 0,
        "out_quantity": 200,
        "out_amount": 2066667,
        "balance_quantity": 1300,
        "balance_amount": 13433333
      }
    ],
    "closing": {
      "quantity": 1300,
      "amount": 13433333,
      "avg_cost": 10333.33
    }
  }
}
```

## 9. VAT Return

### GET /api/v1/reports/vat-return/

**Query params**:
- `return_period`: required (vd: `2026-06`)
- `return_type`: monthly, quarterly

**Response**:
```json
{
  "data": {
    "company": {...},
    "return_period": "2026-06",
    "return_type": "monthly",
    "indicators": {
      "21": { "description": "GT HHDV bán ra chịu thuế GTGT", "amount": 1000000000 },
      "22": { "description": "Thuế GTGT của HHDV bán ra", "amount": 100000000 },
      "23": { "description": "GT HHDV bán ra không chịu thuế", "amount": 0 },
      "24": { "description": "HHDV chịu TS 0%", "amount": 0 },
      "25": { "description": "HHDV chịu TS 5%", "amount": 100000000 },
      "26": { "description": "HHDV chịu TS 8%", "amount": 200000000 },
      "27": { "description": "HHDV chịu TS 10%", "amount": 700000000 },
      "28": { "description": "GT HHDV mua vào được KT", "amount": 600000000 },
      "29": { "description": "Thuế GTGT HHDV mua vào được KT", "amount": 60000000 },
      "40": { "description": "Thuế GTGT đầu ra", "amount": 100000000 },
      "41": { "description": "Thuế GTGT đầu vào được KT", "amount": 60000000 },
      "42": { "description": "Thuế GTGT đầu vào chuyển từ kỳ trước", "amount": 5000000 },
      "45": { "description": "Thuế GTGT phải nộp trong kỳ", "amount": 35000000 }
    },
    "output_breakdown": {
      "0%": { "base": 0, "vat": 0, "invoice_count": 0 },
      "5%": { "base": 100000000, "vat": 5000000, "invoice_count": 5 },
      "8%": { "base": 200000000, "vat": 16000000, "invoice_count": 10 },
      "10%": { "base": 700000000, "vat": 70000000, "invoice_count": 35 }
    },
    "input_breakdown": {...}
  }
}
```

### GET /api/v1/reports/vat-return/output-listing/

Bảng kê đầu ra 01-1/GTGT.

### GET /api/v1/reports/vat-return/input-listing/

Bảng kê đầu vào 01-2/GTGT.

### GET /api/v1/reports/vat-return/export-xml/

XML cho nộp thuế điện tử.

## 10. Asset Depreciation Schedule

### GET /api/v1/reports/asset-depreciation/

**Query params**:
- `period`: required (vd: `2026-06`)
- `using_dept_id`: optional
- `asset_group_id`: optional

**Response**:
```json
{
  "data": {
    "period": "2026-06",
    "assets": [
      {
        "asset_id": 1,
        "asset_code": "TSCD001",
        "asset_name": "Xe Toyota Vios",
        "original_cost": 500000000,
        "accumulated_opening": 50000000,
        "depreciation_period": 8000000,
        "accumulated_closing": 58000000,
        "net_book_value": 442000000,
        "expense_account": "642"
      }
    ],
    "totals": {
      "original_cost": 2000000000,
      "depreciation_period": 30000000,
      "net_book_value": 1450000000
    }
  }
}
```

## 11. Payroll Reports

### GET /api/v1/reports/attendance-summary/

Bảng chấm công tổng hợp tháng.

### GET /api/v1/reports/payroll/

Bảng lương kỳ.

## 12. Generic Report API

### POST /api/v1/reports/generate/

Tạo báo cáo async (cho báo cáo nặng).

```json
{
  "report_code": "trial_balance",
  "parameters": {
    "fiscal_year": 2026,
    "from_period": 1,
    "to_period": 6
  },
  "format": "xlsx"
}
```

Returns:
```json
{
  "data": {
    "job_id": "rpt_xyz789",
    "status": "queued",
    "estimated_duration_seconds": 30
  }
}
```

### GET /api/v1/reports/jobs/{job_id}/

Poll status.

### GET /api/v1/reports/jobs/{job_id}/download/

Download kết quả khi completed.

## 13. Saved Reports

### POST /api/v1/reports/saved/

Lưu cấu hình report để tái sử dụng.

```json
{
  "name": "BCĐTK Quý 2/2026",
  "report_code": "trial_balance",
  "parameters": {
    "fiscal_year": 2026,
    "from_period": 4,
    "to_period": 6
  }
}
```

### GET /api/v1/reports/saved/

List saved reports.

### POST /api/v1/reports/saved/{id}/run/

Run saved report.

## 14. Report Scheduling

### POST /api/v1/report-schedules/

Lên lịch chạy report tự động.

```json
{
  "report_code": "trial_balance",
  "parameters": {...},
  "cron": "0 0 1 * *",
  "format": "pdf",
  "email_to": ["cfo@example.com"],
  "is_active": true
}
```

---

**Tiếp theo**: [Mẫu giao diện →](../07-mau-giao-dien/01-layout-overview.md)
