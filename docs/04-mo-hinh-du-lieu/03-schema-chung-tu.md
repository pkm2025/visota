# 03. Schema chứng từ (Voucher Schema)

> Bảng trung tâm nghiệp vụ kế toán: voucher, voucher_line, balance.

## 1. Accounting Voucher & Lines

```sql
CREATE TABLE accounting_voucher (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    fiscal_year SMALLINT NOT NULL,
    period TINYINT NOT NULL,
    voucher_no VARCHAR(50) NOT NULL,
    voucher_type VARCHAR(50) NOT NULL COMMENT 'journal, cash_receipt, cash_payment, sales_invoice, etc',
    voucher_date DATE NOT NULL,
    posting_date DATE,
    book_code VARCHAR(20),
    status TINYINT DEFAULT 2 COMMENT '0=draft, 1=subsidiary, 2=ledger, 3=locked',
    currency_code CHAR(3) DEFAULT 'VND',
    exchange_rate DECIMAL(18,6) DEFAULT 1.0,
    total_fc DECIMAL(20,4) DEFAULT 0,
    total_vnd DECIMAL(20,4) DEFAULT 0,
    description TEXT,
    source VARCHAR(20) DEFAULT 'manual' COMMENT 'manual, closing, depreciation, allocation, costing, payroll',
    source_reference_id BIGINT UNSIGNED,
    is_reversed BOOLEAN DEFAULT FALSE,
    reversal_voucher_id BIGINT UNSIGNED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT UNSIGNED,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by BIGINT UNSIGNED,
    deleted_at TIMESTAMP NULL,
    deleted_by BIGINT UNSIGNED NULL,
    version INT DEFAULT 1,
    UNIQUE KEY uk_voucher_no (company_id, fiscal_year, voucher_type, voucher_no),
    INDEX idx_date (company_id, voucher_date),
    INDEX idx_period (company_id, fiscal_year, period, status),
    INDEX idx_type_date (company_id, voucher_type, voucher_date),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4
PARTITION BY RANGE (fiscal_year) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p2027 VALUES LESS THAN (2028),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

CREATE TABLE voucher_line (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    voucher_id BIGINT UNSIGNED NOT NULL,
    line_no INT NOT NULL,
    account_code VARCHAR(20) NOT NULL,
    object_type ENUM('customer','vendor','employee','bank','other') NULL,
    object_code VARCHAR(50),
    object_name VARCHAR(255),
    debit_fc DECIMAL(20,4) DEFAULT 0,
    credit_fc DECIMAL(20,4) DEFAULT 0,
    debit_vnd DECIMAL(20,4) DEFAULT 0,
    credit_vnd DECIMAL(20,4) DEFAULT 0,
    description TEXT,
    cost_center_id BIGINT UNSIGNED,
    project_code VARCHAR(50),
    contract_code VARCHAR(50),
    production_order_code VARCHAR(50),
    statistical_qty DECIMAL(18,4),
    statistical_unit VARCHAR(20),
    INDEX idx_voucher (voucher_id),
    INDEX idx_account (account_code),
    INDEX idx_object (object_type, object_code),
    FOREIGN KEY (voucher_id) REFERENCES accounting_voucher(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 2. Account Opening Balance & Period Balance

```sql
-- Số dư đầu kỳ (khởi tạo từ đầu hoặc carry-forward)
CREATE TABLE account_opening_balance (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    fiscal_year SMALLINT NOT NULL,
    account_code VARCHAR(20) NOT NULL,
    object_type ENUM('customer','vendor','employee','bank','other') NULL,
    object_code VARCHAR(50),
    debit_opening DECIMAL(20,4) DEFAULT 0,
    credit_opening DECIMAL(20,4) DEFAULT 0,
    foreign_debit DECIMAL(20,4) DEFAULT 0,
    foreign_credit DECIMAL(20,4) DEFAULT 0,
    UNIQUE KEY uk_balance (company_id, fiscal_year, account_code, object_type, object_code),
    INDEX idx_account (company_id, fiscal_year, account_code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

-- Số dư và phát sinh theo kỳ (cashed, rebuild được)
CREATE TABLE account_period_balance (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    fiscal_year SMALLINT NOT NULL,
    period TINYINT NOT NULL,
    account_code VARCHAR(20) NOT NULL,
    object_type ENUM('customer','vendor','employee','bank','other') NULL,
    object_code VARCHAR(50),
    opening_debit DECIMAL(20,4) DEFAULT 0,
    opening_credit DECIMAL(20,4) DEFAULT 0,
    period_debit DECIMAL(20,4) DEFAULT 0,
    period_credit DECIMAL(20,4) DEFAULT 0,
    closing_debit DECIMAL(20,4) DEFAULT 0,
    closing_credit DECIMAL(20,4) DEFAULT 0,
    opening_debit_fc DECIMAL(20,4) DEFAULT 0,
    opening_credit_fc DECIMAL(20,4) DEFAULT 0,
    period_debit_fc DECIMAL(20,4) DEFAULT 0,
    period_credit_fc DECIMAL(20,4) DEFAULT 0,
    closing_debit_fc DECIMAL(20,4) DEFAULT 0,
    closing_credit_fc DECIMAL(20,4) DEFAULT 0,
    last_transaction_date DATE,
    transaction_count INT DEFAULT 0,
    UNIQUE KEY uk_balance (company_id, fiscal_year, period, account_code, object_type, object_code),
    INDEX idx_period (company_id, fiscal_year, period),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 3. Closing Templates

```sql
CREATE TABLE closing_template (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    sequence INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE closing_template_line (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    template_id BIGINT UNSIGNED NOT NULL,
    line_no INT,
    side ENUM('credit','debit') NOT NULL,
    account_pattern VARCHAR(100) NOT NULL COMMENT 'e.g. 511%, 632%',
    object_pattern VARCHAR(100),
    target_account VARCHAR(20) NOT NULL,
    target_object_code VARCHAR(50),
    description VARCHAR(255),
    FOREIGN KEY (template_id) REFERENCES closing_template(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE closing_run (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    fiscal_year SMALLINT,
    period TINYINT,
    template_id BIGINT UNSIGNED,
    voucher_id BIGINT UNSIGNED COMMENT 'Generated voucher',
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_by BIGINT UNSIGNED,
    status ENUM('success','failed') DEFAULT 'success',
    notes TEXT,
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 4. Year-end Carry Forward

```sql
CREATE TABLE year_end_carry_forward (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    from_fiscal_year SMALLINT NOT NULL,
    to_fiscal_year SMALLINT NOT NULL,
    carried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    carried_by BIGINT UNSIGNED,
    status ENUM('in_progress','completed','failed') DEFAULT 'completed',
    accounts_count INT,
    customers_count INT,
    vendors_count INT,
    products_count INT,
    assets_count INT,
    log_file_path VARCHAR(500),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 5. Cash Voucher (Phiếu thu/chi)

```sql
CREATE TABLE cash_voucher (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    voucher_type ENUM('cash_receipt','cash_payment','bank_receipt','bank_payment') NOT NULL,
    voucher_no VARCHAR(50) NOT NULL,
    voucher_date DATE NOT NULL,
    amount DECIMAL(20,4) NOT NULL,
    currency_code CHAR(3) DEFAULT 'VND',
    exchange_rate DECIMAL(18,6) DEFAULT 1.0,
    amount_vnd DECIMAL(20,4),
    payer_payee VARCHAR(255),
    address TEXT,
    reason TEXT,
    payment_method ENUM('cash','transfer','check') DEFAULT 'cash',
    bank_account_id BIGINT UNSIGNED,
    gl_voucher_id BIGINT UNSIGNED,
    related_invoice_id BIGINT UNSIGNED,
    status TINYINT DEFAULT 2,
    UNIQUE KEY uk_voucher (company_id, voucher_type, voucher_no),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (gl_voucher_id) REFERENCES accounting_voucher(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 6. Sales Invoice

```sql
CREATE TABLE sales_invoice (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    invoice_no VARCHAR(50) NOT NULL,
    invoice_date DATE NOT NULL,
    invoice_type ENUM('goods','service','export','other') DEFAULT 'goods',
    customer_id BIGINT UNSIGNED,
    sales_staff_id BIGINT UNSIGNED,
    contract_no VARCHAR(50),
    delivery_note_no VARCHAR(50),
    currency_code CHAR(3) DEFAULT 'VND',
    exchange_rate DECIMAL(18,6) DEFAULT 1.0,
    subtotal DECIMAL(20,4),
    discount_amount DECIMAL(20,4) DEFAULT 0,
    vat_amount DECIMAL(20,4) DEFAULT 0,
    total_amount DECIMAL(20,4),
    total_vnd DECIMAL(20,4),
    payment_status ENUM('unpaid','partial','paid') DEFAULT 'unpaid',
    paid_amount DECIMAL(20,4) DEFAULT 0,
    einvoice_id BIGINT UNSIGNED,
    gl_voucher_id BIGINT UNSIGNED,
    stock_voucher_id BIGINT UNSIGNED,
    status TINYINT DEFAULT 2,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT UNSIGNED,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by BIGINT UNSIGNED,
    UNIQUE KEY uk_invoice (company_id, invoice_type, invoice_no),
    INDEX idx_date_customer (company_id, invoice_date, customer_id),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (gl_voucher_id) REFERENCES accounting_voucher(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE sales_invoice_line (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    invoice_id BIGINT UNSIGNED NOT NULL,
    line_no INT NOT NULL,
    product_id BIGINT UNSIGNED,
    description TEXT,
    quantity DECIMAL(18,4),
    unit_id VARCHAR(20),
    unit_price DECIMAL(20,4),
    discount_rate DECIMAL(6,4) DEFAULT 0,
    discount_amount DECIMAL(20,4) DEFAULT 0,
    amount_before_vat DECIMAL(20,4),
    vat_rate DECIMAL(6,4),
    vat_amount DECIMAL(20,4),
    amount DECIMAL(20,4),
    revenue_account VARCHAR(20) DEFAULT '5111',
    vat_account VARCHAR(20) DEFAULT '33311',
    inventory_account VARCHAR(20),
    cost_account VARCHAR(20) DEFAULT '632',
    INDEX idx_invoice (invoice_id),
    FOREIGN KEY (invoice_id) REFERENCES sales_invoice(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 7. Purchase Invoice (tương tự Sales Invoice)

```sql
CREATE TABLE purchase_invoice (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    invoice_no VARCHAR(50) NOT NULL,
    invoice_date DATE NOT NULL,
    invoice_type ENUM('goods','service','import','direct_issue') DEFAULT 'goods',
    vendor_id BIGINT UNSIGNED,
    po_no VARCHAR(50),
    warehouse_id BIGINT UNSIGNED,
    currency_code CHAR(3) DEFAULT 'VND',
    exchange_rate DECIMAL(18,6) DEFAULT 1.0,
    subtotal DECIMAL(20,4),
    vat_amount DECIMAL(20,4) DEFAULT 0,
    import_tax DECIMAL(20,4) DEFAULT 0,
    excise_tax DECIMAL(20,4) DEFAULT 0,
    total_amount DECIMAL(20,4),
    total_vnd DECIMAL(20,4),
    paid_amount DECIMAL(20,4) DEFAULT 0,
    gl_voucher_id BIGINT UNSIGNED,
    stock_voucher_id BIGINT UNSIGNED,
    einvoice_id BIGINT UNSIGNED,
    status TINYINT DEFAULT 2,
    UNIQUE KEY uk_invoice (company_id, invoice_type, invoice_no),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE purchase_invoice_line (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    invoice_id BIGINT UNSIGNED NOT NULL,
    line_no INT NOT NULL,
    product_id BIGINT UNSIGNED,
    description TEXT,
    quantity DECIMAL(18,4),
    unit_id VARCHAR(20),
    unit_price DECIMAL(20,4),
    discount_amount DECIMAL(20,4) DEFAULT 0,
    amount_before_vat DECIMAL(20,4),
    vat_rate DECIMAL(6,4),
    vat_amount DECIMAL(20,4),
    amount DECIMAL(20,4),
    inventory_account VARCHAR(20) DEFAULT '156',
    vat_account VARCHAR(20) DEFAULT '1331',
    FOREIGN KEY (invoice_id) REFERENCES purchase_invoice(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 8. E-Invoice

```sql
CREATE TABLE einvoice (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    direction ENUM('output','input') NOT NULL,
    einvoice_no VARCHAR(50),
    serial_no VARCHAR(20),
    template_code VARCHAR(20),
    issue_date DATETIME,
    seller_tax_code VARCHAR(20),
    seller_name VARCHAR(255),
    seller_address TEXT,
    buyer_tax_code VARCHAR(20),
    buyer_name VARCHAR(255),
    buyer_address TEXT,
    amount DECIMAL(20,4),
    vat_amount DECIMAL(20,4),
    total_amount DECIMAL(20,4),
    einvoice_status ENUM('pending','issued','cancelled','replaced','adjusted') DEFAULT 'pending',
    provider ENUM('bkav','viettel','mobifone','tct','other') DEFAULT 'tct',
    xml_data LONGTEXT,
    pdf_url VARCHAR(500),
    related_invoice_id BIGINT UNSIGNED,
    fetched_at DATETIME,
    INDEX idx_status (company_id, einvoice_status),
    INDEX idx_issue_date (company_id, issue_date),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 9. Stock Voucher & Stock Ledger

```sql
CREATE TABLE stock_voucher (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    voucher_type ENUM('receipt','issue','transfer') NOT NULL,
    voucher_no VARCHAR(50) NOT NULL,
    voucher_date DATE NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    to_warehouse_id BIGINT UNSIGNED,
    related_voucher_id BIGINT UNSIGNED,
    related_voucher_type VARCHAR(50),
    reason TEXT,
    total_amount DECIMAL(20,4),
    gl_voucher_id BIGINT UNSIGNED,
    status TINYINT DEFAULT 2,
    UNIQUE KEY uk_voucher (company_id, voucher_type, voucher_no),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE stock_voucher_line (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    voucher_id BIGINT UNSIGNED NOT NULL,
    line_no INT,
    product_id BIGINT UNSIGNED NOT NULL,
    lot_id BIGINT UNSIGNED,
    description TEXT,
    quantity DECIMAL(18,4) NOT NULL,
    unit_id VARCHAR(20),
    unit_cost DECIMAL(20,4),
    amount DECIMAL(20,4),
    gl_account_inv VARCHAR(20),
    gl_account_offset VARCHAR(20),
    object_code VARCHAR(50),
    INDEX idx_product (product_id),
    FOREIGN KEY (voucher_id) REFERENCES stock_voucher(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE stock_lot (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    lot_code VARCHAR(50),
    lot_date DATE,
    expiry_date DATE,
    initial_quantity DECIMAL(18,4),
    current_quantity DECIMAL(18,4),
    unit_cost DECIMAL(20,4),
    INDEX idx_product_lot (product_id, lot_code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE stock_ledger (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    transaction_date DATETIME NOT NULL,
    transaction_type ENUM('receipt','issue','adjust') NOT NULL,
    lot_id BIGINT UNSIGNED,
    quantity DECIMAL(18,4) NOT NULL,
    unit_cost DECIMAL(20,4),
    amount DECIMAL(20,4),
    related_voucher_id BIGINT UNSIGNED,
    balance_quantity DECIMAL(18,4),
    balance_amount DECIMAL(20,4),
    INDEX idx_product_wh_date (product_id, warehouse_id, transaction_date),
    INDEX idx_company_date (company_id, transaction_date),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(transaction_date)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p2027 VALUES LESS THAN (2028),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

CREATE TABLE stock_card (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    warehouse_id BIGINT UNSIGNED NOT NULL,
    period CHAR(7) NOT NULL COMMENT 'YYYY-MM',
    opening_quantity DECIMAL(18,4) DEFAULT 0,
    opening_amount DECIMAL(20,4) DEFAULT 0,
    receipt_quantity DECIMAL(18,4) DEFAULT 0,
    receipt_amount DECIMAL(20,4) DEFAULT 0,
    issue_quantity DECIMAL(18,4) DEFAULT 0,
    issue_amount DECIMAL(20,4) DEFAULT 0,
    closing_quantity DECIMAL(18,4) DEFAULT 0,
    closing_amount DECIMAL(20,4) DEFAULT 0,
    avg_cost DECIMAL(20,4),
    UNIQUE KEY uk_card (company_id, product_id, warehouse_id, period),
    INDEX idx_period (company_id, period),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 10. Fixed Asset & Depreciation

```sql
CREATE TABLE fixed_asset (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    asset_code VARCHAR(50) NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    asset_type_id BIGINT UNSIGNED,
    asset_group_id BIGINT UNSIGNED,
    using_dept_id BIGINT UNSIGNED,
    capital_source_id BIGINT UNSIGNED,
    gl_account VARCHAR(20) DEFAULT '2111',
    depreciation_account VARCHAR(20) DEFAULT '2141',
    expense_account VARCHAR(20) DEFAULT '642',
    original_cost DECIMAL(20,4) NOT NULL,
    currency_code CHAR(3) DEFAULT 'VND',
    depreciation_method ENUM('straight_line','declining_balance','units_of_production') DEFAULT 'straight_line',
    depreciation_rate DECIMAL(8,4),
    useful_life_months INT,
    start_date DATE NOT NULL,
    end_date DATE,
    salvage_value DECIMAL(20,4) DEFAULT 0,
    accumulated_depreciation DECIMAL(20,4) DEFAULT 0,
    net_book_value DECIMAL(20,4),
    status ENUM('draft','active','fully_depreciated','disposed') DEFAULT 'active',
    production_capacity DECIMAL(18,4),
    UNIQUE KEY uk_company_asset (company_id, asset_code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE asset_depreciation (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    asset_id BIGINT UNSIGNED NOT NULL,
    period CHAR(7) NOT NULL,
    depreciation_amount DECIMAL(20,4) NOT NULL,
    accumulated_depreciation_end DECIMAL(20,4),
    net_book_value_end DECIMAL(20,4),
    gl_voucher_id BIGINT UNSIGNED,
    posted_at DATETIME,
    UNIQUE KEY uk_asset_period (asset_id, period),
    FOREIGN KEY (asset_id) REFERENCES fixed_asset(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

---

**Tiếp theo**: [04. Schema danh mục (master)](./04-schema-danh-muc.md)
