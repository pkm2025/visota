# 05. Bảng tính giá tồn kho (Inventory Costing Engine)

> Chi tiết logic và bảng phụ trợ để tính giá xuất kho theo 3 phương pháp.

## 1. Tổng quan 3 phương pháp

| Phương pháp | DB column | Khi nào tính | Đặc điểm |
|-------------|-----------|-------------|---------|
| Trung bình tháng (default) | `weighted_avg` | Cuối tháng | Đơn giản, không sợ âm tạm thời |
| Trung bình di động | `moving_avg` | Sau mỗi lần nhập | Chính xác từng thời điểm, phải có tồn |
| FIFO | `fifo` | Tại thời điểm xuất | Theo dõi chi tiết theo lô |

## 2. Bảng phụ trợ (additional)

```sql
-- Tracking FIFO movements
CREATE TABLE stock_fifo_consumption (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    issue_line_id BIGINT UNSIGNED NOT NULL COMMENT 'Reference to stock_voucher_line of issue',
    receipt_lot_id BIGINT UNSIGNED NOT NULL COMMENT 'Reference to stock_lot',
    quantity DECIMAL(18,4) NOT NULL,
    unit_cost DECIMAL(20,4),
    amount DECIMAL(20,4),
    consumed_at DATETIME,
    INDEX idx_issue (issue_line_id),
    INDEX idx_lot (receipt_lot_id)
) ENGINE=InnoDB CHARSET=utf8mb4;

-- Snapshot cost history (cho moving average)
CREATE TABLE stock_cost_snapshot (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    snapshot_date DATE NOT NULL,
    avg_cost DECIMAL(20,4),
    quantity DECIMAL(18,4),
    amount DECIMAL(20,4),
    UNIQUE KEY uk_snapshot (product_id, warehouse_id, snapshot_date),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

-- Costing job log
CREATE TABLE costing_job (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    period CHAR(7) NOT NULL,
    cost_method ENUM('weighted_avg','moving_avg','fifo'),
    started_at DATETIME,
    completed_at DATETIME,
    status ENUM('queued','running','completed','failed') DEFAULT 'queued',
    error_message TEXT,
    triggered_by BIGINT UNSIGNED,
    products_processed INT,
    vouchers_updated INT,
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 3. Thuật toán

### 3.1. Trung bình tháng (cuối tháng)

```python
def calculate_weighted_avg(company_id, period):
    """
    Chạy vào cuối tháng, tính lại toàn bộ unit_cost cho các stock_ledger trong tháng
    """
    products = get_active_products(company_id)
    
    for product in products:
        warehouses = get_active_warehouses(company_id, product)
        
        for wh in warehouses:
            opening_qty, opening_amt = get_stock_opening(product, wh, period)
            
            # Tổng nhập trong tháng
            receipts = get_period_receipts(product, wh, period)
            total_receipt_qty = sum(r.quantity for r in receipts)
            total_receipt_amt = sum(r.amount for r in receipts)
            
            # Đơn giá bình quân
            if opening_qty + total_receipt_qty > 0:
                avg_cost = (opening_amt + total_receipt_amt) / (opening_qty + total_receipt_qty)
            else:
                avg_cost = 0
            
            # Cập nhật lại toàn bộ stock_ledger trong tháng
            update_ledger_costs(product, wh, period, avg_cost)
            
            # Cập nhật stock_card
            update_stock_card(product, wh, period, avg_cost)
```

### 3.2. Trung bình di động (real-time sau mỗi nhập)

```python
def update_moving_avg_after_receipt(receipt_line):
    """
    Gọi sau khi một phiếu nhập được lưu
    """
    product = receipt_line.product
    wh = receipt_line.warehouse
    new_qty = receipt_line.quantity
    new_amt = receipt_line.quantity * receipt_line.unit_cost
    
    # Lấy avg_cost hiện tại
    current_qty, current_amt = get_current_stock(product, wh)
    
    # Tính avg_cost mới
    new_total_qty = current_qty + new_qty
    new_total_amt = current_amt + new_amt
    
    if new_total_qty > 0:
        new_avg_cost = new_total_amt / new_total_qty
    else:
        new_avg_cost = 0
    
    # Cập nhật vào stock_cost_snapshot
    save_cost_snapshot(product, wh, today, new_avg_cost, new_total_qty, new_total_amt)

def get_issue_cost_moving_avg(issue_line):
    """
    Lấy unit_cost cho phiếu xuất
    """
    snapshot = get_latest_snapshot(issue_line.product, issue_line.warehouse)
    return snapshot.avg_cost if snapshot else 0
```

### 3.3. FIFO

```python
def allocate_fifo_consumption(issue_line):
    """
    Khi phiếu xuất được tạo, lấy từ các lot cũ nhất
    """
    product = issue_line.product
    wh = issue_line.warehouse
    qty_to_issue = issue_line.quantity
    
    # Lấy các lot còn hàng, sắp xếp theo receipt_date ASC
    available_lots = (
        StockLot.objects
        .filter(product=product, warehouse=wh, current_quantity__gt=0)
        .order_by('lot_date', 'id')
    )
    
    consumptions = []
    qty_remaining = qty_to_issue
    
    for lot in available_lots:
        if qty_remaining <= 0:
            break
        
        take_qty = min(qty_remaining, lot.current_quantity)
        consumptions.append({
            'lot': lot,
            'quantity': take_qty,
            'unit_cost': lot.unit_cost,
            'amount': take_qty * lot.unit_cost
        })
        
        lot.current_quantity -= take_qty
        lot.save()
        
        qty_remaining -= take_qty
    
    if qty_remaining > 0:
        raise InsufficientStockError(f"Short {qty_remaining} {product.unit}")
    
    # Tạo stock_fifo_consumption records
    create_fifo_consumptions(issue_line, consumptions)
    
    # Trả về tổng amount và avg_cost
    total_amount = sum(c['amount'] for c in consumptions)
    avg_cost = total_amount / qty_to_issue
    return total_amount, avg_cost
```

## 4. Workflow tính giá cuối tháng

```
1. Cron trigger vào đêm cuối tháng:
   - 23:00 ngày cuối tháng: chạy weighted_avg calculation
   - 02:00 ngày đầu tháng sau: chạy các báo cáo

2. Process:
   - Bước 1: Khóa phiếu nhập/xuất của tháng (chỉ cho phép xem)
   - Bước 2: Tính avg_cost cho từng (product, warehouse)
   - Bước 3: Update stock_ledger.unit_cost và amount
   - Bước 4: Update stock_voucher_line.unit_cost và amount
   - Bước 5: Update stock_card với avg_cost mới
   - Bước 6: Tính lại voucher GL liên quan (N632/C156)
   - Bước 7: Mở khóa phiếu nhập/xuất (nhưng đã cố định giá)

3. Idempotent:
   - Có thể chạy lại nhiều lần
   - Tính lại từ đầu mỗi lần
   - Lưu costing_job log để audit
```

## 5. Validation

```python
def validate_stock_after_costing(company_id, period):
    """
    Kiểm tra tính nhất quán sau khi tính giá
    """
    products = get_active_products(company_id)
    
    for product in products:
        for wh in get_warehouses(product):
            # Tổng amount trong ledger = closing_amount trong stock_card
            ledger_total = sum(
                line.amount for line in 
                StockLedger.objects.filter(product=product, warehouse=wh, period=period)
            )
            
            card = StockCard.objects.get(product=product, warehouse=wh, period=period)
            
            expected_closing = card.opening_amount + card.receipt_amount - card.issue_amount
            
            if abs(ledger_total - expected_closing) > 0.01:
                raise InconsistencyError(
                    f"Mismatch for {product.code}/{wh.code}: "
                    f"ledger={ledger_total}, card={expected_closing}"
                )
```

## 6. Use case: chạy tính giá cuối tháng

### UC-A: Tính giá tháng 06/2026

1. Kế toán vào Tồn kho → Tính giá → Chọn "Trung bình tháng"
2. Chọn kỳ: 06/2026
3. Click "Calculate"
4. Hệ thống:
   - Tạo costing_job với status='running'
   - Lọc tất cả product có phát sinh trong tháng
   - Tính avg_cost cho từng (product, warehouse)
   - Update stock_ledger, stock_card
   - Update voucher GL liên quan
5. Hiển thị báo cáo:
   - Số sản phẩm đã xử lý
   - Số voucher đã update
   - Errors (nếu có)
6. Status='completed'

## 7. Phân quyền

- `inventory.cost.view` — xem cấu hình cost method
- `inventory.cost.calculate` — chạy tính giá cuối kỳ
- `inventory.cost.adjust` — điều chỉnh giá thủ công (cần phê duyệt)

---

**Tiếp theo**: [Kiến trúc kỹ thuật →](../05-kien-truc-ky-thuat/01-kien-truc-tong-the.md)
