"""HR-related ModelForms — uses DateInput widgets for date fields."""

from django import forms

from apps.hr.models import LaborContract, LeaveRecord


class LaborContractForm(forms.ModelForm):
    """Form for creating labor contracts — uses HTML5 date inputs."""

    class Meta:
        model = LaborContract
        fields = [
            "employee",
            "contract_no",
            "contract_type",
            "start_date",
            "end_date",
            "probation_end_date",
            "salary_base",
            "salary_gross",
            "allowance_amount",
            "insurance_salary_base",
            "join_insurance",
            "position_title",
            "department",
            "work_location",
            "signing_date",
            "status",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "probation_end_date": forms.DateInput(attrs={"type": "date"}),
            "signing_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class LeaveRequestForm(forms.ModelForm):
    """Form for creating leave requests — uses HTML5 date inputs."""

    class Meta:
        model = LeaveRecord
        fields = [
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "days",
            "reason",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={"rows": 3}),
        }
