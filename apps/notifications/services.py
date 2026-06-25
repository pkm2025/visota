"""Notification + Email services.

NotificationService.send() is the single entry point — handles inbox + email
based on channel. EmailService wraps Django's send_mail with logging.
"""

from django.conf import settings
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import Company
from apps.identity.models import User

from .models import EmailLog, Notification


class EmailService:
    """SMTP email sender with logging."""

    @staticmethod
    def get_config(company=None):
        """Read SMTP config from settings — can be extended to per-company DB."""
        return {
            "host": getattr(settings, "EMAIL_HOST", "localhost"),
            "port": getattr(settings, "EMAIL_PORT", 25),
            "username": getattr(settings, "EMAIL_HOST_USER", ""),
            "password": getattr(settings, "EMAIL_HOST_PASSWORD", ""),
            "use_tls": getattr(settings, "EMAIL_USE_TLS", True),
            "from_email": getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pmketoan.local"),
        }

    @classmethod
    def send(
        cls,
        *,
        to,
        subject,
        body,
        cc=None,
        company=None,
        sent_by=None,
        related_object_type="",
        related_object_id=None,
        html_body=None,
    ):
        """Send email + log result. Returns True on success."""
        if isinstance(to, str):
            to_list = [t.strip() for t in to.split(",") if t.strip()]
        else:
            to_list = list(to)

        config = cls.get_config(company)
        log = EmailLog.objects.create(
            company=company,
            from_email=config["from_email"],
            to_emails=",".join(to_list),
            cc_emails=",".join(cc) if cc else "",
            subject=subject,
            body=body,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            sent_by=sent_by,
        )

        if not to_list:
            log.status = "failed"
            log.error_message = "No recipients"
            log.save()
            return False

        try:
            connection = get_connection(
                host=config["host"],
                port=config["port"],
                username=config["username"] or None,
                password=config["password"] or None,
                use_tls=config["use_tls"],
            )
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=config["from_email"],
                to=to_list,
                cc=cc,
                connection=connection,
            )
            if html_body:
                msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
            log.status = "sent"
            log.save()
            return True
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)[:1000]
            log.save()
            # In dev, swallow — email is best-effort
            if getattr(settings, "DEBUG", False):
                return False
            raise


class NotificationService:
    """Single entry point for sending notifications."""

    @staticmethod
    def send(
        *,
        user,
        title,
        message,
        type=Notification.Type.INFO,
        url="",
        company=None,
        related_object_type="",
        related_object_id=None,
        channel=Notification.Channel.IN_APP,
        email_subject=None,
        email_body=None,
    ):
        """Send notification to a single user. Returns the Notification object."""
        notif = Notification.objects.create(
            user=user,
            company=company,
            type=type,
            title=title,
            message=message,
            url=url or "",
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )

        if channel in (Notification.Channel.EMAIL, Notification.Channel.BOTH):
            if not user.email:
                return notif
            EmailService.send(
                to=user.email,
                subject=email_subject or title,
                body=email_body or message,
                company=company,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
            )
        return notif

    @staticmethod
    def send_to_role(
        *,
        role_code,
        company,
        title,
        message,
        **kwargs,
    ):
        """Broadcast to every user with a specific role at this company."""
        from apps.identity.models import Role, UserCompanyRole

        role = Role.objects.filter(code=role_code, company=company).first()
        if not role:
            return []
        user_ids = UserCompanyRole.objects.filter(
            role=role, company=company
        ).values_list("user_id", flat=True)
        notifs = []
        for uid in user_ids:
            u = User.objects.get(id=uid)
            n = NotificationService.send(
                user=u, company=company, title=title, message=message, **kwargs
            )
            notifs.append(n)
        return notifs

    @staticmethod
    def send_to_superusers(company, title, message, **kwargs):
        """Broadcast to all superusers (admin alerts)."""
        notifs = []
        for u in User.objects.filter(is_superuser=True, is_active=True):
            n = NotificationService.send(
                user=u, company=company, title=title, message=message, **kwargs
            )
            notifs.append(n)
        return notifs

    @staticmethod
    def mark_read(notification_id, user):
        try:
            n = Notification.objects.get(id=notification_id, user=user)
            n.is_read = True
            n.read_at = timezone.now()
            n.save()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_read(user):
        Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
