"""Public views — landing + blog + contact + newsletter."""

from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from .models import BlogArticle, BlogCategory, ContactRequest, NewsletterSubscriber


# ============ LANDING PAGE ============

class LandingPageView(View):
    def get(self, request):
        featured = BlogArticle.objects.filter(status="published", featured=True).order_by("-published_at")[:3]
        latest = BlogArticle.objects.filter(status="published").order_by("-published_at")[:6]
        return render(request, "public/landing.html", {
            "featured_articles": featured,
            "latest_articles": latest,
        })


# ============ BLOG ============

class BlogListView(ListView):
    template_name = "public/blog_list.html"
    context_object_name = "articles"
    paginate_by = 9

    def get_queryset(self):
        qs = BlogArticle.objects.filter(status="published").select_related("category", "author")
        cat = self.request.GET.get("category")
        if cat:
            qs = qs.filter(category__slug=cat)
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(excerpt__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = BlogCategory.objects.filter(is_active=True)
        ctx["active_category"] = self.request.GET.get("category", "")
        return ctx


class BlogDetailView(DetailView):
    template_name = "public/blog_detail.html"
    context_object_name = "article"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return BlogArticle.objects.filter(status="published").select_related("category", "author")

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.view_count += 1
        self.object.save(update_fields=["view_count"])
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.object
        ctx["related"] = (
            BlogArticle.objects.filter(status="published", category=article.category)
            .exclude(id=article.id).order_by("-published_at")[:3]
        )
        ctx["categories"] = BlogCategory.objects.filter(is_active=True)
        return ctx


# ============ CONTACT FORM ============

class ContactSubmitView(View):
    """POST: handle contact form from landing/blog. Creates ContactRequest + notifies admin."""

    def post(self, request, *args, **kwargs):
        source = request.POST.get("source", "landing")
        cr = ContactRequest.objects.create(
            full_name=request.POST.get("full_name", "").strip(),
            email=request.POST.get("email", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            company_name=request.POST.get("company_name", "").strip(),
            company_size=request.POST.get("company_size", "").strip(),
            message=request.POST.get("message", "").strip(),
            source=source,
            referrer_url=request.POST.get("referrer", ""),
            ip_address=self._get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        # Fire notification to all superusers
        try:
            from apps.notifications.services import NotificationService
            from apps.core.models import Company
            company = Company.objects.first()
            if company:
                NotificationService.send_to_superusers(
                    company=company,
                    type="info",
                    title=f"Liên hệ mới: {cr.full_name}",
                    message=(
                        f"{cr.full_name} ({cr.email}) từ {cr.company_name or '—'} "
                        f"đã gửi yêu cầu qua {cr.get_source_display()}.\n"
                        f"SĐT: {cr.phone or '—'}\n"
                        f"Nội dung: {cr.message[:100] if cr.message else '—'}"
                    ),
                    url="/modern/admin/contacts/",
                    related_object_type="public.contactrequest",
                    related_object_id=cr.id,
                )
        except Exception:
            pass  # notification failure shouldn't block form

        # Also try email
        try:
            from apps.notifications.services import EmailService
            from apps.core.models import Company
            company = Company.objects.first()
            admins = [u.email for u in __import__('apps.identity.models', fromlist=['User']).User.objects.filter(is_superuser=True, email__isnull=False).exclude(email="")]
            if admins and company:
                EmailService.send(
                    to=admins,
                    subject=f"[visota.net] Liên hệ mới: {cr.full_name}",
                    body=(
                        f"Có liên hệ mới từ website visota.net:\n\n"
                        f"Họ tên: {cr.full_name}\n"
                        f"Email: {cr.email}\n"
                        f"SĐT: {cr.phone or '—'}\n"
                        f"Công ty: {cr.company_name or '—'}\n"
                        f"Nguồn: {cr.get_source_display()}\n\n"
                        f"Nội dung:\n{cr.message or '—'}\n"
                    ),
                    company=company,
                )
        except Exception:
            pass

        # JSON response for AJAX, redirect for normal POST
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "id": cr.id})
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/") + "?contact=success")

    def _get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# ============ NEWSLETTER ============

class NewsletterSubscribeView(View):
    """POST: subscribe email to newsletter."""

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email", "").strip().lower()
        if not email or "@" not in email:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": "Email không hợp lệ"})
            return HttpResponseRedirect("/")

        sub, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={"name": request.POST.get("name", ""), "source": "landing"},
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "created": created})
        return HttpResponseRedirect("/?newsletter=success")


# ============ ADMIN: Contact list ============

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView as AdminListView


class ContactListAdminView(LoginRequiredMixin, AdminListView):
    """Admin: list all contact requests."""

    template_name = "modern/admin/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = ContactRequest.objects.all().select_related("assigned_to")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Yêu cầu liên hệ"
        ctx["status_choices"] = ContactRequest.Status.choices
        ctx["new_count"] = ContactRequest.objects.filter(status="new").count()
        return ctx


class ContactUpdateStatusView(LoginRequiredMixin, View):
    """POST: update contact status (mark contacted/converted/rejected)."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        cr = get_object_or_404(ContactRequest, pk=pk)
        new_status = request.POST.get("status")
        if new_status in [c[0] for c in ContactRequest.Status.choices]:
            cr.status = new_status
            cr.notes = request.POST.get("notes", cr.notes)
            cr.save()
        from django.contrib import messages
        messages.success(request, f"Đã cập nhật trạng thái '{cr.get_status_display()}' cho {cr.full_name}.")
        return redirect("ui_modern:admin_contact_list")
