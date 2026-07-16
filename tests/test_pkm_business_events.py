"""Tests for PKM business event logging.

Verifies that business events are logged via ``log_interaction`` at key
service-layer points:

  - VoucherPostingService.post() → voucher_create / ledger  (VAL-CTX-002)
  - SalesInvoiceService._post()  → invoice_create / sales   (VAL-CTX-003)
  - DnsnPostingService.post()    → dnsn_voucher_create / ledger
  - PeriodClosingService.close_period() → period_close / ledger
  - EInvoiceService.issue()      → einvoice_issue / einvoice

All logging is non-blocking (try/except), so business operations must
succeed even if the PKM interaction logging fails.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.models import Company
from apps.einvoice.services import EInvoiceService
from apps.ledger.models import (
    AccountingVoucher,
    DnsnVoucher,
    VoucherLine,
)
from apps.ledger.services import (
    DnsnPostingService,
    PeriodClosingService,
    VoucherPostingService,
)
from apps.master_data.models import Customer, Product
from apps.pkm.models import UserInteractionLog
from apps.sales.models import SalesInvoice, SalesInvoiceLine
from apps.sales.services import SalesInvoiceService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _force_sync():
    """Patch django-q detection so log_interaction writes synchronously."""
    return patch(
        "apps.pkm.services.interaction_service._django_q_available",
        return_value=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="BEVT", name="Business Event Test Co")


@pytest.fixture
def tt58_company(db):
    return Company.objects.create(
        code="BEVT58",
        name="Business Event TT58 Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


def _make_voucher(company, **kwargs):
    """Create a balanced draft AccountingVoucher."""
    debit = kwargs.get("debit_lines", [("111", 1000)])
    credit = kwargs.get("credit_lines", [("5111", 1000)])
    count = AccountingVoucher.objects.count() + 1
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=kwargs.get("voucher_no", f"BE-{company.pk}-{count}"),
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        status=AccountingVoucher.Status.DRAFT,
    )
    line_no = 1
    for acc, amt in debit:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal(str(amt)),
            credit_vnd=Decimal("0"),
        )
        line_no += 1
    for acc, amt in credit:
        VoucherLine.objects.create(
            voucher=v,
            line_no=line_no,
            account_code=acc,
            debit_vnd=Decimal("0"),
            credit_vnd=Decimal(str(amt)),
        )
        line_no += 1
    return v


# ---------------------------------------------------------------------------
# VAL-CTX-002: VoucherPostingService.post() emits voucher_create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_voucher_post_emits_business_event(company):
    """VoucherPostingService.post() logs a voucher_create interaction."""
    v = _make_voucher(company, voucher_no="BE-V01")
    with _force_sync():
        VoucherPostingService().post(v)

    log = UserInteractionLog.objects.filter(
        company=company,
        interaction_type="voucher_create",
        module="ledger",
    )
    assert log.count() == 1
    entry = log.first()
    assert entry.entity_type == "voucher"
    assert entry.entity_id == "BE-V01"
    assert entry.metadata["amount"] == str(v.total_vnd)


@pytest.mark.django_db
def test_voucher_post_event_is_non_blocking(company):
    """Voucher posting succeeds even if log_interaction raises."""
    v = _make_voucher(company, voucher_no="BE-V02")
    with patch(
        "apps.pkm.services.interaction_service.log_interaction",
        side_effect=Exception("PKM down"),
    ):
        # Should NOT raise — logging is wrapped in try/except
        VoucherPostingService().post(v)

    v.refresh_from_db()
    assert v.status == AccountingVoucher.Status.LEDGER


# ---------------------------------------------------------------------------
# VAL-CTX-003: SalesInvoiceService._post() emits invoice_create
# ---------------------------------------------------------------------------


@pytest.fixture
def sales_setup(db, company):
    customer = Customer.objects.create(company=company, code="KH001", name="ABC Co")
    product = Product.objects.create(
        company=company,
        code="SP001",
        name="Widget",
        product_type="goods",
        unit_id="CAI",
        gl_account_inv="156",
        gl_account_cogs="632",
        gl_account_revenue="5111",
    )
    return company, customer, product


@pytest.mark.django_db
def test_sales_invoice_post_emits_business_event(sales_setup):
    """SalesInvoiceService._post() logs an invoice_create interaction."""
    company, customer, product = sales_setup
    service = SalesInvoiceService(company=company)

    with _force_sync():
        invoice = service.create(
            {
                "invoice_no": "SI-BE01",
                "invoice_date": date(2026, 6, 15),
                "customer_id": customer.id,
                "lines": [
                    {
                        "product_id": product.id,
                        "quantity": Decimal("10"),
                        "unit_price": Decimal("100000"),
                        "vat_rate": Decimal("0.10"),
                    },
                ],
                "post": True,
            }
        )

    log = UserInteractionLog.objects.filter(
        company=company,
        interaction_type="invoice_create",
        module="sales",
    )
    assert log.count() == 1
    entry = log.first()
    assert entry.entity_type == "sales_invoice"
    assert entry.entity_id == "SI-BE01"
    assert entry.metadata["total_amount"] == str(invoice.total_amount)


@pytest.mark.django_db
def test_sales_invoice_post_event_is_non_blocking(sales_setup):
    """Sales invoice posting succeeds even if log_interaction raises."""
    company, customer, product = sales_setup
    service = SalesInvoiceService(company=company)

    with patch(
        "apps.pkm.services.interaction_service.log_interaction",
        side_effect=Exception("PKM down"),
    ):
        # Should NOT raise
        invoice = service.create(
            {
                "invoice_no": "SI-BE02",
                "invoice_date": date(2026, 6, 15),
                "customer_id": customer.id,
                "lines": [
                    {
                        "product_id": product.id,
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("100"),
                        "vat_rate": Decimal("0.10"),
                    },
                ],
                "post": True,
            }
        )

    assert invoice.status == 2  # LEDGER


# ---------------------------------------------------------------------------
# DnsnPostingService.post() emits dnsn_voucher_create
# ---------------------------------------------------------------------------


def _make_dnsn_voucher(company, **kwargs):
    """Create a draft DnsnVoucher."""
    return DnsnVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=kwargs.get("voucher_no", f"DN-{company.pk}-{DnsnVoucher.objects.count() + 1}"),
        voucher_type=DnsnVoucher.VoucherType.PHIEU_THU,
        voucher_date=date(2026, 6, 15),
        status=DnsnVoucher.Status.DRAFT,
    )


@pytest.mark.django_db
def test_dnsn_post_emits_business_event(tt58_company):
    """DnsnPostingService.post() logs a dnsn_voucher_create interaction."""
    voucher = _make_dnsn_voucher(tt58_company, voucher_no="DN-BE01")
    entries = [{"ledger_type": "s1", "revenue_amount": Decimal("5000")}]

    with _force_sync():
        DnsnPostingService().post(voucher, entries=entries)

    log = UserInteractionLog.objects.filter(
        company=tt58_company,
        interaction_type="dnsn_voucher_create",
        module="ledger",
    )
    assert log.count() == 1
    entry = log.first()
    assert entry.entity_type == "dnsn_voucher"
    assert entry.entity_id == "DN-BE01"
    assert entry.metadata["total_amount"] == str(voucher.total_amount)


@pytest.mark.django_db
def test_dnsn_post_event_is_non_blocking(tt58_company):
    """DNSN posting succeeds even if log_interaction raises."""
    voucher = _make_dnsn_voucher(tt58_company, voucher_no="DN-BE02")
    entries = [{"ledger_type": "s1", "revenue_amount": Decimal("3000")}]

    with patch(
        "apps.pkm.services.interaction_service.log_interaction",
        side_effect=Exception("PKM down"),
    ):
        # Should NOT raise
        DnsnPostingService().post(voucher, entries=entries)

    voucher.refresh_from_db()
    assert voucher.status == DnsnVoucher.Status.POSTED


# ---------------------------------------------------------------------------
# PeriodClosingService.close_period() emits period_close
# ---------------------------------------------------------------------------


@pytest.fixture
def company_with_activity(db, company):
    """Company with posted revenue + expense so period close has work to do."""
    # Revenue: N111 / C5111 = 5000
    v1 = _make_voucher(
        company,
        voucher_no="PC01",
        debit_lines=[("111", 5000)],
        credit_lines=[("5111", 5000)],
    )
    VoucherPostingService().post(v1)
    # Expense: N642 / C111 = 2000
    v2 = _make_voucher(
        company,
        voucher_no="PC02",
        debit_lines=[("642", 2000)],
        credit_lines=[("111", 2000)],
    )
    VoucherPostingService().post(v2)
    return company


@pytest.mark.django_db
def test_period_close_emits_business_event(company_with_activity):
    """PeriodClosingService.close_period() logs a period_close interaction."""
    with _force_sync():
        svc = PeriodClosingService(company=company_with_activity)
        # Patch out the voucher_create events from the closing voucher's own
        # VoucherPostingService.post call so we can isolate the period_close log.
        result = svc.close_period(fiscal_year=2026, period=6)

    assert result["skipped"] is False

    log = UserInteractionLog.objects.filter(
        company=company_with_activity,
        interaction_type="period_close",
        module="ledger",
    )
    assert log.count() == 1
    entry = log.first()
    assert entry.entity_type == "period"
    assert entry.entity_id == "2026-06"
    assert entry.metadata["fiscal_year"] == 2026
    assert entry.metadata["period"] == 6


@pytest.mark.django_db
def test_period_close_event_is_non_blocking(company_with_activity):
    """Period close succeeds even if log_interaction raises."""
    # Use a different period so the close runs (period 6 already used above
    # in the fixture but is not idempotent-skipped since no closing voucher
    # exists yet). We patch log_interaction to raise.
    with patch(
        "apps.pkm.services.interaction_service.log_interaction",
        side_effect=Exception("PKM down"),
    ):
        svc = PeriodClosingService(company=company_with_activity)
        # Should NOT raise
        result = svc.close_period(fiscal_year=2026, period=6)

    assert result["skipped"] is False
    assert result["voucher_id"] is not None


# ---------------------------------------------------------------------------
# EInvoiceService.issue() emits einvoice_issue
# ---------------------------------------------------------------------------


@pytest.fixture
def einvoice_setup(db, company):
    customer = Customer.objects.create(
        company=company,
        code="CUST001",
        name="EInv Customer",
        tax_code="0109876543",
        address="456 Test Ave",
    )
    product = Product.objects.create(
        company=company,
        code="EPROD",
        name="EInv Product",
        product_type="goods",
        unit_id="cai",
        default_vat_rate=Decimal("10"),
    )
    si = SalesInvoice.objects.create(
        company=company,
        invoice_no="EI-BE01",
        invoice_date=date(2026, 6, 23),
        customer=customer,
        currency_code="VND",
        exchange_rate=Decimal("1"),
        subtotal=Decimal("1000000"),
        vat_amount=Decimal("100000"),
        total_amount=Decimal("1100000"),
        status=2,
    )
    SalesInvoiceLine.objects.create(
        invoice=si,
        line_no=1,
        product=product,
        description="Test line",
        quantity=Decimal("1"),
        unit_id="cai",
        unit_price=Decimal("1000000"),
        amount_before_vat=Decimal("1000000"),
        vat_rate=Decimal("10"),
        vat_amount=Decimal("100000"),
        amount=Decimal("1100000"),
        revenue_account="5111",
        vat_account="33311",
    )
    return company, si


@pytest.mark.django_db
def test_einvoice_issue_emits_business_event(einvoice_setup):
    """EInvoiceService.issue() logs an einvoice_issue interaction."""
    company, si = einvoice_setup

    with _force_sync():
        ei = EInvoiceService.issue(si)

    log = UserInteractionLog.objects.filter(
        company=company,
        interaction_type="einvoice_issue",
        module="einvoice",
    )
    assert log.count() == 1
    entry = log.first()
    assert entry.entity_type == "einvoice"
    assert entry.entity_id == str(ei.pk)
    assert entry.metadata["total_amount"] == str(ei.total_amount)


@pytest.mark.django_db
def test_einvoice_issue_event_is_non_blocking(einvoice_setup):
    """E-invoice issue succeeds even if log_interaction raises."""
    _, si = einvoice_setup

    with patch(
        "apps.pkm.services.interaction_service.log_interaction",
        side_effect=Exception("PKM down"),
    ):
        # Should NOT raise
        ei = EInvoiceService.issue(si)

    assert ei is not None
    assert ei.pk is not None
