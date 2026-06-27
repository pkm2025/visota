#!/bin/bash
# ============================================================
#  Visota Security Audit — chạy weekly qua cron
#  Tools: Lynis (audit), rkhunter (rootkit), Docker Bench
#  Usage: sudo visota-ctl security-audit  (hoặc cron Sun 4am)
# ============================================================

set -e

REPORT_DIR="/var/log/visota/security"
mkdir -p "$REPORT_DIR"
TS=$(date +%Y%m%d_%H%M%S)

echo "=== Visota Security Audit ==="

# ===== 1. System updates check =====
echo "Checking security updates..."
updates=$(dnf check-update --security 2>/dev/null | grep -c "\.el" || echo "0")
echo "  Security updates available: $updates"

# ===== 2. Lynis (if installed) =====
if command -v lynis &>/dev/null; then
    echo "Running Lynis audit..."
    lynis audit system --quiet --logfile "$REPORT_DIR/lynis_${TS}.log" 2>/dev/null || true
    echo "  Lynis report: $REPORT_DIR/lynis_${TS}.log"
else
    echo "  Lynis not installed (install: dnf install lynis)"
fi

# ===== 3. Rootkit Hunter =====
if command -v rkhunter &>/dev/null; then
    echo "Running rkhunter scan..."
    rkhunter --check --skip-keypress --report-warnings-only 2>/dev/null | tee "$REPORT_DIR/rkhunter_${TS}.log" || true
    echo "  rkhunter report: $REPORT_DIR/rkhunter_${TS}.log"
else
    echo "  rkhunter not installed (install: dnf install rkhunter)"
fi

# ===== 4. Failed SSH logins (last 24h) =====
echo "Checking failed SSH logins..."
failed=$(journalctl -u sshd --since "24 hours ago" 2>/dev/null | grep -c "Failed password" || echo "0")
echo "  Failed SSH attempts (24h): $failed"

# ===== 5. fail2ban status =====
if systemctl is-active --quiet fail2ban 2>/dev/null; then
    echo "fail2ban status:"
    fail2ban-client status sshd 2>/dev/null | grep -E "Currently|Total" | sed 's/^/  /'
fi

# ===== 6. Docker exposed ports (should be minimal) =====
echo "Checking exposed Docker ports..."
docker ps --format "{{.Names}}: {{.Ports}}" 2>/dev/null | grep "0.0.0.0" | grep -v "80\|443" && \
    echo "  ⚠ Non-standard ports exposed!" || echo "  ✓ Only 80/443 exposed"

# ===== 7. Disk space =====
disk_pct=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
echo "Disk usage: ${disk_pct}%"
[ "$disk_pct" -gt 85 ] && echo "  🚨 CRITICAL disk space!"

# ===== 8. Open files (resource leak check) =====
open_files=$(cat /proc/sys/fs/file-nr | awk '{print $1}')
max_files=$(cat /proc/sys/fs/file-max)
pct=$((open_files * 100 / max_files))
echo "Open files: ${open_files}/${max_files} (${pct}%)"

echo ""
echo "=== Audit complete ==="
echo "Reports in: $REPORT_DIR"
