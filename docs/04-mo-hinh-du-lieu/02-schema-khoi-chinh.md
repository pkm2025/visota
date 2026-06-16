# 02. Schema khối chính (Master Data Schema)

> Đặc tả SQL DDL cho các bảng master data (danh mục) theo MariaDB 11.x.

## 1. Quản lý công ty & người dùng

```sql
-- Bảng company: đơn vị/tenant
CREATE TABLE company (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    tax_code VARCHAR(20),
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    legal_representative VARCHAR(255),
    chief_accountant VARCHAR(255),
    accounting_regime ENUM('tt133', 'tt200', 'q48', 'q15') DEFAULT 'tt133',
    default_currency CHAR(3) DEFAULT 'VND',
    fiscal_year_start_month TINYINT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_company_tax (tax_code)
) ENGINE=InnoDB CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng user
CREATE TABLE `user` (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    last_login_at DATETIME,
    last_login_ip VARCHAR(50),
    failed_login_count INT DEFAULT 0,
    locked_until DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE role (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE permission (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(100) NOT NULL UNIQUE,
    module VARCHAR(50),
    name VARCHAR(255),
    description TEXT
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE role_permission (
    role_id BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    scope_json JSON,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE user_company_role (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    company_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    valid_from DATE,
    valid_to DATE,
    UNIQUE KEY uk_user_company_role (user_id, company_id, role_id),
    FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES role(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 2. Fiscal Year & Tham số

```sql
CREATE TABLE fiscal_year (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    fiscal_year SMALLINT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('open', 'closing', 'closed') DEFAULT 'open',
    locked_periods JSON,
    carry_forward_to SMALLINT,
    UNIQUE KEY uk_company_fy (company_id, fiscal_year),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE system_parameter (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NULL,
    param_code VARCHAR(100) NOT NULL,
    param_value TEXT,
    data_type ENUM('string','int','decimal','bool','json','date') DEFAULT 'string',
    description TEXT,
    UNIQUE KEY uk_company_param (company_id, param_code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 3. Chart of Accounts

```sql
CREATE TABLE chart_of_accounts (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    account_code VARCHAR(20) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_name_en VARCHAR(255),
    short_name VARCHAR(100),
    parent_account_code VARCHAR(20),
    currency_code CHAR(3) DEFAULT 'VND',
    is_posting_account BOOLEAN DEFAULT FALSE,
    is_general_ledger_account BOOLEAN DEFAULT FALSE,
    account_level TINYINT,
    account_type_id BIGINT UNSIGNED,
    is_customer_account BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    allows_object_code BOOLEAN DEFAULT FALSE,
    allows_cost_center BOOLEAN DEFAULT FALSE,
    allows_project BOOLEAN DEFAULT FALSE,
    allows_production_order BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT UNSIGNED,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by BIGINT UNSIGNED,
    UNIQUE KEY uk_company_account (company_id, account_code),
    INDEX idx_parent (parent_account_code),
    INDEX idx_active (company_id, is_active),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE account_type (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code TINYINT NOT NULL,
    name VARCHAR(100),
    balance_type ENUM('debit','credit') NOT NULL,
    category ENUM('asset','liability','equity','revenue','expense','other') NOT NULL
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 4. Cost Center & Department

```sql
CREATE TABLE cost_center (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_id BIGINT UNSIGNED,
    gl_account VARCHAR(20),
    manager_id BIGINT UNSIGNED,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 5. Customer & Vendor

```sql
CREATE TABLE customer (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    short_name VARCHAR(100),
    tax_code VARCHAR(20),
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    customer_group_id BIGINT UNSIGNED,
    sales_staff_id BIGINT UNSIGNED,
    payment_terms VARCHAR(100),
    credit_limit DECIMAL(20,4) DEFAULT 0,
    currency_code CHAR(3) DEFAULT 'VND',
    default_vat_rate DECIMAL(6,4) DEFAULT 0.10,
    gl_account_receivable VARCHAR(20) DEFAULT '131',
    bank_account_no VARCHAR(50),
    bank_id VARCHAR(20),
    contact_person VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT UNSIGNED,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by BIGINT UNSIGNED,
    UNIQUE KEY uk_company_code (company_id, code),
    INDEX idx_tax (tax_code),
    INDEX idx_name (company_id, name),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE customer_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_group_id BIGINT UNSIGNED,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_group_id) REFERENCES customer_group(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

-- vendor, vendor_group tương tự (đổi 'customer' → 'vendor', 'receivable' → 'payable')
CREATE TABLE vendor (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    tax_code VARCHAR(20),
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    vendor_group_id BIGINT UNSIGNED,
    payment_terms VARCHAR(100),
    currency_code CHAR(3) DEFAULT 'VND',
    gl_account_payable VARCHAR(20) DEFAULT '331',
    is_supplier BOOLEAN DEFAULT TRUE,
    is_contractor BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    INDEX idx_tax (tax_code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 6. Product & Warehouse

```sql
CREATE TABLE product (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(500) NOT NULL,
    name_en VARCHAR(500),
    barcode VARCHAR(50),
    product_type ENUM('raw_material','semi_finished','finished','goods','supplies','tool','service') NOT NULL,
    unit_id VARCHAR(20),
    group_id BIGINT UNSIGNED,
    weight DECIMAL(18,4),
    volume DECIMAL(18,4),
    cost_method ENUM('weighted_avg','moving_avg','fifo') DEFAULT 'weighted_avg',
    gl_account_inv VARCHAR(20),
    gl_account_cogs VARCHAR(20),
    gl_account_revenue VARCHAR(20),
    default_vat_rate DECIMAL(6,4) DEFAULT 0.10,
    default_unit_price DECIMAL(20,4),
    min_stock DECIMAL(18,4),
    max_stock DECIMAL(18,4),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    UNIQUE KEY uk_company_code (company_id, code),
    INDEX idx_barcode (barcode),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE product_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_group_id BIGINT UNSIGNED,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE warehouse (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    type ENUM('material','finished','transit','virtual') DEFAULT 'material',
    manager_id BIGINT UNSIGNED,
    address TEXT,
    gl_account VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE unit_of_measure (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100),
    decimal_places TINYINT DEFAULT 0
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE unit_conversion (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NOT NULL,
    from_unit VARCHAR(20),
    to_unit VARCHAR(20),
    conversion_factor DECIMAL(18,6),
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 7. Currency & Exchange Rate

```sql
CREATE TABLE currency (
    code CHAR(3) PRIMARY KEY,
    name VARCHAR(100),
    symbol VARCHAR(10),
    decimal_places TINYINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE exchange_rate (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    currency_code CHAR(3) NOT NULL,
    rate_date DATE NOT NULL,
    rate DECIMAL(18,6) NOT NULL,
    rate_type ENUM('buying','selling','transfer','average') DEFAULT 'average',
    UNIQUE KEY uk_rate (company_id, currency_code, rate_date, rate_type),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (currency_code) REFERENCES currency(code)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 8. Sales Staff

```sql
CREATE TABLE sales_staff (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    employee_id BIGINT UNSIGNED,
    commission_rate DECIMAL(6,4) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 9. Tax Rate

```sql
CREATE TABLE tax_rate (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    rate DECIMAL(6,4),
    rate_type ENUM('vat_output','vat_input','special_consumption','import','export') NOT NULL,
    effective_from DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_code_type (code, rate_type)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 10. Bank Account

```sql
CREATE TABLE bank_account (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    bank_id VARCHAR(20),
    bank_name VARCHAR(255),
    branch VARCHAR(255),
    account_no VARCHAR(50),
    account_holder VARCHAR(255),
    currency_code CHAR(3) DEFAULT 'VND',
    gl_account VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_account (company_id, account_no),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 11. Loan Agreement

```sql
CREATE TABLE loan_agreement (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    loan_no VARCHAR(50) NOT NULL,
    loan_type ENUM('short_term','long_term') NOT NULL,
    lender_type ENUM('bank','partner','other') DEFAULT 'bank',
    lender_id VARCHAR(50),
    lender_name VARCHAR(255),
    principal DECIMAL(20,4) NOT NULL,
    currency_code CHAR(3) DEFAULT 'VND',
    interest_rate DECIMAL(8,4),
    interest_rate_type ENUM('fixed','floating') DEFAULT 'fixed',
    disbursement_date DATE,
    maturity_date DATE,
    payment_schedule JSON,
    gl_account_liability VARCHAR(20),
    status ENUM('active','closed','overdue') DEFAULT 'active',
    UNIQUE KEY uk_company_loan (company_id, loan_no),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 12. Department & Position (HR)

```sql
CREATE TABLE hr_department (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_id BIGINT UNSIGNED,
    manager_id BIGINT UNSIGNED,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_position (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50),
    name VARCHAR(255),
    level INT
) ENGINE=InnoDB CHARSET=utf8mb4;
```

---

**Tiếp theo**: [03. Schema chứng từ](./03-schema-chung-tu.md)
