"""Smoke tests for the UX-fix deliverables (export, delete, vnd filter, breadcrumb)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.core.models import Company
from apps.ledger.models import AccountingVoucher
from apps.master_data.models import Customer, Product, Vendor

User = get_user_model()


@pytest.fixture
def auth_user(db):
    u, _ = User.objects.get_or_create(
        username="uxfixer", defaults={"email": "ux@t.co"}
    )
    u.set_password("pw")
    u.save()
    return u


@pytest.fixture
def auth_client(auth_user):
    c = Client()
    c.force_login(auth_user)
    return c


@pytest.fixture
def company(db):
    co, _ = Company.objects.get_or_create(code="UXC", defaults={"name": "UX Co"})
    return co


# ---------- Excel export ----------


@pytest.mark.django_db
def test_customer_export_returns_xlsx(auth_client, company):
    Customer.objects.create(code="UX001", name="Cust One", company=company)
    r = auth_client.get("/modern/customers/export/")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert "customers.xlsx" in r.headers["content-disposition"]
    # XLSX magic bytes: PK\x03\x04 (zip)
    assert r.content[:4] == b"PK\x03\x04"


@pytest.mark.django_db
def test_vendor_export_returns_xlsx(auth_client, company):
    Vendor.objects.create(code="UXV01", name="Vendor One", company=company)
    r = auth_client.get("/modern/vendors/export/")
    assert r.status_code == 200
    assert "vendors.xlsx" in r.headers["content-disposition"]


@pytest.mark.django_db
def test_product_export_returns_xlsx(auth_client, company):
    Product.objects.create(code="UXP01", name="Prod One", company=company)
    r = auth_client.get("/modern/products/export/")
    assert r.status_code == 200
    assert "products.xlsx" in r.headers["content-disposition"]


@pytest.mark.django_db
def test_voucher_export_respects_search(auth_client, company, auth_user):
    AccountingVoucher.objects.create(
        company=company, voucher_no="BC-UX-A", voucher_date=date(2026, 6, 18),
        voucher_type="journal", fiscal_year=2026, period=6,
        total_vnd=Decimal("0"), status=AccountingVoucher.Status.DRAFT, created_by=auth_user,
    )
    AccountingVoucher.objects.create(
        company=company, voucher_no="BC-UX-B", voucher_date=date(2026, 6, 18),
        voucher_type="journal", fiscal_year=2026, period=6,
        total_vnd=Decimal("0"), status=AccountingVoucher.Status.DRAFT, created_by=auth_user,
    )
    import io
    import zipfile

    r = auth_client.get("/modern/vouchers/export/?search=BC-UX-A")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    shared = zf.read("xl/sharedStrings.xml").decode("utf-8") if "xl/sharedStrings.xml" in zf.namelist() else ""
    body = sheet + shared
    assert "BC-UX-A" in body
    assert "BC-UX-B" not in body


# ---------- Delete ----------


@pytest.mark.django_db
def test_customer_delete(auth_client, company):
    c = Customer.objects.create(code="UXDEL", name="To Delete", company=company)
    r = auth_client.post(f"/modern/customers/{c.pk}/delete/")
    assert r.status_code == 302
    assert not Customer.objects.filter(pk=c.pk).exists()


@pytest.mark.django_db
def test_voucher_delete_only_for_draft(auth_client, company, auth_user):
    v = AccountingVoucher.objects.create(
        company=company, voucher_no="BC-DEL", voucher_date=date(2026, 6, 18),
        voucher_type="journal", fiscal_year=2026, period=6, total_vnd=Decimal("0"),
        status=AccountingVoucher.Status.LEDGER, created_by=auth_user,
    )
    r = auth_client.post(f"/modern/vouchers/{v.pk}/delete/")
    assert r.status_code == 302
    # Posted voucher must NOT be deleted
    assert AccountingVoucher.objects.filter(pk=v.pk).exists()


# ---------- vnd filter ----------


def test_vnd_filter():
    from apps.ui_modern.templatetags.format_utils import vnd

    assert vnd(1234567) == "1,234,567"
    assert vnd(Decimal("999.99")) == "1,000"
    assert vnd(None) is None
    assert vnd("") == ""
    assert vnd(0) == "0"


# ---------- Breadcrumb include resolves ----------


def test_breadcrumb_include_renders():
    from django.template import engines

    t = engines["django"].from_string(
        "{% include 'shared/_breadcrumb.html' %}"
    )
    out = t.render({"page_title": "Test"})
    assert "Trang chủ" in out
    assert "Test" in out
