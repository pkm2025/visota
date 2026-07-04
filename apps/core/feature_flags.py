"""Feature flag system for PMKetoan.

Simple database-backed feature flags that can be toggled per-company
or globally via environment variables.

Usage:
    from apps.core.feature_flags import is_enabled

    if is_enabled("new_reporting_engine"):
        ...

Flags can be set via:
  1. Environment variable: FEATURE_NEW_REPORTING_ENGINE=1
  2. Database: FeatureFlag.objects.create(key=..., enabled=True)
  3. Default: False (flags are off by default)
"""

import os

from django.core.cache import cache

DEFAULT_FLAGS: dict[str, bool] = {
    "new_reporting_engine": False,
    "ai_assistant": False,
    "batch_einvoice": False,
    "multi_currency": False,
    "advanced_budget": False,
}

CACHE_PREFIX = "feature_flag:"
CACHE_TTL = 300  # 5 minutes


def _get_env_key(flag_key: str) -> str:
    """Convert flag key to env var name: new_engine -> FEATURE_NEW_ENGINE."""
    return f"FEATURE_{flag_key.upper()}"


def is_enabled(flag_key: str, company_id: int | None = None) -> bool:
    """Check if a feature flag is enabled.

    Priority: env var > database (company-specific) > database (global) > default.
    """
    # 1. Environment variable (highest priority)
    env_val = os.environ.get(_get_env_key(flag_key))
    if env_val is not None:
        return env_val.lower() in ("1", "true", "yes", "on")

    # 2. Check cache
    cache_key = f"{CACHE_PREFIX}{flag_key}:{company_id or 'global'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 3. Database lookup
    try:
        from apps.core.models import FeatureFlag

        qs = FeatureFlag.objects.filter(key=flag_key, enabled=True)
        if company_id:
            qs = qs.filter(company_id=company_id)
        else:
            qs = qs.filter(company__isnull=True)
        result = qs.exists()
    except Exception:
        result = DEFAULT_FLAGS.get(flag_key, False)

    cache.set(cache_key, result, CACHE_TTL)
    return result


def enable(flag_key: str, company_id: int | None = None) -> None:
    """Enable a feature flag."""
    from apps.core.models import FeatureFlag

    FeatureFlag.objects.update_or_create(
        key=flag_key,
        company_id=company_id,
        defaults={"enabled": True},
    )
    cache_key = f"{CACHE_PREFIX}{flag_key}:{company_id or 'global'}"
    cache.delete(cache_key)


def disable(flag_key: str, company_id: int | None = None) -> None:
    """Disable a feature flag."""
    from apps.core.models import FeatureFlag

    FeatureFlag.objects.update_or_create(
        key=flag_key,
        company_id=company_id,
        defaults={"enabled": False},
    )
    cache_key = f"{CACHE_PREFIX}{flag_key}:{company_id or 'global'}"
    cache.delete(cache_key)
