"""django-ninja API — REST API for Visota ERP.

Provides /api/v1/ endpoints for vouchers, sales, purchasing, customers,
vendors, reports, and e-invoice operations.

Authentication: Session-based (cookie) for browser, API Key header for
service-to-service. JWT support planned for Phase 2.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from ninja import NinjaAPI, Schema
from ninja.pagination import paginate

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.master_data.models import Customer, Product, Vendor
from apps.sales.models import SalesInvoice

# ---------------------------------------------------------------------------
# API instance
# ---------------------------------------------------------------------------

api = NinjaAPI(
    title="Visota ERP API",
    version="1.0.0",
    description="REST API for Vietnamese accounting — TT133/2016 compliant",
    urls_namespace="api_v1",
)


# ---------------------------------------------------------------------------
# Auth — session-based (browser cookie) + API key
# ---------------------------------------------------------------------------


def get_current_user(request):
    """Resolve user from session (browser) or X-API-Key header."""
    if request.user.is_authenticated:
        return request.user
    api_key = request.headers.get("X-API-Key", "")
    if api_key.startswith("pmk_"):
        user = User.objects.filter(api_key=api_key[4:]).first()
        if user:
            return user
    from ninja.errors import HttpError

    raise HttpError(401, "Authentication required")


def get_current_company(request) -> Company:
    """Get the current company from request (tenant middleware)."""
    company = getattr(request, "current_company", None)
    if company:
        return company
    return Company.objects.first()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class VoucherLineSchema(Schema):
    line_no: int
    account_code: str
    description: str = ""
    debit_vnd: Decimal = Decimal("0")
    credit_vnd: Decimal = Decimal("0")
    object_code: str = ""
    object_name: str = ""


class VoucherSchema(Schema):
    id: int
    voucher_no: str
    voucher_type: str
    voucher_date: date
    status: int
    total_vnd: Decimal
    description: str
    fiscal_year: int
    period: int


class VoucherDetailSchema(VoucherSchema):
    currency_code: str = "VND"
    lines: list[VoucherLineSchema] = []


class CustomerSchema(Schema):
    id: int
    code: str
    name: str
    tax_code: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""


class VendorSchema(Schema):
    id: int
    code: str
    name: str
    tax_code: str = ""
    address: str = ""
    phone: str = ""


class ProductSchema(Schema):
    id: int
    code: str
    name: str
    product_type: str
    default_unit_price: Decimal = Decimal("0")
    unit_id: str = ""
    default_vat_rate: Decimal = Decimal("0")


class SalesInvoiceSchema(Schema):
    id: int
    invoice_no: str
    invoice_date: date
    customer_id: int | None = None
    customer_name: str = ""
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    payment_status: int
    status: int = 2


class SalesInvoiceDetailSchema(SalesInvoiceSchema):
    currency_code: str = "VND"
    exchange_rate: Decimal = Decimal("1")
    lines: list[dict] = []


class TrialBalanceItemSchema(Schema):
    account_code: str
    account_name: str = ""
    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    period_debit: Decimal = Decimal("0")
    period_credit: Decimal = Decimal("0")
    closing_debit: Decimal = Decimal("0")
    closing_credit: Decimal = Decimal("0")


class MessageSchema(Schema):
    message: str
    id: int | None = None


# ---------------------------------------------------------------------------
# Voucher endpoints
# ---------------------------------------------------------------------------


@api.get("/vouchers/", response=list[VoucherSchema], tags=["Accounting"], auth=get_current_user)
@paginate
def list_vouchers(request, fiscal_year: int | None = None, period: int | None = None):
    """List accounting vouchers for current company."""
    company = get_current_company(request)
    qs = AccountingVoucher.objects.filter(company=company).order_by("-voucher_date", "-id")
    if fiscal_year:
        qs = qs.filter(fiscal_year=fiscal_year)
    if period:
        qs = qs.filter(period=period)
    return qs


@api.get(
    "/vouchers/{voucher_id}",
    response=VoucherDetailSchema,
    tags=["Accounting"],
    auth=get_current_user,
)
def get_voucher(request, voucher_id: int):
    company = get_current_company(request)
    voucher = AccountingVoucher.objects.get(id=voucher_id, company=company)
    lines = VoucherLine.objects.filter(voucher=voucher).order_by("line_no")
    return VoucherDetailSchema(
        id=voucher.id,
        voucher_no=voucher.voucher_no,
        voucher_type=voucher.voucher_type,
        voucher_date=voucher.voucher_date,
        status=voucher.status,
        total_vnd=voucher.total_vnd,
        description=voucher.description,
        fiscal_year=voucher.fiscal_year,
        period=voucher.period,
        currency_code=voucher.currency_code,
        lines=[
            VoucherLineSchema(
                line_no=vl.line_no,
                account_code=vl.account_code,
                description=vl.description or "",
                debit_vnd=vl.debit_vnd or Decimal("0"),
                credit_vnd=vl.credit_vnd or Decimal("0"),
                object_code=vl.object_code or "",
                object_name=vl.object_name or "",
            )
            for vl in lines
        ],
    )


@api.post(
    "/vouchers/{voucher_id}/post",
    response=MessageSchema,
    tags=["Accounting"],
    auth=get_current_user,
)
def post_voucher(request, voucher_id: int):
    """Post voucher to ledger (status -> LEDGER)."""
    from apps.ledger.services.voucher_posting_service import VoucherPostingService

    company = get_current_company(request)
    voucher = AccountingVoucher.objects.get(id=voucher_id, company=company)
    VoucherPostingService().post(voucher)
    return MessageSchema(message=f"Voucher {voucher.voucher_no} posted", id=voucher.id)


# ---------------------------------------------------------------------------
# Master data endpoints
# ---------------------------------------------------------------------------


@api.get("/customers/", response=list[CustomerSchema], tags=["Master Data"], auth=get_current_user)
@paginate
def list_customers(request, search: str | None = None):
    company = get_current_company(request)
    qs = Customer.objects.filter(company=company).order_by("code")
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
    return qs


@api.get("/vendors/", response=list[VendorSchema], tags=["Master Data"], auth=get_current_user)
@paginate
def list_vendors(request, search: str | None = None):
    company = get_current_company(request)
    qs = Vendor.objects.filter(company=company).order_by("code")
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
    return qs


@api.get("/products/", response=list[ProductSchema], tags=["Master Data"], auth=get_current_user)
@paginate
def list_products(request, search: str | None = None):
    company = get_current_company(request)
    qs = Product.objects.filter(company=company).order_by("code")
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
    return qs


# ---------------------------------------------------------------------------
# Sales endpoints
# ---------------------------------------------------------------------------


class SalesInvoiceLineInputSchema(Schema):
    product_id: int
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0")


class SalesInvoiceCreateSchema(Schema):
    invoice_no: str
    invoice_date: date
    customer_id: int
    description: str = ""
    currency_code: str = "VND"
    exchange_rate: Decimal = Decimal("1")
    auto_post: bool = True
    lines: list[SalesInvoiceLineInputSchema]


@api.get(
    "/sales/invoices/", response=list[SalesInvoiceSchema], tags=["Sales"], auth=get_current_user
)
@paginate
def list_sales_invoices(request, fiscal_year: int | None = None):
    company = get_current_company(request)
    qs = SalesInvoice.objects.filter(company=company).order_by("-invoice_date", "-id")
    return list(qs)


@api.post(
    "/sales/invoices/",
    response=MessageSchema,
    tags=["Sales"],
    auth=get_current_user,
)
def create_sales_invoice(request, payload: SalesInvoiceCreateSchema):
    """Create a sales invoice via API (automation-friendly, no Alpine.js needed)."""
    from apps.sales.services import SalesInvoiceService

    company = get_current_company(request)
    service = SalesInvoiceService(company=company)
    invoice = service.create(
        {
            "invoice_no": payload.invoice_no,
            "invoice_date": payload.invoice_date,
            "customer_id": payload.customer_id,
            "description": payload.description,
            "currency_code": payload.currency_code,
            "exchange_rate": payload.exchange_rate,
            "auto_post": payload.auto_post,
            "lines": [
                {
                    "product_id": ln.product_id,
                    "quantity": ln.quantity,
                    "unit_price": ln.unit_price,
                    "vat_rate": ln.vat_rate,
                }
                for ln in payload.lines
            ],
        }
    )
    return MessageSchema(message=f"Sales invoice {invoice.invoice_no} created", id=invoice.id)


@api.get(
    "/sales/invoices/{invoice_id}",
    response=SalesInvoiceDetailSchema,
    tags=["Sales"],
    auth=get_current_user,
)
def get_sales_invoice(request, invoice_id: int):
    company = get_current_company(request)
    inv = SalesInvoice.objects.get(id=invoice_id, company=company)
    lines = [
        {
            "line_no": ln.line_no,
            "product_code": ln.product.code if ln.product else "",
            "description": ln.description,
            "quantity": str(ln.quantity),
            "unit_price": str(ln.unit_price),
            "vat_rate": str(ln.vat_rate),
            "amount": str(ln.amount),
        }
        for ln in inv.lines.all()
    ]
    return SalesInvoiceDetailSchema(
        id=inv.id,
        invoice_no=inv.invoice_no,
        invoice_date=inv.invoice_date,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name if inv.customer else "",
        subtotal=inv.subtotal,
        vat_amount=inv.vat_amount,
        total_amount=inv.total_amount,
        payment_status=inv.payment_status,
        status=inv.status,
        currency_code=inv.currency_code,
        exchange_rate=inv.exchange_rate,
        lines=lines,
    )


# ---------------------------------------------------------------------------
# Purchase endpoints
# ---------------------------------------------------------------------------


class PurchaseInvoiceLineInputSchema(Schema):
    product_id: int
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0.1")
    debit_account: str = ""


class PurchaseInvoiceCreateSchema(Schema):
    invoice_no: str
    invoice_date: date
    vendor_id: int
    description: str = ""
    currency_code: str = "VND"
    exchange_rate: Decimal = Decimal("1")
    auto_post: bool = True
    credit_account: str = ""
    lines: list[PurchaseInvoiceLineInputSchema]


@api.post(
    "/purchasing/invoices/",
    response=MessageSchema,
    tags=["Purchasing"],
    auth=get_current_user,
)
def create_purchase_invoice(request, payload: PurchaseInvoiceCreateSchema):
    """Create a purchase invoice via API (automation-friendly)."""
    from apps.purchasing.services import PurchaseInvoiceService

    company = get_current_company(request)
    service = PurchaseInvoiceService(company=company)
    invoice = service.create(
        {
            "invoice_no": payload.invoice_no,
            "invoice_date": payload.invoice_date,
            "vendor_id": payload.vendor_id,
            "description": payload.description,
            "currency_code": payload.currency_code,
            "exchange_rate": payload.exchange_rate,
            "auto_post": payload.auto_post,
            "credit_account": payload.credit_account,
            "lines": [
                {
                    "product_id": ln.product_id,
                    "quantity": ln.quantity,
                    "unit_price": ln.unit_price,
                    "vat_rate": ln.vat_rate,
                    "debit_account": ln.debit_account,
                }
                for ln in payload.lines
            ],
        }
    )
    return MessageSchema(
        message=f"Purchase invoice {invoice.invoice_no} created", id=invoice.id
    )


# ---------------------------------------------------------------------------
# Report endpoints
# ---------------------------------------------------------------------------


@api.get(
    "/reports/trial-balance",
    response=list[TrialBalanceItemSchema],
    tags=["Reports"],
    auth=get_current_user,
)
def trial_balance(request, fiscal_year: int, period: int):
    """Trial balance (Cân đối số phát sinh) for a given period."""
    company = get_current_company(request)
    qs = AccountPeriodBalance.objects.filter(
        company=company, fiscal_year=fiscal_year, period=period
    ).order_by("account_code")
    return [
        TrialBalanceItemSchema(
            account_code=b.account_code,
            opening_debit=b.opening_debit or Decimal("0"),
            opening_credit=b.opening_credit or Decimal("0"),
            period_debit=b.period_debit or Decimal("0"),
            period_credit=b.period_credit or Decimal("0"),
            closing_debit=b.closing_debit or Decimal("0"),
            closing_credit=b.closing_credit or Decimal("0"),
        )
        for b in qs
    ]


@api.get("/reports/ar-aging", tags=["Reports"], auth=get_current_user)
def ar_aging(request):
    """Accounts receivable aging summary."""
    company = get_current_company(request)
    today = date.today()
    result = {"current": 0, "d1_30": 0, "d31_60": 0, "d60_plus": 0, "total": 0}
    unpaid = SalesInvoice.objects.filter(company=company, status__gte=2).exclude(payment_status=2)
    for inv in unpaid:
        amount = (inv.total_amount or 0) - (inv.paid_amount or 0)
        if amount <= 0:
            continue
        result["total"] += int(amount)
        if inv.invoice_date:
            days = (today - inv.invoice_date).days
            if days <= 30:
                result["current"] += int(amount)
            elif days <= 60:
                result["d1_30"] += int(amount)
            elif days <= 90:
                result["d31_60"] += int(amount)
            else:
                result["d60_plus"] += int(amount)
    return result


@api.get("/reports/cash-position", tags=["Reports"], auth=get_current_user)
def cash_position(request, fiscal_year: int, period: int):
    """Cash position: cash on hand (TK 111) + bank (TK 112)."""
    company = get_current_company(request)
    qs = AccountPeriodBalance.objects.filter(
        company=company, fiscal_year=fiscal_year, period=period
    )
    cash = qs.filter(account_code__startswith="111").aggregate(d=Sum("closing_debit"))[
        "d"
    ] or Decimal("0")
    bank = qs.filter(account_code__startswith="112").aggregate(d=Sum("closing_debit"))[
        "d"
    ] or Decimal("0")
    return {
        "cash": int(cash),
        "bank": int(bank),
        "total": int(cash + bank),
        "period": period,
        "fiscal_year": fiscal_year,
    }


# ---------------------------------------------------------------------------
# E-Invoice endpoints
# ---------------------------------------------------------------------------


@api.post("/einvoice/issue/{sales_invoice_id}", tags=["E-Invoice"], auth=get_current_user)
def issue_einvoice(request, sales_invoice_id: int):
    """Issue e-invoice from a sales invoice."""
    from apps.einvoice.services import EInvoiceService

    company = get_current_company(request)
    si = SalesInvoice.objects.get(id=sales_invoice_id, company=company)
    ei = EInvoiceService.issue_from_sales_invoice(si, issued_by=request.user)
    return {
        "id": ei.id,
        "invoice_no": ei.invoice_no,
        "status": ei.status,
        "transaction_id": str(ei.transaction_id),
    }


@api.post("/einvoice/{einvoice_id}/publish", tags=["E-Invoice"], auth=get_current_user)
def publish_einvoice(request, einvoice_id: int):
    """Publish e-invoice (assign number, send to provider)."""
    from apps.einvoice.models import EInvoice
    from apps.einvoice.services import EInvoiceService

    company = get_current_company(request)
    ei = EInvoice.objects.get(id=einvoice_id, company=company)
    EInvoiceService.publish(ei)
    return {"id": ei.id, "status": ei.status, "invoice_no": ei.invoice_no}


# ---------------------------------------------------------------------------
# DNSN (TT58) voucher endpoints
# ---------------------------------------------------------------------------

from apps.ledger.dnsn_api import register_dnsn_endpoints  # noqa: E402

register_dnsn_endpoints(api)


# ---------------------------------------------------------------------------
# PKM (Personal Knowledge Management) module
# ---------------------------------------------------------------------------

from apps.pkm.api import router as pkm_router  # noqa: E402

api.add_router("/pkm/", pkm_router)
