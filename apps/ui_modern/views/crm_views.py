"""UI views for the CRM module."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.core.models import Company
from apps.crm.models import (
    Campaign,
    CRMAccount,
    CRMLead,
    Opportunity,
    OpportunityLine,
    Ticket,
)
from apps.crm.services import OpportunityConverter

# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------


class LeadListView(LoginRequiredMixin, ListView):
    template_name = "modern/crm/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = CRMLead.objects.select_related("assigned_to").order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(company_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        source = self.request.GET.get("source", "").strip()
        if source:
            qs = qs.filter(source=source)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Khách tiềm năng"
        ctx["page_parent"] = "CRM"
        ctx["status_choices"] = CRMLead.LeadStatus.choices
        ctx["source_choices"] = CRMLead.LeadSource.choices
        return ctx


class LeadCreateView(LoginRequiredMixin, CreateView):
    model = CRMLead
    template_name = "modern/crm/lead_form.html"
    fields = [
        "code",
        "full_name",
        "title",
        "company_name",
        "email",
        "phone",
        "mobile",
        "address",
        "tax_code",
        "source",
        "status",
        "assigned_to",
        "description",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm khách tiềm năng"
        ctx["page_parent"] = "CRM"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:crm_lead_list")


# ---------------------------------------------------------------------------
# Accounts & Contacts
# ---------------------------------------------------------------------------


class AccountCreateView(LoginRequiredMixin, CreateView):
    model = CRMAccount
    template_name = "modern/crm/account_form.html"
    fields = [
        "code",
        "name",
        "tax_code",
        "address",
        "phone",
        "email",
        "website",
        "industry",
        "assigned_to",
        "description",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm tài khoản (Account)"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:crm_opportunity_create")


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------


class OpportunityListView(LoginRequiredMixin, ListView):
    template_name = "modern/crm/opportunity_list.html"
    context_object_name = "opportunities"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = Opportunity.objects.select_related("account", "assigned_to").order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
                | Q(account__name__icontains=search)
            )
        stage = self.request.GET.get("stage", "").strip()
        if stage:
            qs = qs.filter(stage=stage)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Cơ hội bán hàng"
        ctx["page_parent"] = "CRM"
        ctx["stage_choices"] = Opportunity.Stage.choices
        return ctx


class OpportunityCreateView(LoginRequiredMixin, CreateView):
    model = Opportunity
    template_name = "modern/crm/opportunity_form.html"
    fields = [
        "code",
        "name",
        "account",
        "contact",
        "stage",
        "probability",
        "estimated_value",
        "currency_code",
        "expected_close_date",
        "assigned_to",
        "description",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm cơ hội bán hàng"
        ctx["page_parent"] = "CRM"
        ctx["is_new"] = True
        ctx["accounts"] = CRMAccount.objects.all().order_by("name")
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        response = super().form_valid(form)
        self._save_lines(self.object)
        return response

    def _save_lines(self, opportunity):
        product_ids = self.request.POST.getlist("line_product")
        quantities = self.request.POST.getlist("line_quantity")
        prices = self.request.POST.getlist("line_price")
        vat_rates = self.request.POST.getlist("line_vat")
        count = max(len(product_ids), len(quantities), len(prices))
        for i in range(count):
            try:
                pid = product_ids[i] if i < len(product_ids) else ""
                qty = quantities[i] if i < len(quantities) else "1"
                price = prices[i] if i < len(prices) else "0"
                vat = vat_rates[i] if i < len(vat_rates) else "0.08"
            except IndexError:
                continue
            if not pid and not price:
                continue
            OpportunityLine.objects.create(
                opportunity=opportunity,
                line_no=i + 1,
                product_id=pid or None,
                quantity=Decimal(qty or "1"),
                unit_price=Decimal(price or "0"),
                vat_rate=Decimal(vat or "0.08"),
            )

    def get_success_url(self):
        return reverse_lazy("ui_modern:crm_opportunity_detail", kwargs={"pk": self.object.pk})


class OpportunityDetailView(LoginRequiredMixin, DetailView):
    model = Opportunity
    template_name = "modern/crm/opportunity_detail.html"
    context_object_name = "opportunity"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.documents.services.attachment_service import AttachmentService

        ctx["page_title"] = str(self.object)
        ctx["page_parent"] = "CRM"
        ctx["activities"] = self.object.activities.all().order_by("-created_at")[:20]
        ctx["attachments"] = AttachmentService.get_for_object(self.object)
        ctx["object_type"] = "crm.opportunity"
        ctx["object_id"] = self.object.pk
        return ctx


class OpportunityConvertView(LoginRequiredMixin, View):
    """POST handler — mark opportunity WON and run OpportunityConverter."""

    login_url = "/auth/login/"

    def post(self, request, pk, *args, **kwargs):
        opportunity = get_object_or_404(Opportunity, pk=pk)
        if opportunity.stage == Opportunity.Stage.WON:
            messages.info(request, "Cơ hội đã được chuyển đổi.")
            return redirect("ui_modern:crm_opportunity_detail", pk=pk)

        opportunity.stage = Opportunity.Stage.WON
        opportunity.probability = Decimal("100")
        opportunity.save()

        company = opportunity.company or Company.objects.first()
        try:
            results = OpportunityConverter(company=company).convert(opportunity)
        except Exception as exc:  # noqa: BLE001
            opportunity.stage = Opportunity.Stage.NEGOTIATION
            opportunity.save()
            messages.error(request, f"Lỗi chuyển đổi: {exc}")
            return redirect("ui_modern:crm_opportunity_detail", pk=pk)

        messages.success(
            request,
            f"Đã tạo: Customer {results['customer'].code}, "
            f"Contract {results['contract'].contract_no}, "
            f"Project {results['project'].code}"
            + (", Invoice draft" if results.get("invoice") else ""),
        )
        return redirect("ui_modern:crm_opportunity_detail", pk=pk)


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


class TicketListView(LoginRequiredMixin, ListView):
    template_name = "modern/crm/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = Ticket.objects.select_related("assigned_to").order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(subject__icontains=search)
                | Q(customer_name__icontains=search)
            )
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        priority = self.request.GET.get("priority", "").strip()
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Chăm sóc khách hàng"
        ctx["page_parent"] = "CRM"
        ctx["status_choices"] = Ticket.Status.choices
        ctx["priority_choices"] = Ticket.Priority.choices
        return ctx


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    template_name = "modern/crm/ticket_form.html"
    fields = [
        "code",
        "subject",
        "description",
        "customer_code",
        "customer_name",
        "contact_name",
        "contact_email",
        "contact_phone",
        "priority",
        "status",
        "assigned_to",
        "related_opportunity",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm ticket hỗ trợ"
        ctx["page_parent"] = "CRM"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:crm_ticket_list")


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


class CampaignListView(LoginRequiredMixin, ListView):
    template_name = "modern/crm/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 25
    login_url = "/auth/login/"

    def get_queryset(self):
        qs = Campaign.objects.order_by("-created_at")
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Chiến dịch Marketing"
        ctx["page_parent"] = "CRM"
        ctx["status_choices"] = Campaign.Status.choices
        ctx["type_choices"] = Campaign.CampaignType.choices
        return ctx


class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    template_name = "modern/crm/campaign_form.html"
    fields = [
        "code",
        "name",
        "campaign_type",
        "status",
        "budget",
        "actual_cost",
        "start_date",
        "end_date",
        "description",
    ]
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Thêm chiến dịch"
        ctx["page_parent"] = "CRM"
        ctx["is_new"] = True
        return ctx

    def form_valid(self, form):
        form.instance.company = Company.objects.first()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("ui_modern:crm_campaign_list")
