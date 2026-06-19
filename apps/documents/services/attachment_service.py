"""Service for attaching files to any model instance."""

from django.contrib.contenttypes.models import ContentType

from apps.documents.models.attachment import Attachment


class AttachmentService:
    """Operations on universal attachments."""

    @staticmethod
    def get_for_object(obj):
        """Get all attachments for any model instance."""
        ct = ContentType.objects.get_for_model(obj)
        return Attachment.objects.filter(content_type=ct, object_id=obj.pk)

    @staticmethod
    def attach(obj, title, file, attachment_type="other", user=None, company=None, description=""):
        """Attach a file to any model instance."""
        ct = ContentType.objects.get_for_model(obj)
        # Resolve company: explicit param > object.company_id > object.company > None
        if company is not None:
            company_id = company.id if hasattr(company, "id") else company
        elif getattr(obj, "company_id", None):
            company_id = obj.company_id
        elif getattr(obj, "company", None) is not None:
            company_id = obj.company.id
        else:
            company_id = None

        return Attachment.objects.create(
            content_type=ct,
            object_id=obj.pk,
            company_id=company_id,
            title=title,
            description=description,
            file=file,
            attachment_type=attachment_type,
            uploaded_by=user,
        )

    @staticmethod
    def get_by_type(obj, attachment_type):
        """Get attachments of a specific type for an object."""
        ct = ContentType.objects.get_for_model(obj)
        return Attachment.objects.filter(
            content_type=ct, object_id=obj.pk, attachment_type=attachment_type
        )
