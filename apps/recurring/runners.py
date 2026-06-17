"""Recurring runner callables — dotted-path entry points for templates.

Each callable accepts ``(company, **opts)`` and returns a JSON-serializable
dict. Keeping them as small wrappers around the real services makes the
``service_func`` dotted path stable and self-contained.
"""

from __future__ import annotations

from datetime import date


def run_depreciation(company, **opts) -> dict:
    """Run monthly depreciation for current period."""
    today = opts.get("as_of") or date.today()
    from apps.assets.services import DepreciationService

    svc = DepreciationService(company=company)
    return svc.calculate_period(fiscal_year=today.year, period=today.month)


def run_payroll(company, **opts) -> dict:
    """Run monthly payroll."""
    today = opts.get("as_of") or date.today()
    from apps.payroll.services import PayrollService

    svc = PayrollService(company=company)
    run = svc.calculate(period=f"{today.year}-{today.month:02d}")
    return {"payroll_run_id": run.id, "period": f"{today.year}-{today.month:02d}"}


def run_period_closing(company, **opts) -> dict:
    """Run period closing (KC → 911 → 421)."""
    today = opts.get("as_of") or date.today()
    from apps.ledger.services import PeriodClosingService

    svc = PeriodClosingService(company=company)
    return svc.close_period(fiscal_year=today.year, period=today.month)


def noop(company, **opts) -> dict:  # noqa: ARG001
    """Default no-op runner — used for tests / placeholders."""
    return {"status": "ok", "message": "noop"}
