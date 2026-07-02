"""Send tax deadline reminders to users.

Checks upcoming tax deadlines (VAT, PIT, BHXH) and sends in-app
notifications 7 days and 1 day before the due date. Designed to run
daily via cron or django-q2 schedule.

Usage:
    python manage.py send_tax_reminders
    python manage.py send_tax_reminders --dry-run
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.core.models import Company
from apps.identity.models import User, UserCompanyRole
from apps.notifications.models import Notification

REMINDER_DAYS = [7, 1]  # send 7 days and 1 day before deadline


def get_upcoming_deadlines(today):
    """Return list of (type, due_date, days_left, url) for upcoming tax deadlines."""
    deadlines = []

    # VAT + PIT: 20th of current month (for last month's taxes) or next month
    # Whichever 20th is nearest and still upcoming
    current_20 = date(today.year, today.month, 20)
    if today <= current_20:
        vat_date = current_20
    elif today.month == 12:
        vat_date = date(today.year + 1, 1, 20)
    else:
        vat_date = date(today.year, today.month + 1, 20)

    vat_days = (vat_date - today).days
    if vat_days in REMINDER_DAYS or vat_days == 0:
        deadlines.append(("VAT (GTGT)", vat_date, vat_days, "/modern/reports/vat-return/"))
        deadlines.append(("TNCN (khấu trừ)", vat_date, vat_days, "/modern/reports/pit-monthly/"))

    # BHXH: last day of current month
    if today.month == 12:
        bhxh_date = date(today.year, 12, 31)
    else:
        bhxh_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    bhxh_days = (bhxh_date - today).days
    if bhxh_days in REMINDER_DAYS or bhxh_days == 0:
        deadlines.append(("BHXH + D62", bhxh_date, bhxh_days, "/modern/reports/d62/"))

    return deadlines


class Command(BaseCommand):
    help = "Send tax deadline reminders to admin/chief accountant users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without creating notifications.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        today = date.today()
        deadlines = get_upcoming_deadlines(today)

        if not deadlines:
            self.stdout.write("No tax deadlines within reminder window today.")
            return

        sent_count = 0
        skipped_count = 0

        for company in Company.objects.filter(is_active=True):
            # Notify admin + chief accountant roles
            recipient_ids = set(
                UserCompanyRole.objects.filter(
                    company=company,
                    role__code__in=["admin", "chief_accountant"],
                ).values_list("user_id", flat=True)
            )
            # Also notify superusers assigned to this company
            recipient_ids.update(
                UserCompanyRole.objects.filter(
                    company=company, user__is_superuser=True
                ).values_list("user_id", flat=True)
            )
            # Fallback: if no role-bound users, notify all superusers
            if not recipient_ids:
                recipient_ids = set(
                    User.objects.filter(is_superuser=True, is_active=True).values_list(
                        "id", flat=True
                    )
                )

            if not recipient_ids:
                continue

            for tax_type, due_date, days_left, url in deadlines:
                # Dedup key: type + due_date + days_left prevents double-sending
                dedup_key = f"tax_reminder:{tax_type}:{due_date.isoformat()}:{days_left}"

                for uid in recipient_ids:
                    # Check if already sent
                    exists = Notification.objects.filter(
                        user_id=uid,
                        company=company,
                        related_object_type="tax_reminder",
                        related_object_id=hash(dedup_key) % 2147483647,
                    ).exists()
                    if exists:
                        skipped_count += 1
                        continue

                    if days_left <= 0:
                        title = f"HẾT HẠN: {tax_type} hôm nay!"
                        due_str = due_date.strftime("%d/%m/%Y")
                        msg = f"{tax_type} đến hạn hôm nay ({due_str}). Nộp ngay để tránh phạt."
                        ntype = Notification.Type.ERROR
                    elif days_left <= 1:
                        title = f"MAI HẾT HẠN: {tax_type}"
                        due_str = due_date.strftime("%d/%m/%Y")
                        msg = f"{tax_type} đến hạn ngày {due_str} (mai). Chuẩn bị nộp ngay."
                        ntype = Notification.Type.WARNING
                    else:
                        title = f"Sắp hết hạn: {tax_type} ({days_left} ngày)"
                        due_str = due_date.strftime("%d/%m/%Y")
                        msg = f"{tax_type} đến hạn ngày {due_str} — còn {days_left} ngày."
                        ntype = Notification.Type.WARNING

                    if dry_run:
                        self.stdout.write(f"[DRY] → user={uid} company={company.code}: {title}")
                        continue

                    Notification.objects.create(
                        user_id=uid,
                        company=company,
                        type=ntype,
                        title=title,
                        message=msg,
                        url=url,
                        related_object_type="tax_reminder",
                        related_object_id=hash(dedup_key) % 2147483647,
                    )
                    sent_count += 1

        action = "would send" if dry_run else "sent"
        self.stdout.write(
            self.style.SUCCESS(
                f"Tax reminders: {action} {sent_count}, skipped {skipped_count} (duplicates)."
            )
        )
