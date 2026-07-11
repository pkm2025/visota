"""Global "super search" registry and service.

Searches across many object types, scoped to the current company and the
modules the user has access to. Result groups are personalized: their order
follows a time-decayed per-user click affinity so frequently used object
types surface first.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.parse import urlencode

from django.apps import apps
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

PER_TYPE_LIMIT = 5
_HALF_LIFE_DAYS = 30.0
_DECAY = math.log(2) / _HALF_LIFE_DAYS


@dataclass(frozen=True)
class SearchType:
    key: str
    label: str
    icon: str
    module: str  # permission is "<module>.access"
    model_path: str  # "app_label.ModelName"
    fields: tuple[str, ...]  # fields matched with icontains
    code_field: str  # primary display value
    name_field: str | None  # secondary display value
    list_url: str  # fallback list url name (ui_modern namespace)
    detail_url: str | None = None  # detail url name taking pk
    list_param: str = "search"

    def get_model(self):
        app_label, model_name = self.model_path.split(".")
        return apps.get_model(app_label, model_name)


# Order here is the default ordering (used when no personalization exists yet).
REGISTRY: tuple[SearchType, ...] = (
    SearchType(
        key="customer",
        label="Khách hàng",
        icon="bi-people",
        module="sales",
        model_path="master_data.Customer",
        fields=("code", "name", "name_en", "short_name", "tax_code", "phone"),
        code_field="code",
        name_field="name",
        list_url="customer_list",
        detail_url="customer_update",
    ),
    SearchType(
        key="vendor",
        label="Nhà cung cấp",
        icon="bi-truck",
        module="purchasing",
        model_path="master_data.Vendor",
        fields=("code", "name", "name_en", "short_name", "tax_code", "phone"),
        code_field="code",
        name_field="name",
        list_url="vendor_list",
        detail_url="vendor_update",
    ),
    SearchType(
        key="product",
        label="Hàng hóa",
        icon="bi-box",
        module="master_data",
        model_path="master_data.Product",
        fields=("code", "name", "name_en", "barcode"),
        code_field="code",
        name_field="name",
        list_url="product_list",
        detail_url="product_detail",
    ),
    SearchType(
        key="voucher",
        label="Phiếu kế toán",
        icon="bi-receipt",
        module="ledger",
        model_path="ledger.AccountingVoucher",
        fields=("voucher_no", "book_code"),
        code_field="voucher_no",
        name_field=None,
        list_url="voucher_list",
        detail_url="voucher_detail",
    ),
    SearchType(
        key="sales_invoice",
        label="Hóa đơn bán",
        icon="bi-receipt-cutoff",
        module="sales",
        model_path="sales.SalesInvoice",
        fields=("invoice_no",),
        code_field="invoice_no",
        name_field=None,
        list_url="sales_invoice_list",
    ),
    SearchType(
        key="purchase_invoice",
        label="Phiếu nhập mua",
        icon="bi-bag",
        module="purchasing",
        model_path="purchasing.PurchaseInvoice",
        fields=("invoice_no",),
        code_field="invoice_no",
        name_field=None,
        list_url="purchase_invoice_list",
    ),
    SearchType(
        key="employee",
        label="Nhân viên",
        icon="bi-person-badge",
        module="hr",
        model_path="hr.Employee",
        fields=("code", "full_name", "phone", "personal_tax_code"),
        code_field="code",
        name_field="full_name",
        list_url="employee_list",
    ),
    SearchType(
        key="asset",
        label="Tài sản",
        icon="bi-bounding-box",
        module="assets",
        model_path="assets.FixedAsset",
        fields=("asset_code", "asset_name", "asset_name_en"),
        code_field="asset_code",
        name_field="asset_name",
        list_url="asset_list",
    ),
    SearchType(
        key="contract",
        label="Hợp đồng",
        icon="bi-file-earmark-text",
        module="contracts",
        model_path="contracts.Contract",
        fields=("contract_no", "party_name", "party_tax_code"),
        code_field="contract_no",
        name_field="party_name",
        list_url="contract_list",
        detail_url="contract_detail",
    ),
    SearchType(
        key="project",
        label="Dự án",
        icon="bi-kanban",
        module="projects",
        model_path="projects.Project",
        fields=("code", "name", "customer_name"),
        code_field="code",
        name_field="name",
        list_url="project_list",
        detail_url="project_detail",
    ),
    SearchType(
        key="crm_lead",
        label="Khách tiềm năng",
        icon="bi-person-plus",
        module="crm",
        model_path="crm.CRMLead",
        fields=("code", "full_name", "company_name", "phone", "tax_code"),
        code_field="full_name",
        name_field="company_name",
        list_url="crm_lead_list",
    ),
    SearchType(
        key="crm_opportunity",
        label="Cơ hội bán hàng",
        icon="bi-briefcase",
        module="crm",
        model_path="crm.Opportunity",
        fields=("code", "name"),
        code_field="code",
        name_field="name",
        list_url="crm_opportunity_list",
        detail_url="crm_opportunity_detail",
    ),
    SearchType(
        key="bid",
        label="Cơ hội đấu thầu",
        icon="bi-briefcase",
        module="bidding",
        model_path="bidding.BidOpportunity",
        fields=("bid_no", "bid_name", "investor_name"),
        code_field="bid_no",
        name_field="bid_name",
        list_url="bid_list",
        detail_url="bid_detail",
    ),
)

_BY_KEY = {t.key: t for t in REGISTRY}


def is_valid_type(key: str) -> bool:
    return key in _BY_KEY


def _permitted_types(user, company) -> list[SearchType]:
    if getattr(user, "is_superuser", False):
        return list(REGISTRY)
    from apps.identity.services import UserService

    service = UserService(user, company)
    return [t for t in REGISTRY if service.has_permission(f"{t.module}.access")]


def _order_by_affinity(user, company, types: list[SearchType]) -> list[SearchType]:
    from apps.core.models import UserSearchAffinity

    scores = dict(
        UserSearchAffinity.objects.filter(user=user, company=company).values_list(
            "object_type", "score"
        )
    )
    default_pos = {t.key: i for i, t in enumerate(types)}
    return sorted(types, key=lambda t: (-scores.get(t.key, 0.0), default_pos[t.key]))


def _build_url(t: SearchType, obj) -> str:
    if t.detail_url:
        try:
            return reverse(f"ui_modern:{t.detail_url}", kwargs={"pk": obj.pk})
        except NoReverseMatch:
            pass
    base = reverse(f"ui_modern:{t.list_url}")
    code = getattr(obj, t.code_field, "") or ""
    if code:
        return f"{base}?{urlencode({t.list_param: code})}"
    return base


def search(user, company, query: str, per_type: int = PER_TYPE_LIMIT) -> list[dict]:
    """Return personalized, permission-scoped result groups.

    Each group holds at most ``per_type`` items plus a ``has_more`` flag.
    """
    query = (query or "").strip()
    if not query or not company:
        return []

    types = _order_by_affinity(user, company, _permitted_types(user, company))
    groups: list[dict] = []

    for t in types:
        model = t.get_model()
        q = Q()
        for field in t.fields:
            q |= Q(**{f"{field}__icontains": query})
        rows = list(model.objects.filter(company=company).filter(q)[: per_type + 1])
        if not rows:
            continue
        has_more = len(rows) > per_type
        items = []
        for obj in rows[:per_type]:
            code = getattr(obj, t.code_field, "") or ""
            name = getattr(obj, t.name_field, "") if t.name_field else ""
            items.append({"code": code, "name": name, "url": _build_url(t, obj)})
        groups.append(
            {
                "key": t.key,
                "label": t.label,
                "icon": t.icon,
                "items": items,
                "has_more": has_more,
                "list_url": reverse(f"ui_modern:{t.list_url}")
                + f"?{urlencode({t.list_param: query})}",
            }
        )
    return groups


def record_click(user, company, object_type: str) -> None:
    """Increment a user's affinity for an object type with time decay."""
    from apps.core.models import UserSearchAffinity

    affinity, created = UserSearchAffinity.objects.get_or_create(
        user=user,
        company=company,
        object_type=object_type,
        defaults={"score": 1.0},
    )
    if created:
        return
    elapsed_days = (timezone.now() - affinity.updated_at).total_seconds() / 86400.0
    affinity.score = affinity.score * math.exp(-_DECAY * elapsed_days) + 1.0
    affinity.save(update_fields=["score", "updated_at"])
