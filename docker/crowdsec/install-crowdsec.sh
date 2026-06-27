#!/bin/bash
# ============================================================
#  Install CrowdSec bouncer on host — blocks IPs via firewalld
#  Run: sudo bash docker/crowdsec/install-crowdsec.sh
# ============================================================

set -e

echo "=== Installing CrowdSec Bouncer ==="

# 1. Install bouncer package on host
# For AlmaLinux/RHEL:
dnf install -y crowdsec-firewall-bouncer-iptables 2>/dev/null || {
    # Fallback: install from CrowdSec repo
    curl -s https://packagecloud.io/install/repositories/crowdsec/crowdsec/script.rpm.sh | bash
    dnf install -y crowdsec-firewall-bouncer
}

# 2. Configure to connect to CrowdSec container API
cat > /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml << 'EOF'
api_url: http://127.0.0.1:8080/
api_key: ""
disable_ipv6: false
deny_action: DROP
deny_log: true
deny_log_prefix: "CROWDSEC-BLOCK"
# Use iptables directly (firewalld compatible)
mode: iptables
pid_dir: /var/run/
update_frequency: 10s
daemonize: true
log_mode: file
log_dir: /var/log/
log_level: info
EOF

# 3. Generate API key
echo "Generating bouncer API key..."
bouncer_name="visota-firewall-bouncer"
api_key=$(docker exec crowdsec cscli bouncers add "$bouncer_name" -o raw 2>/dev/null || echo "")

if [ -n "$api_key" ]; then
    sed -i "s/api_key: \"\"/api_key: \"$api_key\"/" /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
    echo "  API key: ${api_key:0:8}..."
else
    echo "  Warning: Could not auto-generate API key."
    echo "  Run: docker exec crowdsec cscli bouncers add $bouncer_name"
    echo "  Then update /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml"
fi

# 4. Enable + start
systemctl enable crowdsec-firewall-bouncer
systemctl restart crowdsec-firewall-bouncer

# 5. Verify
sleep 3
if systemctl is-active --quiet crowdsec-firewall-bouncer; then
    echo ""
    echo "✓ CrowdSec bouncer active — blocking bad IPs via firewalld"
    echo ""
    echo "Useful commands:"
    echo "  cscli decisions list          — xem IPs đang bị block"
    echo "  cscli metrics                 — xem số lượng tấn công"
    echo "  cscli alerts list             — xem alerts"
    echo "  docker exec crowdsec cscli hub list  — xem collections"
else
    echo "✗ Bouncer failed to start — check: journalctl -u crowdsec-firewall-bouncer"
fi

# 6. Enable Traefik log file (for CrowdSec to read)
echo ""
echo "=== Enabling Traefik access logs ==="
if [ -f /opt/traefik/traefik.yml ]; then
    # Add access logs config if not present
    if ! grep -q "accessLog" /opt/traefik/traefik.yml; then
        cat >> /opt/traefik/traefik.yml << 'TRAEFIKLOG'

accessLog:
  filePath: "/var/log/traefik/access.log"
  format: json
  bufferingSize: 100
TRAEFIKLOG
        mkdir -p /opt/traefik/logs
        cd /opt/traefik && docker compose restart traefik
        echo "✓ Traefik access logs enabled → /opt/traefik/logs/access.log"
    else
        echo "  Traefik access logs already configured"
    fi
fi
