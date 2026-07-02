"""Public models — Blog + Contact + Newsletter."""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

# ============ BLOG ============


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=7, default="#2563eb")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "blog_category"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogArticle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Nháp"
        PUBLISHED = "published", "Đã đăng"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    excerpt = models.TextField(blank=True, default="")
    content = models.TextField(help_text="HTML content")
    cover_image = models.ImageField(upload_to="blog/covers/", null=True, blank=True)
    category = models.ForeignKey(
        BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    tags = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_articles",
    )
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blog_article"
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:300]
        if self.status == self.Status.PUBLISHED and not self.published_at:
            from django.utils import timezone

            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []


# ============ CONTACT / LEAD CAPTURE ============


class ContactRequest(models.Model):
    """Form submission from landing/blog — auto-notifies superadmin."""

    class Source(models.TextChoices):
        LANDING = "landing", "Landing page"
        BLOG = "blog", "Blog"
        PRICING = "pricing", "Pricing page"
        DEMO = "demo", "Demo request"
        CONTACT = "contact", "Contact form"

    class Status(models.TextChoices):
        NEW = "new", "Mới"
        CONTACTED = "contacted", "Đã liên hệ"
        CONVERTED = "converted", "Đã chuyển đổi"
        REJECTED = "rejected", "Từ chối"

    # Lead info
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    company_size = models.CharField(max_length=50, blank=True, default="")
    message = models.TextField(blank=True, default="")

    # Tracking
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.LANDING)
    referrer_url = models.URLField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    # Workflow
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_contacts",
    )

    # Link to CRM lead if converted
    crm_lead_id = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contact_request"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email}) — {self.get_source_display()}"


class NewsletterSubscriber(models.Model):
    """Email capture for newsletter."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=50, default="landing")
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "newsletter_subscriber"
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email
