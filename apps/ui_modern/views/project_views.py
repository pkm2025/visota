"""UI views for Project Management."""

from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.contracts.models import Contract
from apps.core.models import Company
from apps.hr.models import Employee
from apps.master_data.models import Product
from apps.projects.models import (
    Project,
    ProjectPhase,
    ProjectResource,
)
from apps.projects.services import ProjectService


class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects with optional search filter."""

    template_name = "modern/projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = Project.objects.select_related("manager", "contract").order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(customer_name__icontains=search)
            )
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Dự án"
        ctx["page_parent"] = "Nghiệp vụ"
        ctx["status_choices"] = Project.Status.choices
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project."""

    model = Project
    template_name = "modern/projects/project_form.html"
    fields = [
        "code",
        "name",
        "description",
        "contract",
        "manager",
        "start_date",
        "end_date",
        "budget_revenue",
        "budget_cost",
        "status",
        "priority",
        "customer_code",
        "customer_name",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tạo dự án"
        ctx["page_parent"] = "Dự án"
        ctx["employees"] = Employee.objects.filter(status="active")
        ctx["contracts"] = Contract.objects.filter(status="active")
        ctx["status_choices"] = Project.Status.choices
        ctx["priority_choices"] = Project.Priority.choices
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:project_detail", kwargs={"pk": self.object.pk})


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """Project dashboard — phases, resources, costs, transactions."""

    template_name = "modern/projects/project_detail.html"
    context_object_name = "project"
    login_url = "/auth/login/"

    def get_queryset(self):
        return Project.objects.prefetch_related("phases", "resources", "transactions")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        from apps.documents.services.attachment_service import AttachmentService

        ctx["page_title"] = f"{project.code} - {project.name}"
        ctx["page_parent"] = "Dự án"
        ctx["cost_summary"] = ProjectService.get_cost_summary(project)
        ctx["resource_summary"] = ProjectService.get_resource_summary(project)
        ctx["progress"] = ProjectService.calculate_progress(project)
        ctx["phases"] = project.phases.all()
        ctx["resources"] = project.resources.all().select_related("employee", "product")
        ctx["transactions"] = project.transactions.all()[:20]
        ctx["employees"] = Employee.objects.filter(status="active")
        ctx["products"] = Product.objects.filter(is_active=True)
        ctx["attachments"] = AttachmentService.get_for_object(project)
        ctx["object_type"] = "projects.project"
        ctx["object_id"] = project.pk
        return ctx


class ProjectAddPhaseView(LoginRequiredMixin, View):
    """POST handler — add a phase to a project."""

    login_url = "/auth/login/"

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        name = request.POST.get("name", "").strip()
        if not name:
            return HttpResponseBadRequest("Name is required")
        sequence = int(request.POST.get("sequence", 0) or 0)
        if sequence <= 0:
            last = project.phases.order_by("-sequence").first()
            sequence = (last.sequence + 1) if last else 1
        ProjectPhase.objects.create(
            project=project,
            sequence=sequence,
            name=name,
            description=request.POST.get("description", "").strip(),
            weight=Decimal(request.POST.get("weight", "0") or "0"),
            status=request.POST.get("status", "not_started"),
        )
        ProjectService.calculate_progress(project)
        return HttpResponse(status=204)


class ProjectTogglePhaseView(LoginRequiredMixin, View):
    """POST handler — mark a phase completed / not_started."""

    login_url = "/auth/login/"

    def post(self, request, pk, phase_pk):
        project = get_object_or_404(Project, pk=pk)
        phase = get_object_or_404(ProjectPhase, project=project, pk=phase_pk)
        new_status = request.POST.get("status", "completed")
        phase.status = new_status
        if new_status == "completed":
            from django.utils import timezone

            phase.completed_at = timezone.now()
        else:
            phase.completed_at = None
        phase.save(update_fields=["status", "completed_at"])
        ProjectService.calculate_progress(project)
        return HttpResponse(status=204)


class ProjectAddResourceView(LoginRequiredMixin, View):
    """POST handler — add a resource to a project."""

    login_url = "/auth/login/"

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        resource_type = request.POST.get("resource_type", "human")
        employee_id = request.POST.get("employee") or None
        product_id = request.POST.get("product") or None
        name = request.POST.get("name", "").strip()
        role = request.POST.get("role", "").strip()
        quantity = Decimal(request.POST.get("quantity", "1") or "1")
        unit = request.POST.get("unit", "").strip()
        unit_cost = Decimal(request.POST.get("unit_cost", "0") or "0")

        ProjectResource.objects.create(
            project=project,
            resource_type=resource_type,
            employee_id=employee_id,
            product_id=product_id,
            name=name,
            role=role,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
        )
        return HttpResponse(status=204)
