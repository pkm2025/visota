"""Project service — progress, cost, and resource summaries."""

from decimal import Decimal


class ProjectService:
    """Service for project management operations."""

    @staticmethod
    def calculate_progress(project):
        """Calculate project progress from phases (weighted average)."""
        phases = list(project.phases.all())
        if not phases:
            return project.progress_percent

        total_weight = sum((p.weight for p in phases), Decimal("0"))
        if total_weight == 0:
            return project.progress_percent

        completed_weight = sum((p.weight for p in phases if p.status == "completed"), Decimal("0"))
        in_progress_weight = sum(
            (p.weight * Decimal("0.5") for p in phases if p.status == "in_progress"),
            Decimal("0"),
        )

        progress = (completed_weight + in_progress_weight) / total_weight * 100
        progress = min(progress, Decimal("100"))

        project.progress_percent = progress.quantize(Decimal("0.01"))
        project.save(update_fields=["progress_percent", "updated_at"])
        return project.progress_percent

    @staticmethod
    def get_cost_summary(project):
        """Get budget vs actual cost breakdown."""
        transactions = list(project.transactions.all())
        actual_revenue = sum(
            (t.amount for t in transactions if t.transaction_type == "revenue"),
            Decimal("0"),
        )
        actual_cost = sum(
            (t.amount for t in transactions if t.transaction_type != "revenue"),
            Decimal("0"),
        )

        return {
            "budget_revenue": project.budget_revenue,
            "budget_cost": project.budget_cost,
            "actual_revenue": actual_revenue,
            "actual_cost": actual_cost,
            "revenue_variance": project.budget_revenue - actual_revenue,
            "cost_variance": project.budget_cost - actual_cost,
            "profit": actual_revenue - actual_cost,
            "margin": (
                (actual_revenue - actual_cost) / actual_revenue * 100 if actual_revenue > 0 else 0
            ),
        }

    @staticmethod
    def get_resource_summary(project):
        """Get resource allocation summary."""
        humans = list(project.resources.filter(resource_type="human").select_related("employee"))
        materials = list(
            project.resources.filter(resource_type="material").select_related("product")
        )

        human_cost_planned = sum((r.planned_cost for r in humans), Decimal("0"))
        human_cost_actual = sum((r.actual_cost for r in humans), Decimal("0"))
        material_cost_planned = sum((r.planned_cost for r in materials), Decimal("0"))
        material_cost_actual = sum((r.actual_cost for r in materials), Decimal("0"))

        return {
            "human_count": len(humans),
            "material_count": len(materials),
            "human_cost_planned": human_cost_planned,
            "human_cost_actual": human_cost_actual,
            "material_cost_planned": material_cost_planned,
            "material_cost_actual": material_cost_actual,
        }
