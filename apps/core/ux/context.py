"""UXContext: tracks which layout × interaction style × workflow is active.

3 dimensions of UX:
1. Layout (Modern/Classic/Mobile/Portal) — set by URL prefix via TenantMiddleware
2. Interaction Style (Guided/Standard/Quick/Bulk) — from ?style= or session
3. Workflow (scratch/template/photo/import) — from ?workflow=
"""

from dataclasses import dataclass


@dataclass
class UXContext:
    """User's current UX variant: layout + interaction style + workflow."""

    layout: str = "modern"
    style: str = "standard"
    workflow: str = "scratch"

    @classmethod
    def from_request(cls, request) -> "UXContext":
        """Build UXContext from request, considering GET params + session."""
        # Layout priority: explicit attr (TenantMiddleware) > URL prefix > 'modern'
        layout = getattr(request, "current_layout", None)
        if not layout:
            path = getattr(request, "path", "") or ""
            layout = cls._layout_from_path(path)
        session = getattr(request, "session", {}) or {}

        # Style priority: GET ?style= > session pref > layout default
        get_params = getattr(request, "GET", {}) or {}
        style = (
            get_params.get("style")
            or session.get(f"ux_style_{layout}")
            or cls.default_style_for_layout(layout)
        )

        # Workflow priority: GET ?workflow= > default 'scratch'
        workflow = get_params.get("workflow", "scratch") or "scratch"

        return cls(layout=layout, style=style, workflow=workflow)

    @staticmethod
    def default_style_for_layout(layout: str) -> str:
        """Return the default interaction style for a given layout."""
        defaults = {
            "mobile": "guided",  # touch-first, simpler
            "portal": "standard",  # customer-facing, simple
            "modern": "standard",
            "classic": "standard",
        }
        return defaults.get(layout, "standard")

    def get_template(self, operation: str, template_name: str = "form.html") -> str:
        """Return full template path: '{layout}/{operation}/{style}/{template_name}'."""
        return f"{self.layout}/{operation}/{self.style}/{template_name}"

    def get_list_template(self, module: str, template_name: str = "list.html") -> str:
        """List views don't vary by style — just layout."""
        return f"{self.layout}/{module}/{template_name}"

    @staticmethod
    def _layout_from_path(path: str) -> str:
        """Infer layout code from URL path prefix (e.g. '/mobile/...' -> 'mobile')."""
        known = ("modern", "classic", "mobile", "portal")
        for code in known:
            if f"/{code}/" in path or path.startswith(f"/{code}"):
                return code
        return "modern"
