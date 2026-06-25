"""Public URL routes — landing + blog + contact + newsletter + signup."""

from django.urls import path

from .views import (
    BlogDetailView,
    BlogListView,
    ContactListAdminView,
    ContactSubmitView,
    ContactUpdateStatusView,
    LandingPageView,
    NewsletterSubscribeView,
    SignupView,
)

app_name = "public"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("blog/", BlogListView.as_view(), name="blog_list"),
    path("blog/<slug:slug>/", BlogDetailView.as_view(), name="blog_detail"),
    path("contact/submit/", ContactSubmitView.as_view(), name="contact_submit"),
    path("newsletter/subscribe/", NewsletterSubscribeView.as_view(), name="newsletter_subscribe"),
    path("admin/contacts/", ContactListAdminView.as_view(), name="admin_contact_list"),
    path("admin/contacts/<int:pk>/status/", ContactUpdateStatusView.as_view(), name="admin_contact_status"),
]
