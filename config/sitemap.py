"""Sitemap configuration for visota.net.

Exposes the homepage and key public pages (blog, signup, legal) so search
engines can discover them via /sitemap.xml.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for static public-facing views served under the `public` namespace."""

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "public:landing",
            "public:blog_list",
            "public:signup",
            "public:terms",
            "public:privacy",
        ]

    def location(self, item):
        return reverse(item)
