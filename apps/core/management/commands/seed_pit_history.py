"""Seed Vietnamese PIT (Thuế TNCN) rate history — 2009 → 2026.

Tracks deduction and bracket changes across 4 PIT law periods:
  1. 2009-01-01 → 2013-06-30  Luật TNCN 04/2007/QH12        (GTGC 4M, NPT 1.6M, 7 bậc)
  2. 2013-07-01 → 2020-06-30  Luật 26/2012/QH13 (sửa đổi)   (GTGC 9M, NPT 3.6M, 7 bậc)
  3. 2020-07-01 → 2025-12-31  NQ 954/2020/NQ-UBTVQH14       (GTGC 11M, NPT 4.4M, 7 bậc)
  4. 2026-01-01 → now         Luật 09/2026/QH16 (hiệu lực 01/01/2026) (GTGC 13.2M, NPT 5.2M, 5 bậc)

Note: Luật 09/2026/QH16 is effective from kỳ tính thuế năm 2026 (01/01/2026),
NOT from 01/07/2026 as previously assumed.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.core.models import PITRateHistory

PIT_HISTORY = [
    {
        "period_start": "2009-01-01",
        "period_end": "2013-06-30",
        "personal_deduction": 4000000,
        "dependent_deduction": 1600000,
        "brackets": [
            [5000000, 0.05],
            [10000000, 0.10],
            [18000000, 0.15],
            [32000000, 0.20],
            [52000000, 0.25],
            [80000000, 0.30],
            [999999999, 0.35],
        ],
        "legal_basis": "Luật TNCN 04/2007/QH12",
        "is_current": False,
    },
    {
        "period_start": "2013-07-01",
        "period_end": "2020-06-30",
        "personal_deduction": 9000000,
        "dependent_deduction": 3600000,
        "brackets": [
            [5000000, 0.05],
            [10000000, 0.10],
            [18000000, 0.15],
            [32000000, 0.20],
            [52000000, 0.25],
            [80000000, 0.30],
            [999999999, 0.35],
        ],
        "legal_basis": "Luật 26/2012/QH13 (sửa đổi Luật TNCN)",
        "is_current": False,
    },
    {
        "period_start": "2020-07-01",
        "period_end": "2025-12-31",
        "personal_deduction": 11000000,
        "dependent_deduction": 4400000,
        "brackets": [
            [5000000, 0.05],
            [10000000, 0.10],
            [18000000, 0.15],
            [32000000, 0.20],
            [52000000, 0.25],
            [80000000, 0.30],
            [999999999, 0.35],
        ],
        "legal_basis": "Nghị quyết 954/2020/NQ-UBTVQH14",
        "is_current": False,
    },
    # 2026-01-01 → hiện tại (Luật 09/2026/QH16 — hiệu lực từ kỳ tính thuế năm 2026)
    # GTGC 13.2M/tháng (158.4M/năm), NPT 5.2M, 5 bậc lũy tiến.
    {
        "period_start": "2026-01-01",
        "period_end": None,
        "personal_deduction": 13200000,
        "dependent_deduction": 5200000,
        "brackets": [
            [5000000, 0.05],
            [10000000, 0.10],
            [18000000, 0.15],
            [32000000, 0.20],
            [999999999, 0.25],
        ],  # 5 bậc theo Luật 09/2026/QH16
        "legal_basis": "Luật 09/2026/QH16 (hiệu lực từ 01/01/2026)",
        "is_current": True,
    },
    # Dự kiến từ 01/07/2026 (NQ 110/2025) — chưa áp dụng, chỉ ghi chú.
    # Nếu sau này được kích hoạt, bỏ comment và cập nhật is_current.
    # {
    #     "period_start": "2026-07-01",
    #     "period_end": None,
    #     "personal_deduction": 15500000,
    #     "dependent_deduction": 6200000,
    #     "brackets": [
    #         [5000000, 0.05],
    #         [10000000, 0.10],
    #         [18000000, 0.15],
    #         [32000000, 0.20],
    #         [999999999, 0.25],
    #     ],
    #     "legal_basis": "NQ 110/2025/UBTVQH15 (dự kiến từ 01/07/2026)",
    #     "is_current": False,
    # },
]


class Command(BaseCommand):
    help = "Seed PIT rate history (4 periods: 2009, 2013, 2020, 2026)."

    def handle(self, *args, **options):
        # Reset is_current across all rows before re-applying
        PITRateHistory.objects.filter(is_current=True).update(is_current=False)
        created_count = 0
        for entry in PIT_HISTORY:
            period_start = date.fromisoformat(entry["period_start"])
            period_end = date.fromisoformat(entry["period_end"]) if entry["period_end"] else None
            _, created = PITRateHistory.objects.update_or_create(
                period_start=period_start,
                defaults={
                    "period_end": period_end,
                    "personal_deduction": Decimal(str(entry["personal_deduction"])),
                    "dependent_deduction": Decimal(str(entry["dependent_deduction"])),
                    "brackets": entry["brackets"],
                    "legal_basis": entry["legal_basis"],
                    "is_current": entry.get("is_current", False),
                },
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PIT_HISTORY)} PIT rate history entries ({created_count} new)."
            )
        )
