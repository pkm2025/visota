"""Universal attachment views — upload/delete/download for any entity."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.documents.models.attachment import Attachment
from apps.documents.services.attachment_service import AttachmentService


class AttachmentUploadView(LoginRequiredMixin, View):
    """Universal attachment upload — works for any entity."""

    login_url = "/auth/login/"

    def post(self, request):
        content_type_str = request.POST.get("content_type", "")
        object_id = request.POST.get("object_id")
        title = request.POST.get("title", "Untitled")
        attachment_type = request.POST.get("attachment_type", "other")
        description = request.POST.get("description", "")
        uploaded_file = request.FILES.get("file")

        referer = request.META.get("HTTP_REFERER", "/modern/")

        if not uploaded_file:
            messages.error(request, "Vui lòng chọn file.")
            return redirect(referer)

        if "." not in content_type_str or not object_id:
            messages.error(request, "Thiếu thông tin đối tượng đính kèm.")
            return redirect(referer)

        try:
            app_label, model = content_type_str.split(".", 1)
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            messages.error(request, f"Không tìm thấy loại đối tượng: {content_type_str}")
            return redirect(referer)

        model_class = ct.model_class()
        if model_class is None:
            messages.error(request, "Model không tồn tại.")
            return redirect(referer)

        obj = get_object_or_404(model_class, pk=object_id)
        company = getattr(obj, "company", None)

        att = AttachmentService.attach(
            obj=obj,
            title=title,
            file=uploaded_file,
            attachment_type=attachment_type,
            user=request.user,
            company=company,
            description=description,
        )

        messages.success(request, f"Đã tải lên: {att.title}")
        return redirect(referer)


class AttachmentDeleteView(LoginRequiredMixin, View):
    """Delete an attachment."""

    login_url = "/auth/login/"

    def post(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        if att.file:
            att.file.delete(save=False)
        title = att.title
        att.delete()
        messages.success(request, f"Đã xóa: {title}")
        return redirect(request.META.get("HTTP_REFERER", "/modern/"))


class AttachmentDownloadView(LoginRequiredMixin, View):
    """Download attachment file."""

    login_url = "/auth/login/"

    def get(self, request, pk):
        att = get_object_or_404(Attachment, pk=pk)
        if not att.file:
            messages.error(request, "File không tồn tại.")
            return redirect(request.META.get("HTTP_REFERER", "/modern/"))

        response = HttpResponse(att.file, content_type="application/octet-stream")
        filename = att.file.name.split("/")[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
