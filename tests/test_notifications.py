"""Tests for notifications module: send, mark_read, send_to_role."""

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Company
from apps.notifications.models import EmailLog, Notification
from apps.notifications.services import NotificationService, EmailService

User = get_user_model()


@pytest.fixture
def company(db):
    return Company.objects.create(code="TESTNOT", name="Test Notif Co")


@pytest.fixture
def user(db, company):
    u = User.objects.create_user(
        username="alice", password="Secret123!", email="alice@test.local"
    )
    return u


@pytest.fixture
def user2(db, company):
    return User.objects.create_user(
        username="bob", password="Secret123!", email="bob@test.local"
    )


# ---------- Model tests ----------

@pytest.mark.django_db
def test_notification_str(user):
    n = Notification.objects.create(
        user=user, type="info", title="Test", message="Body"
    )
    assert str(n) == "[info] Test → alice"


@pytest.mark.django_db
def test_notification_icon_property(user):
    n = Notification.objects.create(user=user, type="success", title="x", message="y")
    assert "bi-check-circle" in n.icon
    assert "text-success" in n.icon


@pytest.mark.django_db
def test_notification_default_unread(user):
    n = Notification.objects.create(user=user, type="info", title="x", message="y")
    assert n.is_read is False
    assert n.read_at is None


# ---------- Service tests ----------

@pytest.mark.django_db
def test_send_creates_notification(user, company):
    n = NotificationService.send(
        user=user, company=company, type="warning",
        title="Hello", message="World"
    )
    assert n.pk is not None
    assert n.user == user
    assert n.company == company
    assert n.type == "warning"
    assert n.title == "Hello"


@pytest.mark.django_db
def test_send_in_app_channel_does_not_create_email(user, company):
    NotificationService.send(
        user=user, company=company,
        title="x", message="y", channel=Notification.Channel.IN_APP,
    )
    assert EmailLog.objects.count() == 0


@pytest.mark.django_db
def test_send_email_channel_creates_log(user, company, settings):
    """In dev with console backend, EmailLog still records the attempt."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    NotificationService.send(
        user=user, company=company,
        title="x", message="y",
        channel=Notification.Channel.EMAIL,
    )
    assert EmailLog.objects.count() == 1
    log = EmailLog.objects.first()
    assert log.status == "sent"
    assert log.to_emails == user.email


@pytest.mark.django_db
def test_send_both_channel_creates_notification_and_email(user, company, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    NotificationService.send(
        user=user, company=company,
        title="x", message="y", channel=Notification.Channel.BOTH,
    )
    assert Notification.objects.count() == 1
    assert EmailLog.objects.count() == 1


@pytest.mark.django_db
def test_send_to_user_without_email_skips_email(user, company):
    user.email = ""
    user.save()
    # Should not raise even though email is empty
    NotificationService.send(
        user=user, company=company,
        title="x", message="y", channel=Notification.Channel.BOTH,
    )
    assert Notification.objects.count() == 1
    assert EmailLog.objects.count() == 0


@pytest.mark.django_db
def test_mark_read(user, company):
    n = NotificationService.send(user=user, company=company, title="x", message="y")
    assert n.is_read is False
    ok = NotificationService.mark_read(n.id, user)
    assert ok
    n.refresh_from_db()
    assert n.is_read is True
    assert n.read_at is not None


@pytest.mark.django_db
def test_mark_read_wrong_user_returns_false(user, user2, company):
    n = NotificationService.send(user=user, company=company, title="x", message="y")
    # user2 tries to mark user's notification
    ok = NotificationService.mark_read(n.id, user2)
    assert ok is False


@pytest.mark.django_db
def test_mark_all_read(user, company):
    for i in range(5):
        NotificationService.send(user=user, company=company, title=f"x{i}", message="y")
    assert Notification.objects.filter(user=user, is_read=False).count() == 5
    NotificationService.mark_all_read(user)
    assert Notification.objects.filter(user=user, is_read=False).count() == 0


@pytest.mark.django_db
def test_send_to_superusers(company, db):
    admin = User.objects.create_superuser(
        username="admin", password="Secret123!", email="admin@test.local"
    )
    NotificationService.send_to_superusers(
        company=company, title="x", message="y"
    )
    assert Notification.objects.filter(user=admin).count() == 1


@pytest.mark.django_db
def test_email_service_get_config_returns_defaults():
    config = EmailService.get_config(company=None)
    assert "host" in config
    assert "port" in config
    assert "from_email" in config


@pytest.mark.django_db
def test_email_service_send_handles_no_recipients(company):
    ok = EmailService.send(to="", subject="x", body="y", company=company)
    assert ok is False
    log = EmailLog.objects.first()
    assert log.status == "failed"
    assert "No recipients" in log.error_message


@pytest.mark.django_db
def test_email_service_send_accepts_list_recipients(company, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    ok = EmailService.send(
        to=["a@x.co", "b@x.co"], subject="x", body="y", company=company
    )
    assert ok is True
    log = EmailLog.objects.first()
    assert "a@x.co" in log.to_emails
    assert "b@x.co" in log.to_emails


@pytest.mark.django_db
def test_voucher_post_fires_notification_to_superusers(company, db):
    """VoucherPostingService.post() should send notification to superusers."""
    from datetime import date
    from decimal import Decimal
    from apps.ledger.models import AccountingVoucher, VoucherLine
    from apps.ledger.services.voucher_posting_service import VoucherPostingService

    admin = User.objects.create_superuser(
        username="admin2", password="Secret123!", email="admin2@test.local"
    )
    v = AccountingVoucher.objects.create(
        company=company, fiscal_year=2026, period=6,
        voucher_no="TEST-NOTIF-1", voucher_type="journal",
        voucher_date=date(2026, 6, 23), currency_code="VND",
        exchange_rate=Decimal("1"), total_vnd=Decimal("100"),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(voucher=v, line_no=1, account_code="111", debit_vnd=Decimal("100"))
    VoucherLine.objects.create(voucher=v, line_no=2, account_code="111", credit_vnd=Decimal("100"))

    VoucherPostingService().post(v)
    assert Notification.objects.filter(user=admin).count() == 1
    n = Notification.objects.filter(user=admin).first()
    assert "TEST-NOTIF-1" in n.title


# ---------- Tax reminder command tests ----------

from datetime import date
from apps.notifications.management.commands.send_tax_reminders import (
    get_upcoming_deadlines,
)


@pytest.mark.django_db
def test_get_upcoming_deadlines_7_days_before(company):
    """Aug 13 → 7 days before VAT/PIT deadline (Aug 20)."""
    test_date = date(2026, 8, 13)
    deadlines = get_upcoming_deadlines(test_date)
    types = [d[0] for d in deadlines]
    assert "VAT (GTGT)" in types
    assert "TNCN (khấu trừ)" in types
    for _, _, days_left, _ in deadlines:
        assert days_left == 7


@pytest.mark.django_db
def test_get_upcoming_deadlines_1_day_before():
    """Aug 19 → 1 day before VAT/PIT deadline (Aug 20)."""
    test_date = date(2026, 8, 19)
    deadlines = get_upcoming_deadlines(test_date)
    assert len(deadlines) >= 2  # VAT + PIT
    for _, _, days_left, _ in deadlines:
        assert days_left == 1


@pytest.mark.django_db
def test_get_upcoming_deadlines_no_window():
    """July 2 → no deadlines within 7-day window."""
    deadlines = get_upcoming_deadlines(date(2026, 7, 2))
    assert len(deadlines) == 0


@pytest.mark.django_db
def test_get_upcoming_deadlines_bhxh_end_of_month():
    """July 24 → 7 days before BHXH (July 31)."""
    deadlines = get_upcoming_deadlines(date(2026, 7, 24))
    types = [d[0] for d in deadlines]
    assert "BHXH + D62" in types
    bhxh = [d for d in deadlines if d[0] == "BHXH + D62"][0]
    assert bhxh[2] == 7


@pytest.mark.django_db
def test_tax_reminder_command_sends_notifications(mocker):
    """Full command run sends notifications to admin + chief accountant."""
    from apps.identity.models import Role, UserCompanyRole
    from django.core.management import call_command

    company = Company.objects.create(code="TAXRM", name="Tax Reminder Co")
    admin_user = User.objects.create_user(
        username="taxadmin", password="Secret123!", email="taxadmin@test.local",
        is_superuser=True, is_staff=True,
    )
    accountant = User.objects.create_user(
        username="taxkt", password="Secret123!", email="taxkt@test.local",
    )
    # Create roles
    admin_role = Role.objects.create(company=company, code="admin", name="Admin")
    kt_role = Role.objects.create(company=company, code="chief_accountant", name="KTT")
    UserCompanyRole.objects.create(user=accountant, company=company, role=kt_role)

    # Mock date.today() to return Aug 13 (7 days before Aug 20 deadline)
    mock_date = mocker.patch(
        "apps.notifications.management.commands.send_tax_reminders.date"
    )
    mock_date.today.return_value = date(2026, 8, 13)
    # Make side_effect for date() constructor still work
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    call_command("send_tax_reminders")

    # Should have VAT + PIT = 2 deadline types × 2 recipients = 4 notifications
    # (accountant via role, admin via superuser+role)
    notifs = Notification.objects.filter(company=company, related_object_type="tax_reminder")
    assert notifs.count() >= 2
    titles = [n.title for n in notifs]
    assert any("VAT" in t for t in titles)
    assert any("TNCN" in t for t in titles)
    # All should be warning type (7 days left)
    assert all(n.type == Notification.Type.WARNING for n in notifs)


@pytest.mark.django_db
def test_tax_reminder_command_dedup(mocker):
    """Running command twice does not create duplicate notifications."""
    from apps.identity.models import Role, UserCompanyRole
    from django.core.management import call_command

    company = Company.objects.create(code="TAXDD", name="Tax Dedup Co")
    admin_user = User.objects.create_user(
        username="ddadmin", password="Secret123!", email="ddadmin@test.local",
        is_superuser=True, is_staff=True,
    )

    mock_date = mocker.patch(
        "apps.notifications.management.commands.send_tax_reminders.date"
    )
    mock_date.today.return_value = date(2026, 8, 13)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    call_command("send_tax_reminders")
    count1 = Notification.objects.filter(
        company=company, related_object_type="tax_reminder"
    ).count()

    call_command("send_tax_reminders")
    count2 = Notification.objects.filter(
        company=company, related_object_type="tax_reminder"
    ).count()

    assert count1 == count2  # no duplicates
    assert count1 > 0


@pytest.mark.django_db
def test_tax_reminder_command_dry_run(mocker):
    """--dry-run prints but does not create notifications."""
    from apps.identity.models import Role, UserCompanyRole
    from django.core.management import call_command
    from io import StringIO

    company = Company.objects.create(code="TAXDR", name="Tax DryRun Co")
    admin_user = User.objects.create_user(
        username="dradmin", password="Secret123!", email="dradmin@test.local",
        is_superuser=True, is_staff=True,
    )

    mock_date = mocker.patch(
        "apps.notifications.management.commands.send_tax_reminders.date"
    )
    mock_date.today.return_value = date(2026, 8, 13)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

    out = StringIO()
    call_command("send_tax_reminders", "--dry-run", stdout=out)
    output = out.getvalue()
    assert "[DRY]" in output
    assert Notification.objects.filter(
        company=company, related_object_type="tax_reminder"
    ).count() == 0

