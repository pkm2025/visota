# 04. Schema danh mục từ điển (Master Data)

> Các bảng danh mục phụ trợ: loại TK, nhóm KH/NCC/SP, lý do, nguồn vốn...

## 1. Account types & Account Groups

```sql
CREATE TABLE account_type (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code TINYINT NOT NULL UNIQUE,
    name VARCHAR(100),
    balance_type ENUM('debit','credit') NOT NULL,
    category ENUM('asset','liability','equity','revenue','expense','other_income','other_expense','off_balance') NOT NULL,
    description TEXT
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 2. Customer / Vendor Groups

```sql
CREATE TABLE customer_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_group_id BIGINT UNSIGNED,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_group_id) REFERENCES customer_group(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE vendor_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_group_id BIGINT UNSIGNED,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_group_id) REFERENCES vendor_group(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 3. Product Groups

```sql
CREATE TABLE product_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    parent_group_id BIGINT UNSIGNED,
    product_category ENUM('raw_material','semi_finished','finished','goods','supplies','tool','service'),
    default_gl_account_inv VARCHAR(20),
    default_gl_account_cogs VARCHAR(20),
    default_gl_account_revenue VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_group_id) REFERENCES product_group(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 4. Sales Price (Giá bán)

```sql
CREATE TABLE sales_price (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    customer_group_id BIGINT UNSIGNED NULL,
    sales_staff_id BIGINT UNSIGNED NULL,
    currency_code CHAR(3) DEFAULT 'VND',
    min_quantity DECIMAL(18,4) DEFAULT 1,
    unit_price DECIMAL(20,4) NOT NULL,
    effective_from DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    INDEX idx_product (product_id),
    INDEX idx_effective (product_id, effective_from, effective_to),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE CASCADE
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 5. Tax Rate Group

```sql
CREATE TABLE tax_rate_group (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    direction ENUM('output','input') NOT NULL,
    default_tax_rate_id BIGINT UNSIGNED NOT NULL,
    description TEXT,
    UNIQUE KEY uk_company_code_direction (company_id, code, direction),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (default_tax_rate_id) REFERENCES tax_rate(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 6. Asset Categories (Loại / Nhóm / Phân nhóm TS)

```sql
CREATE TABLE asset_category (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    level ENUM('type','group','subgroup') NOT NULL,
    parent_id BIGINT UNSIGNED,
    is_for_tool BOOLEAN DEFAULT FALSE COMMENT 'TRUE=CCDC, FALSE=TSCĐ',
    default_gl_account VARCHAR(20),
    default_depreciation_rate DECIMAL(8,4),
    default_useful_life_months INT,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id),
    FOREIGN KEY (parent_id) REFERENCES asset_category(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE asset_using_department (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    cost_center_id BIGINT UNSIGNED,
    default_expense_account VARCHAR(20),
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE asset_reason (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    type ENUM('increase','decrease') NOT NULL,
    name VARCHAR(255),
    description TEXT
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE capital_source (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    description TEXT
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 7. Workshop (Phân xưởng)

```sql
CREATE TABLE workshop (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    cost_center_id BIGINT UNSIGNED,
    manager_id BIGINT UNSIGNED,
    cost_account_material VARCHAR(20) DEFAULT '621',
    cost_account_labor VARCHAR(20) DEFAULT '622',
    cost_account_overhead VARCHAR(20) DEFAULT '627',
    wip_account VARCHAR(20) DEFAULT '154',
    finished_account VARCHAR(20) DEFAULT '155',
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 8. Shift & Time Clock (Tiền lương)

```sql
CREATE TABLE shift (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_minutes INT DEFAULT 60,
    late_grace_minutes INT DEFAULT 5,
    early_leave_grace_minutes INT DEFAULT 5,
    is_night_shift BOOLEAN DEFAULT FALSE,
    is_weekend BOOLEAN DEFAULT FALSE,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE standard_workday (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    period CHAR(7) NOT NULL,
    standard_days DECIMAL(5,2) DEFAULT 22,
    standard_hours DECIMAL(5,2) DEFAULT 176,
    UNIQUE KEY uk_company_period (company_id, period),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE time_clock_machine (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    model VARCHAR(100),
    location VARCHAR(255),
    api_endpoint VARCHAR(500),
    api_key VARCHAR(255),
    last_sync DATETIME,
    UNIQUE KEY uk_company_code (company_id, code),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE public_holiday (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    holiday_date DATE NOT NULL,
    holiday_name VARCHAR(255),
    is_paid BOOLEAN DEFAULT TRUE,
    INDEX idx_date (company_id, holiday_date),
    FOREIGN KEY (company_id) REFERENCES company(id)
) ENGINE=InnoDB CHARSET=utf8mb4;
```

## 9. HR Master Data (~35 dictionary tables)

```sql
CREATE TABLE hr_position (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    level INT
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_title (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_labor_category (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_education_level (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    rank INT
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_ethnicity (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_religion (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_nationality (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code CHAR(2) NOT NULL UNIQUE COMMENT 'ISO 3166-1 alpha-2',
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_province (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    region VARCHAR(50)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_district (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    province_id BIGINT UNSIGNED,
    FOREIGN KEY (province_id) REFERENCES hr_province(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_ward (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    district_id BIGINT UNSIGNED,
    FOREIGN KEY (district_id) REFERENCES hr_district(id)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_marital_status (
    id TINYINT PRIMARY KEY,
    code VARCHAR(20),
    name VARCHAR(100)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_gender (
    id TINYINT PRIMARY KEY,
    code VARCHAR(20),
    name VARCHAR(50)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_health_status (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_contract_status (
    id TINYINT PRIMARY KEY,
    code VARCHAR(20),
    name VARCHAR(100)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_computer_skill_level (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_language (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code CHAR(3) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_social_role (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_healthcare_facility (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    address TEXT,
    province_id BIGINT UNSIGNED
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_certificate (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    issuer VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_reward_discipline_type (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    type ENUM('reward','discipline')
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_specialization (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_training_type (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_ability (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_family_relation_type (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255)
) ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE hr_policy (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255),
    description TEXT
) ENGINE=InnoDB CHARSET=utf8mb4;
```

---

**Tiếp theo**: [05. Bảng tính giá tồn kho](./05-bang-tinh-gia-ton-kho.md)
