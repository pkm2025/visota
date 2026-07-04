"""Structured JSON logging with PII scrubbing for PMKetoan.

Provides:
  - StructuredJSONFormatter: JSON output with request_id, timestamp, level
  - PII field redaction (passwords, tokens, emails, phone numbers)
  - Request ID propagation via X-Request-ID header
"""

import json
import logging
import re
import uuid
from typing import Any

PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4,5}\b"), "[PHONE]"),
    (re.compile(r"\b\d{9,12}\b"), "[TAX_ID]"),
]

PII_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "private_key",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
        "tax_code",
    }
)


def scrub_value(val: Any) -> Any:
    """Redact PII from a value."""
    if isinstance(val, str):
        for pattern, replacement in PII_PATTERNS:
            val = pattern.sub(replacement, val)
        return val
    if isinstance(val, dict):
        return {
            k: "[REDACTED]" if k.lower() in PII_KEYS else scrub_value(v) for k, v in val.items()
        }
    if isinstance(val, (list, tuple)):
        return [scrub_value(v) for v in val]
    return val


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter with PII scrubbing and request_id."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Scrub extra fields
        for key in ("user_id", "path", "method", "status_code", "ip"):
            if hasattr(record, key):
                log_entry[key] = scrub_value(getattr(record, key))

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class RequestIDFilter(logging.Filter):
    """Inject request_id from threadlocal into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            import threading

            tid = threading.current_thread().ident
            record.request_id = getattr(threading.current_thread(), "_request_id", f"tid-{tid}")
        return True


def get_request_id() -> str:
    """Generate or retrieve the current request ID."""
    import threading

    return getattr(threading.current_thread(), "_request_id", str(uuid.uuid4())[:8])


def set_request_id(request_id: str | None = None) -> str:
    """Set the request ID for the current thread."""
    import threading

    rid = request_id or uuid.uuid4().hex[:12]
    threading.current_thread()._request_id = rid
    return rid


def configure_structured_logging():
    """Configure structured JSON logging with PII scrubbing."""
    formatter = StructuredJSONFormatter()
    request_filter = RequestIDFilter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(request_filter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # App loggers
    for app in ("apps", "django", "gunicorn"):
        logger = logging.getLogger(app)
        logger.handlers = []
        logger.addHandler(handler)
        logger.propagate = True
