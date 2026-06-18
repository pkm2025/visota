"""Generic delete views for master data models.

These views do a hard delete of the record, then redirect back to the
list.  Subclasses can override :meth:`before_delete` to perform extra
checks (e.g. prevent deletion when references exist).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View


class MasterDataDeleteView(LoginRequiredMixin, View):
    """Delete a master-data record by primary key.

    Subclasses must set :attr:`model` and :attr:`redirect_name` (the URL
    name to redirect to after deletion).
    """

    model = None
    redirect_name = ""
    login_url = "/auth/login/"

    def get_redirect_url(self):
        return reverse(self.redirect_name)

    def post(self, request, pk, *args, **kwargs):
        from django.shortcuts import get_object_or_404

        instance = get_object_or_404(self.model, pk=pk)
        label = f"{getattr(instance, 'code', '')} - {getattr(instance, 'name', '')}".strip(" -")

        # Block deletion when related records reference this one.
        blocked_reasons = self.protected_reasons(instance)
        if blocked_reasons:
            messages.error(
                request,
                f"Không thể xóa {label}: " + "; ".join(blocked_reasons),
            )
            return HttpResponseRedirect(self.get_redirect_url())

        try:
            instance.delete()
            messages.success(request, f"Đã xóa {label}")
        except models.ProtectedError as e:
            related = ", ".join({str(obj) for obj in e.protected_objects} | set())
            messages.error(request, f"Không thể xóa {label}: bị tham chiếu bởi {related}")
        return HttpResponseRedirect(self.get_redirect_url())

    def get(self, request, pk, *args, **kwargs):
        return HttpResponseRedirect(self.get_redirect_url())

    def protected_reasons(self, instance):
        """Override to enumerate protection reasons; default: none."""
        return []
