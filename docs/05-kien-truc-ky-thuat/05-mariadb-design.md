# 05. Thiết kế MariaDB

> Quyết định thiết kế database cho MariaDB 11.x: storage engine, charset, partitioning, indexing.

## 1. Version & Engine

| Component | Version | Lý do |
|-----------|--------|------|
| MariaDB | 11.4 LTS (hoặc 11.x mới nhất) | LTS, performance, features |
| Storage engine | InnoDB (default) | Transactional, ACID, row-level locking |
| Charset | `utf8mb4` | Hỗ trợ đầy đủ tiếng Việt + emoji |
| Collation | `utf8mb4_unicode_ci` | Sắp xếp đúng tiếng Việt |
| Time zone | UTC (server), Asia/Ho_Chi_Minh (display) | Tránh ambiguity |

## 2. Server config khuyến nghị

```ini
# /etc/mysql/mariadb.conf.d/50-server.cnf

[mysqld]
# Basic
user = mysql
pid-file = /var/run/mysqld/mysqld.pid
socket = /var/run/mysqld/mysqld.sock
port = 3306
basedir = /usr
datadir = /var/lib/mysql
tmpdir = /tmp

# Charset
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# InnoDB (điều chỉnh theo RAM server)
innodb_buffer_pool_size = 8G        # 60-70% RAM
innodb_buffer_pool_instances = 8
innodb_log_file_size = 1G
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT
innodb_file_per_table = 1
innodb_stats_persistent = 1
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Connection
max_connections = 200
max_user_connections = 150
wait_timeout = 28800
interactive_timeout = 28800

# Query cache (TẮT — QC không hiệu quả với workload nặng)
query_cache_type = 0
query_cache_size = 0

# Logging
log_error = /var/log/mysql/error.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = 1

# Binary log (cho replication + PITR)
server_id = 1
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
expire_logs_days = 7
max_binlog_size = 100M

# Safety
sql_mode = STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
default_storage_engine = InnoDB

# Performance
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000
innodb_flush_neighbors = 0
innodb_adaptive_hash_index = ON
```

## 3. Quy ước đặt tên

| Object | Convention | Ví dụ |
|--------|-----------|------|
| Database | snake_case | `pmketoan_prod` |
| Table | snake_case, plural | `accounting_voucher`, `voucher_line` |
| Column | snake_case | `voucher_no`, `fiscal_year` |
| Primary key | `id` (BIGINT UNSIGNED AUTO_INCREMENT) | |
| Foreign key | `<entity>_id` | `company_id`, `customer_id` |
| Index | `idx_<table>_<cols>` | `idx_voucher_date` |
| Unique constraint | `uk_<table>_<cols>` | `uk_company_voucher_no` |
| Foreign key constraint | `fk_<table>_<col>` | `fk_voucher_company` |

## 4. Quy ước kiểu dữ liệu

| Use case | Type | Lý do |
|----------|------|------|
| PK, FK | `BIGINT UNSIGNED` | Đủ lớn cho high volume |
| Money | `DECIMAL(20,4)` | Tránh float rounding |
| Exchange rate | `DECIMAL(18,6)` | Cần 6 số thập phân |
| Tax rate | `DECIMAL(6,4)` | 0.0000 - 1.0000 (0% - 100%) |
| Quantity | `DECIMAL(18,4)` | Hỗ trợ số thập phân |
| Date | `DATE` | |
| Timestamp | `TIMESTAMP` hoặc `DATETIME` | |
| Short text | `VARCHAR(255)` | |
| Long text | `TEXT` | |
| Very long (XML) | `LONGTEXT` | |
| Status enum | `TINYINT` + comment | Tự ghi chú |
| Boolean | `BOOLEAN` (= TINYINT(1)) | |

## 5. Multi-tenant strategy

### 5.1. Approach: Shared Database, Shared Schema

Tất cả data trong 1 database, phân biệt qua `company_id` column.

```sql
CREATE TABLE accounting_voucher (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    -- ...
    INDEX idx_company_date (company_id, voucher_date)
);
```

### 5.2. Tại sao không Schema-per-tenant?

| Approach | Pros | Cons |
|----------|------|------|
| **Shared DB / Shared Schema** | Khả năng scale tốt, query dễ, ít overhead | Cần filter mọi query |
| Shared DB / Schema-per-tenant | Cô lập data rõ hơn | Migrate khó, connection pool issue |
| DB-per-tenant | Cô lập hoàn toàn | Operational overhead lớn |

→ Chọn **Shared DB / Shared Schema** vì phù hợp với kế toán (ít công ty nhưng nhiều user).

### 5.3. Row-level security

Tự động filter mọi query:

```python
# apps/core/managers.py
from django.db import models

class CompanyQuerySet(models.QuerySet):
    def for_company(self, company_id):
        return self.filter(company_id=company_id)


class CompanyManager(models.Manager.from_queryset(CompanyQuerySet)):
    def get_queryset(self):
        # Tự động filter nếu có current_company trong thread-local
        from apps.core.middleware import _thread_locals
        company_id = getattr(_thread_locals, 'company_id', None)
        qs = super().get_queryset()
        if company_id and hasattr(qs.model, 'company_id'):
            qs = qs.filter(company_id=company_id)
        return qs


class CompanyOwnedModel(models.Model):
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE)
    objects = CompanyManager()
    
    class Meta:
        abstract = True
```

## 6. Partitioning

### 6.1. Khi nào partition?

- Bảng > 10 triệu rows
- Query thường theo range (theo năm, tháng)

### 6.2. Bảng nên partition

| Bảng | Partition key | Strategy |
|------|--------------|---------|
| `accounting_voucher` | `fiscal_year` | RANGE |
| `voucher_line` | (qua voucher_id) hoặc `fiscal_year` | RANGE |
| `stock_ledger` | `transaction_date` | RANGE by year |
| `attendance_record` | `attendance_date` | RANGE by year-month |
| `user_access_log` | `created_at` | RANGE by month |

```sql
ALTER TABLE accounting_voucher
PARTITION BY RANGE (fiscal_year) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p2026 VALUES LESS THAN (2027),
    PARTITION p2027 VALUES LESS THAN (2028),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 6.3. Maintenance partition

```sql
-- Thêm partition cho năm mới (chạy mỗi cuối năm)
ALTER TABLE accounting_voucher 
REORGANIZE PARTITION pmax INTO (
    PARTITION p2028 VALUES LESS THAN (2028),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- Archive data cũ (sau 5 năm)
ALTER TABLE accounting_voucher DROP PARTITION p2020;
-- Hoặc: ALTER TABLE ... EXCHANGE PARTITION ... WITH TABLE archived_voucher_2020;
```

## 7. Indexing strategy

### 7.1. Indexing rules

1. **PK index**: tự động có (InnoDB clustered)
2. **FK index**: MariaDB tự tạo index cho FK
3. **Filter columns**: Index column thường WHERE (nhưng tránh over-indexing)
4. **Sort columns**: Index cho ORDER BY
5. **Compound index**: theo thứ tự selectivity cao → thấp

### 7.2. Index ví dụ

```sql
-- Voucher: query theo công ty + ngày
ALTER TABLE accounting_voucher ADD INDEX idx_company_date (company_id, voucher_date);

-- Voucher: query theo công ty + kỳ
ALTER TABLE accounting_voucher ADD INDEX idx_company_period (company_id, fiscal_year, period, status);

-- Voucher line: query theo voucher
ALTER TABLE voucher_line ADD INDEX idx_voucher_id (voucher_id);

-- Voucher line: query theo account
ALTER TABLE voucher_line ADD INDEX idx_account_code (account_code);

-- Stock ledger: query theo product/warehouse
ALTER TABLE stock_ledger ADD INDEX idx_product_wh (product_id, warehouse_id, transaction_date);

-- Customer: tìm theo MST
ALTER TABLE customer ADD INDEX idx_tax_code (tax_code);
```

### 7.3. Covering index

Cho query hot:

```sql
-- VD: list voucher với thông tin chính
SELECT voucher_no, voucher_date, total_vnd, status
FROM accounting_voucher
WHERE company_id = 1 AND fiscal_year = 2026 AND status = 2
ORDER BY voucher_date DESC
LIMIT 25;

-- Covering index:
ALTER TABLE accounting_voucher ADD INDEX idx_cover_list
(company_id, fiscal_year, status, voucher_date, voucher_no, total_vnd);
```

### 7.4. Execution plan analysis

```sql
EXPLAIN SELECT * FROM accounting_voucher
WHERE company_id = 1 AND voucher_date BETWEEN '2026-01-01' AND '2026-06-30';

EXPLAIN ANALYZE SELECT v.voucher_no, vl.account_code, vl.debit_vnd
FROM accounting_voucher v
JOIN voucher_line vl ON vl.voucher_id = v.id
WHERE v.company_id = 1 AND v.fiscal_year = 2026;
```

## 8. Backup strategy

### 8.1. Daily full backup

```bash
#!/bin/bash
# /scripts/backup_full.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/mysql/full
mkdir -p $BACKUP_DIR

mariadb-backup --backup \
    --target-dir=$BACKUP_DIR/$DATE \
    --user=backup --password=$BACKUP_PASSWORD \
    --compress --compress-threads=4

# Keep 7 daily backups
find $BACKUP_DIR -mtime +7 -delete

# Upload to S3
aws s3 sync $BACKUP_DIR/$DATE s3://pmketoan-backup/full/$DATE
```

### 8.2. Hourly incremental (via binlog)

```bash
#!/bin/bash
# /scripts/backup_binlog.sh
DATE=$(date +%Y%m%d_%H%M%S)
mysql -u backup -p$BACKUP_PASSWORD -e "FLUSH BINARY LOGS;"
cp /var/lib/mysql/mysql-bin.* /backup/mysql/binlog/$DATE/
```

### 8.3. Point-in-time recovery

```bash
# Restore to specific time
mariadb-backup --copy-back --target-dir=/backup/mysql/full/20260616_020000
mysqlbinlog --start-datetime="2026-06-16 10:00:00" \
            --stop-datetime="2026-06-16 11:30:00" \
            /var/lib/mysql/mysql-bin.* | mysql -u root -p
```

## 9. High Availability

### 9.1. Primary-Replica replication

```
┌────────────┐    writes      ┌────────────┐
│  Primary   │ ─────────────→ │  Replica   │
│  (read+write)│              │  (read)    │
└────────────┘                └────────────┘
       ↑                            ↑
       │ writes                     │ reads (reports)
       │                            │
   Application                  Reporting
```

Django config:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pmketoan',
        'USER': 'pmketoan_app',
        'PASSWORD': '...',
        'HOST': 'primary.db.internal',
        'PORT': '3306',
    },
    'replica': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pmketoan',
        'USER': 'pmketoan_app_replica',
        'PASSWORD': '...',
        'HOST': 'replica.db.internal',
        'PORT': '3306',
    },
}

# Router
DATABASE_ROUTERS = ['apps.db_router.ReadWriteRouter']

# apps/db_router.py
class ReadWriteRouter:
    def db_for_read(self, model, **hints):
        # Reads from replica for reporting models
        if model._meta.app_label == 'reporting':
            return 'replica'
        return 'default'
    
    def db_for_write(self, model, **hints):
        return 'default'
```

### 9.2. Galera Cluster (cho HA cao)

3-node Galera cluster cho multi-master:

```ini
[mysqld]
binlog_format = ROW
default_storage_engine = InnoDB
innodb_autoinc_lock_mode = 2

wsrep_on = ON
wsrep_provider = /usr/lib/galera/libgalera_smm.so
wsrep_cluster_name = pmketoan_cluster
wsrep_cluster_address = gcomm://node1,node2,node3
wsrep_node_address = node1
wsrep_node_name = node1
wsrep_sst_method = mariabackup
```

## 10. Monitoring

### 10.1. Slow query log

```sql
-- Bật slow log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 'ON';
```

### 10.2. Performance schema

```sql
-- Top 10 slow queries
SELECT DIGEST_TEXT, COUNT_STAR, AVG_TIMER_WAIT/1000000000 AS avg_ms
FROM performance_schema.events_statements_summary_by_digest
ORDER BY AVG_TIMER_WAIT DESC
LIMIT 10;

-- Top tables by IO
SELECT * FROM sys.io_global_by_file_by_bytes LIMIT 10;
```

### 10.3. External monitoring

- **Prometheus + mysqld_exporter**: metrics
- **Grafana**: dashboard
- **Percona PMM**: comprehensive monitoring

## 11. Quy ước migration

```python
# apps/ledger/migrations/0002_add_voucher_index.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('ledger', '0001_initial')]
    
    operations = [
        migrations.AddIndex(
            model_name='accountingvoucher',
            index=models.Index(
                fields=['company', 'voucher_date'],
                name='idx_company_date',
            ),
        ),
    ]
```

Quy tắc:
- Không bao giờ `DROP COLUMN` mà không có migration data
- Test trên staging trước
- Backup trước migration lớn
- Dùng `ALTER TABLE ... ALGORITHM=INPLACE, LOCK=NONE` cho changes lớn

---

**Tiếp theo**: [06. Deployment](./06-deployment.md)
