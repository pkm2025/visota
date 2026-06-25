#!/bin/bash
set -euo pipefail
BACKUP_DIR=/var/backups/visota
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

source /opt/visota/.env

mysqldump --single-transaction --routines --triggers \
  --user=$DB_USER --password=$DB_PASSWORD $DB_NAME \
  | gzip > $BACKUP_DIR/db_${TS}.sql.gz

aws s3 cp $BACKUP_DIR/db_${TS}.sql.gz s3://visota-backups/db/$(date +%Y/%m/%d)/ 2>/dev/null || true
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
echo "✓ Backup: db_${TS}.sql.gz"
