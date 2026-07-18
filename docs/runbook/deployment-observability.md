# Deployment Observability — Visota ERP

> Where to check deploy impact and system health.

## Monitoring Dashboards

### Sentry (Error Tracking)
- **URL:** https://sentry.io (configure SENTRY_DSN in .env)
- **What:** JavaScript errors, Django exceptions, slow transactions
- **Deploy check:** After deploy, check Sentry for new error spikes

### Django Health Checks
- **URL:** https://visota.net/health/ (simple JSON)
- **URL:** https://visota.net/health/detailed/ (full system check)
- **What:** Database, cache, queue connectivity

### Docker Health Check
- Built into Dockerfile: `curl -f http://localhost:8900/health/`
- Reports container health to Docker daemon

## Log Aggregation

Logs are output to stdout in structured JSON format (see `apps/core/logging_utils.py`).
Each log line includes `request_id` for distributed tracing.

To follow a request through the system, grep for the `X-Request-ID` response header
and search logs for that ID.

## Deploy Notifications

GitHub Actions Deploy workflow sends a notification on each push to main.
Configure a Slack webhook to receive deploy alerts:

```bash
# In GitHub repo settings > Secrets:
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Metrics (Optional)

Prometheus metrics endpoint available when `PROMETHEUS_METRICS_ENABLED=true`.
Scrape with:
```yaml
scrape_configs:
  - job_name: 'visota'
    metrics_path: /metrics
    static_configs:
      - targets: ['visota.net:8900']
```

## Alerting

Configure PagerDuty/OpsGenie integration via Sentry:
1. Sentry > Settings > Integrations > PagerDuty
2. Create alert rules for: new error rate > threshold, performance regression
