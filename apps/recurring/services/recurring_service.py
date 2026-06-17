"""RecurringService — runs all due recurring templates."""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.recurring.models import RecurringTemplate


def _resolve_callable(dotted: str):
    """Resolve ``module.path:attr`` or ``module.path.attr`` to a callable."""
    if ":" in dotted:
        module_path, attr = dotted.split(":", 1)
    elif "." in dotted:
        module_path, attr = dotted.rsplit(".", 1)
    else:
        raise ValueError(f"Invalid dotted path: {dotted!r}")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _compute_next_run(schedule_type: str, day_of_month: int, now: datetime) -> datetime:
    """Compute the next run datetime given schedule + day-of-month."""
    # Make `now` tz-aware if necessary (Django USE_TZ=True).
    if timezone.is_naive(now):
        now = timezone.make_aware(now)

    day = max(1, min(28, int(day_of_month)))
    cur_year, cur_month = now.year, now.month

    def first_of_month(year: int, month: int) -> datetime:
        d = datetime(year, month, day, hour=2, minute=0, second=0, microsecond=0)
        return timezone.make_aware(d) if timezone.is_naive(d) else d

    if schedule_type == RecurringTemplate.ScheduleType.MONTHLY:
        candidate = first_of_month(cur_year, cur_month)
        if candidate <= now:
            # move to next month
            if cur_month == 12:
                candidate = first_of_month(cur_year + 1, 1)
            else:
                candidate = first_of_month(cur_year, cur_month + 1)
        return candidate

    if schedule_type == RecurringTemplate.ScheduleType.QUARTERLY:
        # First month of current quarter
        q_month = ((cur_month - 1) // 3) * 3 + 1
        candidate = first_of_month(cur_year, q_month)
        while candidate <= now:
            q_month += 3
            if q_month > 12:
                q_month = 1
                cur_year += 1
            candidate = first_of_month(cur_year, q_month)
        return candidate

    if schedule_type == RecurringTemplate.ScheduleType.YEARLY:
        candidate = first_of_month(cur_year, 1)
        while candidate <= now:
            cur_year += 1
            candidate = first_of_month(cur_year, 1)
        return candidate

    # default: monthly
    return _compute_next_run(RecurringTemplate.ScheduleType.MONTHLY, day, now)


class RecurringService:
    """Run all due recurring templates for a company."""

    def __init__(self, company=None):
        self.company = company

    # ---------- single template ----------
    @transaction.atomic
    def run_one(self, template: RecurringTemplate) -> dict[str, Any]:
        """Import + call template.service_func, capture result, update template."""
        func = _resolve_callable(template.service_func)
        company = template.company or self.company
        try:
            result = func(company) if company is not None else func()
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc), "type": type(exc).__name__}
            status = "error"

        now = timezone.now()
        template.last_run_at = now
        template.last_run_result = {"status": status, "result": result}
        template.next_run_at = _compute_next_run(
            template.schedule_type, template.day_of_month, now
        )
        template.save()
        return {"template_id": template.id, "name": template.name, **template.last_run_result}

    # ---------- all due ----------
    def run_all_due(self) -> list[dict[str, Any]]:
        """Find all active templates where next_run_at <= now, execute them."""
        now = timezone.now()
        qs = RecurringTemplate.objects.filter(
            is_active=True, next_run_at__lte=now
        )
        if self.company is not None:
            qs = qs.filter(company=self.company)
        results = []
        for tpl in qs:
            results.append(self.run_one(tpl))
        return results

    # ---------- defaults ----------
    def setup_defaults(self, company) -> list[RecurringTemplate]:
        """Create default recurring templates for a new company."""
        defaults = [
            {
                "name": "Khấu hao TSCĐ/CCDC hàng tháng",
                "description": "Tính khấu hao tài sản cố định + CCDC",
                "service_func": "apps.recurring.runners:run_depreciation",
                "schedule_type": RecurringTemplate.ScheduleType.MONTHLY,
                "day_of_month": 1,
            },
            {
                "name": "Tính lương định kỳ",
                "description": "Tính lương nhân viên kỳ hiện tại",
                "service_func": "apps.recurring.runners:run_payroll",
                "schedule_type": RecurringTemplate.ScheduleType.MONTHLY,
                "day_of_month": 28,
            },
            {
                "name": "Kết chuyển cuối kỳ",
                "description": "KC doanh thu/chi phí → 911 → 421",
                "service_func": "apps.recurring.runners:run_period_closing",
                "schedule_type": RecurringTemplate.ScheduleType.MONTHLY,
                "day_of_month": 28,
            },
        ]
        created = []
        now = timezone.now()
        for d in defaults:
            tpl, _ = RecurringTemplate.objects.update_or_create(
                company=company,
                name=d["name"],
                defaults={
                    "description": d["description"],
                    "service_func": d["service_func"],
                    "schedule_type": d["schedule_type"],
                    "day_of_month": d["day_of_month"],
                    "is_active": True,
                    "next_run_at": _compute_next_run(
                        d["schedule_type"], d["day_of_month"], now
                    ),
                },
            )
            created.append(tpl)
        return created
