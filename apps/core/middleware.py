"""Tenant and branding middleware."""

DEFAULT_BRAND = {
    "name": "PMKetoan",
    "logo": "/static/images/logo.svg",
    "logo_dark": "/static/images/logo-dark.svg",
    "primary_color": "#2563eb",
    "accent_color": "#16a34a",
    "favicon": "/static/images/favicon.ico",
    "hide_pmketoan_branding": False,
    "custom_css": "",
}


class TenantMiddleware:
    """Detect current layout from URL path."""

    LAYOUT_PREFIXES = {
        "/modern/": "modern",
        "/classic/": "classic",
        "/mobile/": "mobile",
        "/portal/": "portal",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_layout = self._detect_layout(request.path)
        request.current_company = self._get_current_company(request)
        return self.get_response(request)

    def _detect_layout(self, path: str) -> str:
        for prefix, layout in self.LAYOUT_PREFIXES.items():
            if path.startswith(prefix):
                return layout
        return "modern"

    def _get_current_company(self, request):
        if not hasattr(request, "session"):
            return None
        company_id = request.session.get("current_company_id")
        if not company_id:
            return None
        from apps.core.models import Company

        return Company.objects.filter(id=company_id, is_active=True).first()


class BrandingMiddleware:
    """Set request.brand from current company."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company = getattr(request, "current_company", None)
        if company:
            request.brand = {
                "name": company.display_name,
                "logo": company.brand_logo.url if company.brand_logo else DEFAULT_BRAND["logo"],
                "logo_dark": company.brand_logo_dark.url
                if company.brand_logo_dark
                else DEFAULT_BRAND["logo_dark"],
                "primary_color": company.brand_primary_color,
                "accent_color": company.brand_accent_color,
                "favicon": company.brand_favicon.url
                if company.brand_favicon
                else DEFAULT_BRAND["favicon"],
                "hide_pmketoan_branding": company.hide_pmketoan_branding,
                "custom_css": company.custom_css,
                "stamp": company.company_stamp.url if company.company_stamp else "",
                "company": company,  # full object for templates
            }
        else:
            request.brand = DEFAULT_BRAND.copy()
        return self.get_response(request)
