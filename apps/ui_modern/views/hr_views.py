"""HR UI views — employee list + create."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.hr.models import Employee
from apps.ui_modern.mixins import PermissionRequiredMixin, require_current_company


class EmployeeListView(LoginRequiredMixin, ListView):
    """List of employees for the current company."""

    template_name = "modern/hr/employee_list.html"
    context_object_name = "employees"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        company = require_current_company(self.request)
        qs = (
            Employee.objects.filter(company=company)
            .select_related("department", "position")
            .order_by("code")
        )
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(code__icontains=search) | qs.filter(full_name__icontains=search)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Nhân viên"
        ctx["status_choices"] = Employee.Status.choices
        return ctx


class EmployeeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create a new employee (Django generic CreateView)."""

    model = Employee
    template_name = "modern/hr/employee_form.html"
    fields = [
        "code",
        "full_name",
        "birth_date",
        "gender",
        "id_card_no",
        "personal_tax_code",
        "social_insurance_no",
        "phone",
        "email",
        "address",
        "department",
        "position",
        "hire_date",
        "probation_end_date",
        "official_date",
        "base_salary",
        "allowance",
        "bank_account_no",
        "bank_id",
        "status",
        "notes",
    ]
    login_url = "/auth/login/"
    required_permission = "hr.access"
    success_url = reverse_lazy("ui_modern:employee_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm nhân viên"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = require_current_company(self.request)
        return super().form_valid(form)
