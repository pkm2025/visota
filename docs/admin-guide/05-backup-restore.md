# A5 — Backup & Restore

> Quy trình backup hàng ngày, restore khi cần, DR plan.

## 1. Chiến lược backup

### Khuyến nghị 3-2-1

| Loại | Số bản | Nơi | Tần suất |
|------|--------|-----|-----------|
| Production DB | 2 latest | On-prem + cloud | Hàng ngày (02:00) |
| File media (uploads, PDF) | 1 | Cloud (S3) | Hàng ngày (03:00) |
| Off-site replication | 1 | DR site (khác DC) | Realtime (master-slave) |

### Lưu trữ

| Loại | Retention |
|------|-----------|
| Daily | 30 ngày |
| Weekly (Chủ nhật) | 12 tuần |
| Monthly (ngày 1) | 12 tháng |
| Yearly (01/01) | 10 năm (per Luật KT) |

## 2. Backup DB

### Script backup hàng ngày

`scripts/backup_db.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR=/var/backups/pmketoan
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME=pmketoan_prod
DB_USER=pmk
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

echo "[$(date)] Starting backup..."

# Backup via MariaDB mysqldump
mysqldump \
  --user=$DB_USER \
  --password=${DB_PASSWORD} \
  --single-transaction \
  --routines --triggers \
  --databases $DB_NAME \
  | gzip > $BACKUP_DIR/db_${TIMESTAMP}.sql.gz

# Verify
if [ $? -eq 0 ] && [ $(stat -c%s $BACKUP_DIR/db_${TIMESTAMP}.sql.gz) -gt 1000000 ]; then
  echo "[$(date)] OK: $(ls -lh $BACKUP_DIR/db_${TIMESTAMP}.sql.gz)"
else
  echo "[$(date)] FAIL: backup too small or error"
  exit 1
fi

# Cleanup old
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Cleanup done"

# Upload to cloud (optional, configure aws-cli)
if command -v aws &> /dev/null; then
  aws s3 cp $BACKUP_DIR/db_${TIMESTAMP}.sql.gz \
    s3://pmketoan-backups/db/$(date +%Y/%m/%d)/db_${TIMESTAMP}.sql.gz
fi

echo "[$(date)] Done"
```

### Crontab

```cron
# Backup daily at 2 AM
0 2 * * * /opt/pmketoan/scripts/backup_db.sh >> /var/log/pmk_backup.log 2>&1

# Backup weekly (Sun 3 AM)
0 3 * * 0 /opt/pmketoan/scripts/backup_db.sh --weekly >> /var/log/pmk_backup.log 2>&1
```

## 3. Backup file media

Files lưu tại `MEDIA_ROOT` (mặc định `/var/lib/pmketoan/media/`). Bao gồm:
- Attachment files (PDF, JPG, Excel)
- EInvoice XML/JSON/PDF
- Contract scans
- BHXH report PDFs
- Avatars

### Script sync S3

```bash
#!/bin/bash
aws s3 sync /var/lib/pmketoan/media/ s3://pmketoan-media/ \
  --storage-class STANDARD_IA \
  --delete \
  --exclude "*.tmp"
```

Chạy hàng ngày sau DB backup.

## 4. Restore

### DB restore

```bash
# Stop app
sudo systemctl stop pmketoan

# Drop and recreate DB (careful!)
mysql -u root -p -e "DROP DATABASE pmketoan_prod; CREATE DATABASE pmketoan_prod;"

# Restore
gunzip -c /var/backups/pmketoan/db_20260623_020000.sql.gz | \
  mysql -u pmk -p pmketoan_prod

# Start app
sudo systemctl start pmketoan

# Verify
curl -s http://localhost:8903/health/ | jq .
```

### File media restore

```bash
aws s3 sync s3://pmketoan-media/ /var/lib/pmketoan/media/ --delete
sudo chown -R pmketoan:pmketoan /var/lib/pmketoan/media/
```

### Restore thử nghiệm (DR drill)

**Quý 1 lần**, test restore sang server khác:

1. Chuẩn bị server DR (empty)
2. Restore DB backup gần nhất
3. Restore media từ S3
4. Verify:
   - Login được
   - Voucher list load được
   - 1 HĐĐT có file XML download được
5. Ghi log: thời gian restore, file size, kết quả verify
6. Nếu fail → điều chỉnh script

## 5. Point-in-time recovery

Nếu cần restore về thời điểm cụ thể (VD: xóa nhầm dữ liệu lúc 14:30):

### MariaDB binlog

1. Đảm bảo `log_bin=mysql-bin` trong `my.cnf`
2. Backup daily full + binlog liên tục

```bash
# Xác định thời điểm cần restore
mysqlbinlog --start-datetime="2026-06-23 00:00:00" \
            --stop-datetime="2026-06-23 14:29:00" \
  /var/lib/mysql/mysql-bin.001234 | \
  mysql -u root -p pmketoan_prod
```

## 6. Monitoring backup

### Health check script

```bash
#!/bin/bash
# Check backup freshness
LAST_BACKUP=$(ls -t /var/backups/pmketoan/db_*.sql.gz | head -1)
LAST_TIME=$(stat -c %Y $LAST_BACKUP)
NOW=$(date +%s)
AGE_HOURS=$(( (NOW - LAST_TIME) / 3600 ))

if [ $AGE_HOURS -gt 26 ]; then
  echo "ALERT: Last backup is $AGE_HOURS hours old"
  # Send to Slack/PagerDuty
  curl -X POST $SLACK_WEBHOOK -d "{\"text\":\"Visota ERP backup ALERT: $AGE_HOURS hours old\"}"
  exit 1
fi
echo "OK: last backup $AGE_HOURS hours ago"
```

### Cron

```cron
*/15 * * * * /opt/pmketoan/scripts/check_backup.sh
```

## 7. BCP / DR Plan

### RTO / RPO

| Metric | Mục tiêu |
|--------|----------|
| **RPO** (data loss) | ≤ 24h (daily backup) |
| **RTO** (downtime) | ≤ 4h |

### Khi production sập

1. **0-15 phút**: phát hiện (Prometheus alert)
2. **15-30 phút**: đánh giá nguyên nhân (DB crash / app bug / DC sập)
3. **30 phút - 4 giờ**: restore
   - DB crash → restore từ backup
   - App bug → rollback code
   - DC sập → switch sang DR site
4. **4-8 giờ**: verify + onboard user

### DR site (khác DC)

- Replicate realtime qua master-slave
- DNS failover (Cloudflare/Route53)
- Test switch ежеквартально

## 8. Encrypted backup

Backup có chứa dữ liệu nhạy cảm (MST, CCCD, lương). Mã hóa at-rest:

```bash
# GPG encryption
gpg --batch --yes --passphrase "$GPG_PASS" \
  --symmetric --cipher-algo AES256 \
  db_${TIMESTAMP}.sql.gz

# Result: db_${TIMESTAMP}.sql.gz.gpg
# Upload only .gpg to cloud
```

Restore:

```bash
gpg --batch --yes --passphrase "$GPG_PASS" --decrypt \
  db_${TIMESTAMP}.sql.gz.gpg | gunzip | mysql -u pmk -p pmketoan_prod
```

## 9. Compliance retention

Per **Luật Kế toán 2015** và **TT200/2014**:

| Loại chứng từ | Thời gian lưu |
|---------------|---------------|
| HĐĐT XML/PDF | ≥ 10 năm |
| Báo cáo tài chính | ≥ 10 năm |
| Sổ kế toán | ≥ 10 năm |
| Phiếu kế toán | ≥ 10 năm |
| Hợp đồng + thanh lý | ≥ 10 năm |
| Bảng lương + PIT | ≥ 10 năm |
| HĐLĐ + BHXH | ≥ 10 năm sau khi nghỉ |

> Đảm bảo backup yearly archive giữ 10+ năm. Cloud Glacier for archive.

## 10. Checklist hàng tháng

- [ ] Backup daily chạy OK (check log)
- [ ] Backup size không giảm đột ngột (> 20% alert)
- [ ] DR drill 1 lần/tháng — restore sang test env
- [ ] Test restore 1 file media ngẫu nhiên
- [ ] Verify binlog rotation OK
- [ ] Cloud sync OK (S3 bucket có file mới)

---

Tài liệu liên quan:
- [T6-deployment](../technical/06-deployment.md) — Deployment chi tiết
- [R7-troubleshooting](../runbook/07-troubleshooting.md) — Khôi phục sự cố
