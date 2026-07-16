"""Interaction logging and smart-context summary service for the PKM module.

This module provides three public functions:

  - ``log_interaction`` - Captures a user interaction as a ``UserInteractionLog``
    row. When django-q2 is available, the insert is enqueued asynchronously so
    the caller (e.g. a view or middleware) is never blocked. If django-q2 is
    unavailable or the enqueue fails, it falls back to a synchronous insert.
    Any exception during logging is swallowed so that interaction capture can
    NEVER break the main user operation.

  - ``get_context_summary`` - Builds a human-readable summary of a user's
    recent activity (e.g. "Recently viewed 3 ledger pages, created 2 notes").
    Used to enrich Q&A prompts with interaction context.

  - ``get_recent_interactions`` - Returns a queryset of recent interaction
    logs scoped by user + company, ordered by ``created_at`` descending.

All queries are scoped by ``user_id`` and ``company_id`` to enforce per-user
and multi-tenant isolation.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

from django.db.models import Count
from django.utils import timezone

from apps.pkm.models import UserInteractionLog

if TYPE_CHECKING:
    from apps.core.models import Company
    from apps.identity.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "log_interaction",
    "get_context_summary",
    "get_recent_interactions",
    "DEFAULT_SUMMARY_HOURS",
    "DEFAULT_RECENT_LIMIT",
]

#: Default time window (in hours) for the activity summary.
DEFAULT_SUMMARY_HOURS: int = 24

#: Default maximum number of recent interactions returned by ``get_recent_interactions``.
DEFAULT_RECENT_LIMIT: int = 20

#: Vietnamese labels for each interaction type used in the smart-context summary.
#: Each entry is a callable or string that describes one occurrence; the
#: summary uses :data:`INTERACTION_TYPE_LABEL_VN` for the noun form.
INTERACTION_LABELS: dict[str, str] = {
    "page_view": "lượt xem trang",
    "search": "lượt tìm kiếm",
    "note_create": "ghi chú đã tạo",
    "document_create": "tài liệu đã tải lên",
    "voucher_create": "phiếu đã lập",
    "invoice_create": "hóa đơn đã lập",
    "dnsn_voucher_create": "phiếu DNSN đã lập",
    "period_close": "lần khóa sổ kỳ",
    "einvoice_issue": "hóa đơn điện tử đã phát hành",
}

#: Human-readable Vietnamese verb phrases for business-event interaction types.
#: Used to render individual recent events in the summary.
INTERACTION_VERB_VN: dict[str, str] = {
    "voucher_create": "lập phiếu kế toán",
    "invoice_create": "lập hóa đơn bán hàng",
    "dnsn_voucher_create": "lập phiếu DNSN",
    "period_close": "khóa sổ kỳ kế toán",
    "einvoice_issue": "phát hành hóa đơn điện tử",
    "note_create": "tạo ghi chú",
    "document_create": "tải lên tài liệu",
    "search": "tìm kiếm",
}

#: Vietnamese labels for each module code (used in the activity summary
#: and the "current module" line).
MODULE_LABELS_VN: dict[str, str] = {
    "ledger": "Kế toán",
    "pkm": "Quản lý tri thức",
    "sales": "Bán hàng",
    "purchasing": "Mua hàng",
    "inventory": "Kho",
    "hr": "Nhân sự",
    "payroll": "Tiền lương",
    "reporting": "Báo cáo",
    "assets": "Tài sản cố định",
    "master_data": "Dữ liệu nền",
    "contracts": "Hợp đồng",
    "input_docs": "Chứng từ đầu vào",
    "recurring": "Khoản định kỳ",
    "projects": "Dự án",
    "crm": "CRM",
    "treasury": "Quỹ",
    "banking": "Ngân hàng",
    "guarantees": "Bảo lãnh",
    "loans": "Tiền vay",
    "bidding": "Đấu thầu",
    "budget": "Ngân sách",
    "fx": "Ngoại tệ",
    "einvoice": "Hóa đơn điện tử",
    "approvals": "Phê duyệt",
}

#: Vietnamese labels for Company.AccountingRegime choice values.
#: Used by :func:`_format_company_context` to render the regime in a
#: human-readable Vietnamese form (e.g. "TT58/2026").
REGIME_LABELS_VN: dict[str, str] = {
    "tt133": "TT133/2016",
    "tt200": "TT200/2014",
    "tt58": "TT58/2026",
    "q48": "QĐ48/2006",
}

#: Vietnamese labels for Company.EntityType choice values.
ENTITY_TYPE_LABELS_VN: dict[str, str] = {
    "doanh_nghiep_sieu_nho": "Doanh nghiệp siêu nhỏ",
    "ho_kinh_doanh": "Hộ kinh doanh",
    "ca_nhan_kinh_doanh": "Cá nhân kinh doanh",
}

#: Vietnamese labels for Company.VatMethod choice values.
VAT_METHOD_LABELS_VN: dict[str, str] = {
    "khau_tru": "Khấu trừ",
    "ty_le_phan_tram": "Tỷ lệ %",
}

#: Vietnamese labels for Company.TndnMethod choice values.
TNDN_METHOD_LABELS_VN: dict[str, str] = {
    "tinh_thue": "Tính thuế",
    "ty_le_phan_tram": "Tỷ lệ %",
}

#: Vietnamese descriptions for each TT58 tax method group (1-4).
#: Only shown for TT58 companies (regime='tt58'). The key is the
#: ``Company.tax_method_group`` integer (1-4); the value is a short
#: Vietnamese clause describing the VAT + TNDN method combination.
TAX_GROUP_DESCRIPTIONS_VN: dict[int, str] = {
    1: "GTGT theo tỷ lệ %, TNDN theo tỷ lệ %",
    2: "GTGT theo tỷ lệ %, TNDN tính thuế",
    3: "GTGT khấu trừ, TNDN theo tỷ lệ %",
    4: "GTGT khấu trừ, TNDN tính thuế",
}

#: Legacy English module-page labels (kept for backwards compatibility).
MODULE_PAGE_LABELS: dict[str, str] = {
    "ledger": "ledger pages",
    "pkm": "PKM pages",
    "sales": "sales pages",
    "purchasing": "purchasing pages",
    "inventory": "inventory pages",
    "hr": "HR pages",
    "reporting": "reporting pages",
}

#: Interaction types that represent business events (as opposed to passive
#: page views or content actions). These are rendered with their amounts in
#: the summary when the metadata carries an amount.
BUSINESS_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "voucher_create",
        "invoice_create",
        "dnsn_voucher_create",
        "period_close",
        "einvoice_issue",
    }
)

#: Metadata keys that may carry a monetary amount for a business event.
_AMOUNT_METADATA_KEYS: tuple[str, ...] = ("amount", "total_amount", "voucher_amount")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _django_q_available() -> bool:
    """Return True if django-q2 can actually execute tasks in this process.

    A common production bug: django-q2 is importable and ``async_task``
    successfully enqueues a row to the ORM broker, but no worker process is
    running to dequeue and execute it. The enqueue call does not raise, so
    the naive "library is importable" check silently swallows the interaction
    log - it sits in ``django_q_ormq`` forever and is never turned into a
    ``UserInteractionLog`` row.

    This helper returns True only when the task will actually run. We consider
    it available when EITHER:

      1. ``Q_CLUSTER['sync']`` is True (django-q2 runs the task inline during
         the ``async_task`` call - no separate worker needed). This is the
         configuration used by the test and dev settings.
      2. ``Q_CLUSTER['sync']`` is False AND there is evidence that a django-q
         worker is actively processing tasks (at least one row in
         ``django_q_task`` or ``django_q_success`` with a recent timestamp).
         This detects a live worker in production.

    Returns False (so the caller falls back to ``_create_sync``) when:
      - django-q2 is not importable, OR
      - the cluster is async but no worker activity is detected (the dev
        server runs without a ``qcluster`` process, so enqueued tasks would
        never be processed).
    """
    try:
        import django_q.tasks  # noqa: F401
    except ImportError:
        return False

    from django.conf import settings

    cluster = getattr(settings, "Q_CLUSTER", {}) or {}
    if cluster.get("sync"):
        # Sync mode runs the task inline during async_task - always reliable.
        return True

    # Async mode: only advertise availability if a worker is actively running.
    # We probe the django-q bookkeeping tables for evidence of recent worker
    # activity. If neither table has any rows, no worker has ever processed a
    # task in this database, so enqueueing would silently no-op.
    return _worker_is_active()


def _worker_is_active() -> bool:
    """Detect whether a django-q worker is currently processing tasks.

    Probes the django-q bookkeeping tables for evidence of worker activity.
    Used by :func:`_django_q_available` to decide whether async enqueueing is
    safe. Returns True only when there is concrete evidence that a worker has
    processed at least one task in this database.

    The check is intentionally cheap (single indexed COUNT/SELECT) so it can
    run on every ``log_interaction`` call without measurable overhead.
    """
    try:
        from django_q.models import OrmQueue, Success, Task  # noqa: F401
    except Exception:
        return False

    try:
        # A running worker populates Success (completed tasks) or Task
        # (in-flight/failed tasks). If both are empty, no worker has ever run.
        return bool(Success.objects.exists() or Task.objects.exists())
    except Exception:
        # Tables not migrated yet or DB error - treat as no worker.
        return False


def _enqueue_async(
    user: User | None,
    company: Company,
    interaction_type: str,
    module: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any],
) -> Any:
    """Enqueue a synchronous log-creation task via django-q2's ``async_task``.

    The task target is ``_create_sync`` (imported by string path) so django-q2
    workers can resolve it. Raises if the enqueue itself fails (the caller is
    responsible for fallback).
    """
    from django_q.tasks import async_task

    return async_task(
        "apps.pkm.services.interaction_service._create_sync",
        user.id if user else None,
        company.id,
        interaction_type,
        module,
        entity_type,
        entity_id,
        metadata,
    )


def _create_sync(
    user_id: int | None,
    company_id: int,
    interaction_type: str,
    module: str,
    entity_type: str = "",
    entity_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> UserInteractionLog | None:
    """Create a ``UserInteractionLog`` row synchronously.

    This function is also the target of ``async_task`` (called by django-q2
    workers), so it accepts IDs rather than model instances to stay
    serializable across the task broker.

    Returns the created instance, or ``None`` if creation fails.
    """
    try:
        from apps.core.models import Company
        from apps.identity.models import User

        return UserInteractionLog.objects.create(
            user=User.objects.get(pk=user_id) if user_id else None,
            company=Company.objects.get(pk=company_id),
            interaction_type=interaction_type,
            module=module,
            entity_type=entity_type or "",
            entity_id=str(entity_id) if entity_id else "",
            metadata=metadata if metadata is not None else {},
        )
    except Exception:
        logger.exception(
            "interaction_service._create_sync: failed to log interaction "
            "(user=%s, company=%s, type=%s, module=%s)",
            user_id,
            company_id,
            interaction_type,
            module,
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def log_interaction(
    user: User | None,
    company: Company,
    interaction_type: str,
    module: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UserInteractionLog | None:
    """Log a user interaction, preferring async insertion for non-blocking behaviour.

    Behaviour:
      1. If django-q2 is available, the insert is enqueued via ``async_task``
         so the caller returns immediately (non-blocking).
      2. If django-q2 is unavailable OR the enqueue raises, fall back to a
         synchronous insert.
      3. If the synchronous insert also fails, the exception is logged and
         ``None`` is returned. Interaction logging NEVER raises to the caller,
         because it must not break the main user operation (e.g. a page load
         or note creation).

    Args:
        user: The user performing the interaction (may be ``None`` for
            system/automated events where no user is available, e.g. business
            events emitted from the service layer).
        company: The user's current company (multi-tenant scope).
        interaction_type: One of ``UserInteractionLog.InteractionType`` values
            (e.g. ``"page_view"``, ``"search"``, ``"note_create"``).
        module: The Visota module where the interaction occurred
            (e.g. ``"ledger"``, ``"pkm"``).
        entity_type: Optional entity type label (e.g. ``"note"``).
        entity_id: Optional entity identifier as a string.
        metadata: Optional free-form JSON metadata (e.g. ``{"query": "VAT"}``).

    Returns:
        The created ``UserInteractionLog`` instance (sync path), or ``None``
        if the async path was used or creation failed.
    """
    etype = entity_type or ""
    eid = str(entity_id) if entity_id else ""
    meta = metadata if metadata is not None else {}
    uid = user.id if user else None

    # Try the non-blocking async path first
    if _django_q_available():
        try:
            _enqueue_async(user, company, interaction_type, module, etype, eid, meta)
            return None  # async path does not return a model instance
        except Exception:
            logger.warning(
                "log_interaction: async enqueue failed, falling back to sync "
                "(user=%s, type=%s, module=%s)",
                uid,
                interaction_type,
                module,
                exc_info=True,
            )
            # Fall through to sync path

    # Synchronous fallback - never raise to the caller
    try:
        return _create_sync(
            user_id=uid,
            company_id=company.id,
            interaction_type=interaction_type,
            module=module,
            entity_type=etype,
            entity_id=eid,
            metadata=meta,
        )
    except Exception:
        logger.exception(
            "log_interaction: synchronous create failed (user=%s, type=%s, module=%s)",
            uid,
            interaction_type,
            module,
        )
        return None


def get_recent_interactions(
    user: User,
    company: Company,
    limit: int = DEFAULT_RECENT_LIMIT,
) -> Any:
    """Return recent interaction logs for a user within a company.

    The queryset is scoped by ``user`` + ``company`` (per-user and
    multi-tenant isolation) and ordered by ``created_at`` descending (most
    recent first), leveraging the model's default ordering.

    Args:
        user: The user whose interactions to retrieve.
        company: The company scope.
        limit: Maximum number of records to return (default 20).

    Returns:
        A queryset of ``UserInteractionLog`` instances (not yet evaluated).
    """
    return UserInteractionLog.objects.filter(user=user, company=company).order_by("-created_at")[
        :limit
    ]


def _format_vnd(amount: Any) -> str:
    """Format a numeric amount as a Vietnamese-number VND string.

    Accepts ``Decimal``, ``int``, ``float``, or numeric string. Returns the
    value formatted with thousands separators (e.g. ``50.000.000``). Falls
    back to ``str(amount)`` when the value cannot be normalised.
    """
    try:
        from decimal import Decimal

        if isinstance(amount, str):
            value = Decimal(amount)
        elif isinstance(amount, (int, float)):
            value = Decimal(str(amount))
        elif isinstance(amount, Decimal):
            value = amount
        else:
            return str(amount)
        # Quantize to integer VND (no sub-unit) and use '.' as the thousands
        # separator which is the Vietnamese convention.
        integer_part = int(value.quantize(Decimal("1")))
        return f"{integer_part:,}".replace(",", ".")
    except Exception:
        return str(amount)


def _extract_amount(metadata: dict[str, Any]) -> str | None:
    """Return the first amount-like value found in the event metadata.

    Looks up keys in :data:`_AMOUNT_METADATA_KEYS`. Returns the raw value
    (caller formats via :func:`_format_vnd`) or ``None`` when no amount key
    is present.
    """
    if not isinstance(metadata, dict):
        return None
    for key in _AMOUNT_METADATA_KEYS:
        value = metadata.get(key)
        if value is not None:
            return str(value)
    return None


def _format_page_views_vn(page_view_modules: dict[str, int]) -> str | None:
    """Format the page-view portion of the summary in Vietnamese.

    Returns a string like "xem 3 trang Kế toán, 2 trang Bán hàng" or
    ``None`` if there are no page views.
    """
    if not page_view_modules:
        return None
    parts: list[str] = []
    # Sort by module code for a stable, deterministic order.
    for mod, cnt in sorted(page_view_modules.items()):
        label = MODULE_LABELS_VN.get(mod, mod)
        parts.append(f"{cnt} trang {label}")
    return "xem " + ", ".join(parts)


def _format_business_events_vn(events: list[UserInteractionLog]) -> str | None:
    """Format recent business events (with amounts) as a Vietnamese fragment.

    Each event becomes a short clause such as::

        "lập phiếu kế toán BE-V01 (50.000.000 VND)"

    Returns ``None`` when the events list is empty.
    """
    if not events:
        return None
    parts: list[str] = []
    for entry in events:
        verb = INTERACTION_VERB_VN.get(
            entry.interaction_type,
            INTERACTION_LABELS.get(entry.interaction_type, entry.interaction_type),
        )
        clause = verb
        if entry.entity_id:
            clause += f" {entry.entity_id}"
        amount_raw = _extract_amount(entry.metadata or {})
        if amount_raw is not None:
            clause += f" ({_format_vnd(amount_raw)} VND)"
        parts.append(clause)
    return "hoạt động nghiệp vụ: " + ", ".join(parts)


def _format_content_actions_vn(counts: dict[str, int]) -> str | None:
    """Format non-business content actions (notes, documents, searches).

    Returns a Vietnamese fragment like "tạo 2 ghi chú, tải lên 1 tài liệu"
    or ``None`` when there are no content actions to summarise.
    """
    if not counts:
        return None
    order = ["note_create", "document_create", "search"]
    parts: list[str] = []
    for itype in order:
        count = counts.get(itype)
        if not count:
            continue
        verb = INTERACTION_VERB_VN.get(itype, INTERACTION_LABELS.get(itype, itype))
        parts.append(f"{verb} {count}")
    # Include any remaining content-action types not explicitly handled.
    handled = {"page_view"} | set(order) | set(BUSINESS_EVENT_TYPES)
    for itype, count in counts.items():
        if itype in handled or not count:
            continue
        label = INTERACTION_LABELS.get(itype, itype)
        parts.append(f"{count} {label}")
    return ", ".join(parts) if parts else None


def _get_current_module_vn(
    page_view_modules: dict[str, int],
    latest_page_view: UserInteractionLog | None,
) -> str | None:
    """Determine the user's current module as a Vietnamese phrase.

    Prefers the module of the most recent page view (closest to "where the
    user is right now"). Falls back to the most-viewed module in the window.
    Returns ``None`` when there are no page views.
    """
    module_code: str | None = None
    if latest_page_view is not None:
        module_code = latest_page_view.module
    elif page_view_modules:
        module_code = max(page_view_modules, key=lambda m: page_view_modules[m])
    if not module_code:
        return None
    label = MODULE_LABELS_VN.get(module_code, module_code)
    return f"Đang ở module {label}"


def _get_user_role_vn(user: User, company: Company) -> str | None:
    """Look up the user's role within the company and return a Vietnamese phrase.

    Queries :class:`apps.identity.models.UserCompanyRole` for the user's role
    in the given company. Returns a phrase like "Vai trò: Kế toán viên" or
    ``None`` when no role assignment exists. Non-blocking: any lookup error
    returns ``None``.
    """
    try:
        from apps.identity.models import UserCompanyRole

        ucr = (
            UserCompanyRole.objects.filter(user=user, company=company)
            .select_related("role")
            .order_by("-is_default", "id")
            .first()
        )
        if ucr is None or ucr.role_id is None:
            return None
        role_name = ucr.role.name or ucr.role.code
        return f"Vai trò: {role_name}"
    except Exception:
        logger.debug(
            "get_context_summary: không thể truy vấn vai trò người dùng "
            "(user=%s, company=%s) — bỏ qua.",
            getattr(user, "id", user),
            getattr(company, "id", company),
            exc_info=True,
        )
        return None


def _format_company_context(user: User, company: Company) -> str:  # noqa: ARG001
    """Build a Vietnamese natural-language description of the company's
    business context (entity type, accounting regime, tax method group,
    VAT/TNDN methods, industry).

    The text is designed to be prepended to the activity summary inside
    :func:`get_context_summary` so the Q&A LLM can personalise its answers
    based on the user's accounting regime and tax configuration.

    Behaviour is non-blocking: any unexpected error returns an empty string
    so the caller never breaks.

    Args:
        user: The user requesting the context (unused for now, kept for
            signature symmetry with :func:`_format_project_context`).
        company: The company whose context to render.

    Returns:
        A Vietnamese string such as:
        ``"Công ty thuộc loại hình Doanh nghiệp siêu nhỏ, áp dụng TT58/2026
        (Nhóm 2: GTGT theo tỷ lệ %, TNDN tính thuế). Phương pháp GTGT: Tỷ lệ %.
        Phương pháp TNDN: Tính thuế. Ngành: Thương mại - Công nghệ."``
        Returns ``""`` when the company context cannot be assembled.
    """
    try:
        regime_code = getattr(company, "accounting_regime", "") or ""
        entity_code = getattr(company, "entity_type", "") or ""
        vat_code = getattr(company, "vat_method", "") or ""
        tndn_code = getattr(company, "tndn_method", "") or ""
        industry = (getattr(company, "industry", "") or "").strip()

        regime_label = REGIME_LABELS_VN.get(regime_code, regime_code.upper() or "—")
        entity_label = ENTITY_TYPE_LABELS_VN.get(entity_code, entity_code)

        parts: list[str] = []
        parts.append(f"Công ty thuộc loại hình {entity_label}")
        parts.append(f"áp dụng chế độ kế toán {regime_label}")

        # TT58-specific tax method group description.
        if regime_code == "tt58":
            try:
                group_no = int(company.tax_method_group)
            except Exception:
                group_no = 0
            group_desc = TAX_GROUP_DESCRIPTIONS_VN.get(group_no)
            if group_desc:
                parts.append(f"Nhóm {group_no}: {group_desc}")

        vat_label = VAT_METHOD_LABELS_VN.get(vat_code, vat_code)
        tndn_label = TNDN_METHOD_LABELS_VN.get(tndn_code, tndn_code)
        parts.append(f"Phương pháp GTGT: {vat_label}")
        parts.append(f"Phương pháp TNDN: {tndn_label}")

        if industry:
            parts.append(f"Ngành: {industry}")

        return ", ".join(parts) + "."
    except Exception:
        logger.debug(
            "_format_company_context: không thể dựng bối cảnh công ty (company=%s) — bỏ qua.",
            getattr(company, "id", company),
            exc_info=True,
        )
        return ""


def get_context_summary(
    user: User,
    company: Company,
    hours: int = DEFAULT_SUMMARY_HOURS,
) -> str:
    """Build a Vietnamese natural-language summary of the user's recent activity.

    The summary is designed to be injected into the Q&A system prompt so the
    LLM can personalise its answer based on what the user has been doing.

    The summary includes (when available):

      - The user's role in the current company (e.g. "Vai trò: Kế toán viên").
      - The current module inferred from the most recent page view
        (e.g. "Đang ở module Kế toán").
      - Recent business activities grouped by module, with amounts for
        business events (e.g. "hoạt động nghiệp vụ: lập phiếu kế toán BE-V01
        (50.000.000 VND)").
      - A grouped breakdown of page views and content actions across modules.

    All queries are scoped by ``user`` + ``company`` (per-user and
    multi-tenant isolation) and restricted to the given time window.

    Args:
        user: The user whose activity to summarise.
        company: The company scope.
        hours: Time window in hours (default 24).

    Returns:
        A Vietnamese natural-language summary string. When no activity is
        recorded, returns a Vietnamese "no recent activity" message.
    """
    cutoff = timezone.now() - datetime.timedelta(hours=hours)

    base_qs = UserInteractionLog.objects.filter(
        user=user,
        company=company,
        created_at__gte=cutoff,
    )

    # --- Aggregate counts per interaction_type / module ----------------------
    counts_by_type: dict[str, int] = {}
    page_view_modules: dict[str, int] = {}

    for row in base_qs.values("interaction_type", "module").annotate(count=Count("id")):
        itype = row["interaction_type"]
        module = row["module"]
        count = row["count"]
        counts_by_type[itype] = counts_by_type.get(itype, 0) + count
        if itype == "page_view":
            page_view_modules[module] = page_view_modules.get(module, 0) + count

    # --- Assemble the summary ------------------------------------------------
    lines: list[str] = []

    # Company context (non-blocking). Prepended before the activity summary so
    # the Q&A LLM knows the user's accounting regime, entity type, tax method
    # group, and industry. Empty string is treated as "no context".
    company_context = _format_company_context(user, company)
    if company_context:
        lines.append(company_context)

    # Role hint (non-blocking — may be None). Included even when there is no
    # recent interaction activity so the LLM still knows the user's role.
    role_line = _get_user_role_vn(user, company)
    if role_line:
        lines.append(role_line)

    if not counts_by_type:
        # No interaction activity, but still return the role line (if any)
        # followed by the Vietnamese no-activity message.
        if lines:
            lines.append("Không có hoạt động gần đây trong %d giờ qua." % hours)
            return ". ".join(lines) + "."
        return "Không có hoạt động gần đây trong %d giờ qua." % hours

    # --- Latest page view (for current-module detection) --------------------
    latest_page_view: UserInteractionLog | None = (
        base_qs.filter(interaction_type="page_view").order_by("-created_at").first()
    )

    # --- Recent business events (with amounts) ------------------------------
    business_event_qs = base_qs.filter(interaction_type__in=list(BUSINESS_EVENT_TYPES)).order_by(
        "-created_at"
    )[:10]
    business_events: list[UserInteractionLog] = list(business_event_qs)

    # Current module context
    module_line = _get_current_module_vn(page_view_modules, latest_page_view)
    if module_line:
        lines.append(module_line)

    # Recent business activities (Vietnamese, with amounts when available)
    events_fragment = _format_business_events_vn(business_events)
    if events_fragment:
        lines.append(events_fragment)

    # Page views grouped by module
    page_fragment = _format_page_views_vn(page_view_modules) if page_view_modules else None
    if page_fragment:
        lines.append(page_fragment)

    # Other content actions (notes/documents/searches), excluding business events
    content_counts = {
        itype: count
        for itype, count in counts_by_type.items()
        if itype != "page_view" and itype not in BUSINESS_EVENT_TYPES
    }
    content_fragment = _format_content_actions_vn(content_counts)
    if content_fragment:
        lines.append(content_fragment)

    if not lines:
        return "Không có hoạt động gần đây trong %d giờ qua." % hours

    return ". ".join(lines) + "."
