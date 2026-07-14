"""django-ninja API router for TT58 DNSN voucher CRUD.

Provides REST endpoints under /api/dnsn/vouchers/ for:
- GET    /          — list with filtering by type and date range (paginated)
- POST   /          — create
- GET    /{id}      — retrieve
- PATCH  /{id}      — update (DRAFT only)
- DELETE /{id}      — delete (DRAFT only, prevents deletion of POSTED)
"""

from datetime import date
from decimal import Decimal

from ninja import NinjaAPI, Schema
from ninja.pagination import PageNumberPagination, paginate

from apps.core.models import Company
from apps.ledger.models import DnsnVoucher


def _get_company(request) -> Company:
    company = getattr(request, "current_company", None)
    if company:
        return company
    return Company.objects.first()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DnsnVoucherCreateSchema(Schema):
    voucher_no: str
    voucher_type: str
    voucher_date: date
    description: str = ""
    partner_name: str = ""
    partner_tax_code: str = ""
    partner_address: str = ""
    invoice_no: str = ""
    invoice_date: date | None = None
    invoice_form: str = ""
    invoice_serial: str = ""
    total_amount: Decimal = Decimal("0")


class DnsnVoucherSchema(Schema):
    id: int
    voucher_no: str
    voucher_type: str
    voucher_date: date
    posting_date: date | None = None
    description: str
    partner_name: str = ""
    partner_tax_code: str = ""
    partner_address: str = ""
    invoice_no: str = ""
    invoice_date: date | None = None
    invoice_form: str = ""
    invoice_serial: str = ""
    status: str
    fiscal_year: int
    period: int
    total_amount: Decimal


class DnsnVoucherDetailSchema(DnsnVoucherSchema):
    pass


class DnsnVoucherUpdateSchema(Schema):
    voucher_no: str | None = None
    voucher_type: str | None = None
    voucher_date: date | None = None
    description: str | None = None
    partner_name: str | None = None
    partner_tax_code: str | None = None
    partner_address: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    invoice_form: str | None = None
    invoice_serial: str | None = None
    total_amount: Decimal | None = None


class MessageSchema(Schema):
    message: str
    id: int | None = None


class DnsnLedgerInfoSchema(Schema):
    ledger_type: str
    label: str


class DnsnLedgerEntrySchema(Schema):
    id: int
    entry_date: date
    ledger_type: str
    description: str
    partner_name: str = ""
    revenue_amount: Decimal = Decimal("0")
    cost_amount: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    tndn_amount: Decimal = Decimal("0")
    cash_in: Decimal = Decimal("0")
    cash_out: Decimal = Decimal("0")
    bank_in: Decimal = Decimal("0")
    bank_out: Decimal = Decimal("0")
    vat_input: Decimal = Decimal("0")
    vat_output: Decimal = Decimal("0")
    vat_payable: Decimal = Decimal("0")
    item_code: str = ""
    item_name: str = ""
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    running_balance: Decimal = Decimal("0")
    voucher_id: int | None = None
    fiscal_year: int
    period: int


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def register_dnsn_endpoints(api: NinjaAPI) -> None:
    """Register DNSN voucher CRUD endpoints on an existing NinjaAPI instance."""

    @api.get(
        "/dnsn/vouchers/",
        response=list[DnsnVoucherSchema],
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    @paginate(PageNumberPagination)
    def list_dnsn_vouchers(
        request,
        voucher_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
    ):
        """List DNSN vouchers for the current company with optional filtering."""
        company = _get_company(request)
        qs = DnsnVoucher.objects.filter(company=company).order_by("-voucher_date", "-id")
        if voucher_type:
            qs = qs.filter(voucher_type=voucher_type)
        if date_from:
            qs = qs.filter(voucher_date__gte=date_from)
        if date_to:
            qs = qs.filter(voucher_date__lte=date_to)
        if status:
            qs = qs.filter(status=status)
        return list(qs)

    @api.post(
        "/dnsn/vouchers/",
        response={201: DnsnVoucherSchema},
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    def create_dnsn_voucher(request, payload: DnsnVoucherCreateSchema):
        """Create a new DNSN voucher."""
        company = _get_company(request)
        voucher = DnsnVoucher.objects.create(
            company=company,
            fiscal_year=payload.voucher_date.year,
            period=payload.voucher_date.month,
            voucher_no=payload.voucher_no,
            voucher_type=payload.voucher_type,
            voucher_date=payload.voucher_date,
            description=payload.description,
            partner_name=payload.partner_name,
            partner_tax_code=payload.partner_tax_code,
            partner_address=payload.partner_address,
            invoice_no=payload.invoice_no,
            invoice_date=payload.invoice_date,
            invoice_form=payload.invoice_form,
            invoice_serial=payload.invoice_serial,
            total_amount=payload.total_amount,
            status=DnsnVoucher.Status.DRAFT,
        )
        return 201, voucher

    @api.get(
        "/dnsn/vouchers/{voucher_id}",
        response=DnsnVoucherDetailSchema,
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    def get_dnsn_voucher(request, voucher_id: int):
        """Retrieve a single DNSN voucher."""
        company = _get_company(request)
        return DnsnVoucher.objects.get(id=voucher_id, company=company)

    @api.patch(
        "/dnsn/vouchers/{voucher_id}",
        response=DnsnVoucherSchema,
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    def update_dnsn_voucher(request, voucher_id: int, payload: DnsnVoucherUpdateSchema):
        """Update a DRAFT DNSN voucher."""
        company = _get_company(request)
        voucher = DnsnVoucher.objects.get(id=voucher_id, company=company)

        if voucher.is_posted:
            from ninja.errors import HttpError

            raise HttpError(400, "Cannot edit a posted voucher.")

        # Only update fields that were explicitly provided (not None)
        data = payload.dict(exclude_none=True)
        allowed_fields = {
            "voucher_no",
            "voucher_type",
            "voucher_date",
            "description",
            "partner_name",
            "partner_tax_code",
            "partner_address",
            "invoice_no",
            "invoice_date",
            "invoice_form",
            "invoice_serial",
            "total_amount",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(voucher, key, value)

        # Recompute fiscal_year/period if date changed
        if "voucher_date" in data and voucher.voucher_date:
            voucher.fiscal_year = voucher.voucher_date.year
            voucher.period = voucher.voucher_date.month

        voucher.save()
        voucher.refresh_from_db()
        return voucher

    @api.delete(
        "/dnsn/vouchers/{voucher_id}",
        response=MessageSchema,
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    def delete_dnsn_voucher(request, voucher_id: int):
        """Delete a DRAFT DNSN voucher. POSTED vouchers cannot be deleted."""
        company = _get_company(request)
        voucher = DnsnVoucher.objects.get(id=voucher_id, company=company)

        if voucher.is_posted:
            from ninja.errors import HttpError

            raise HttpError(400, "Cannot delete a posted voucher.")

        voucher_no = voucher.voucher_no
        voucher.delete()
        return MessageSchema(message=f"Deleted voucher {voucher_no}", id=None)

    register_dnsn_ledger_endpoints(api)


def register_dnsn_ledger_endpoints(api: NinjaAPI) -> None:
    """Register DNSN ledger listing/entry endpoints on the NinjaAPI."""

    @api.get(
        "/dnsn/ledgers/",
        response=list[DnsnLedgerInfoSchema],
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    def list_dnsn_ledgers(request):
        """List all available DNSN ledger types for the current company."""
        from apps.ledger.dnsn_ledger_types import LEDGER_LABELS, get_company_available_ledgers

        company = _get_company(request)
        available = get_company_available_ledgers(company)
        return [{"ledger_type": lt, "label": LEDGER_LABELS.get(lt, lt.upper())} for lt in available]

    @api.get(
        "/dnsn/ledgers/{ledger_type}/entries/",
        response=list[DnsnLedgerEntrySchema],
        tags=["DNSN"],
        auth=lambda request: request.user.is_authenticated,
    )
    @paginate(PageNumberPagination)
    def list_dnsn_ledger_entries(
        request,
        ledger_type: str,
        fiscal_year: int | None = None,
        period: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        """List DNSN ledger entries for a specific ledger type with running balances.

        The ledger_type must be available for the company's tax_method_group
        or explicitly enabled as an optional ledger.
        """
        from apps.ledger.dnsn_ledger_types import get_company_available_ledgers
        from apps.ledger.models import DnsnLedgerEntry

        company = _get_company(request)
        available = get_company_available_ledgers(company)

        if ledger_type not in available:
            from ninja.errors import HttpError

            raise HttpError(
                403,
                f"Ledger {ledger_type} is not available for this company.",
            )

        qs = DnsnLedgerEntry.objects.filter(
            company=company,
            ledger_type=ledger_type,
        ).order_by("entry_date", "id", "line_no")

        if fiscal_year:
            qs = qs.filter(fiscal_year=fiscal_year)
        if period:
            qs = qs.filter(period=period)
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)

        return list(qs)
