"""Generic delete views for master data models.

These views do a hard delete of the record, then redirect back to the
list.  Subclasses can override :meth:`before_delete` to perform extra
checks (e.g. prevent deletion when references exist).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from ..mixins import require_current_company


class MasterDataDeleteView(LoginRequiredMixin, View):
    """Delete a master-data record by primary key.

    Subclasses must set :attr:`model` and :attr:`redirect_name` (the URL
    name to redirect to after deletion).

    VAL-SEC-003: the lookup is scoped to ``request.current_company`` so
    a user cannot delete another tenant's master-data record by guessing
    its primary key.
    """

    model = None
    redirect_name = ""
    login_url = "/auth/login/"

    def get_redirect_url(self):
        return reverse(self.redirect_name)

    def _scope_kwargs(self, request):
        """Return filter kwargs that pin the lookup to the current company.

        Falls back to ``{}`` for models that don't expose a ``company`` FK
        (so this base remains safe to use across master-data models).
        """
        company = require_current_company(request)
        if any(f.name == "company" for f in self.model._meta.get_fields()):
            return {"company": company}
        return {}

    def post(self, request, pk, *args, **kwargs):
        instance = get_object_or_404(self.model, pk=pk, **self._scope_kwargs(request))
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
