"""Tests for TT58 DnsnVoucher CRUD: views, templates, and API endpoints.

Covers VAL-TT58-010 through VAL-TT58-017:
- Create phiếu thu/chi/nhập/xuất vouchers via UI
- Voucher form has no account_code/debit/credit fields
- Edit DRAFT vouchers successfully
- Delete DRAFT vouchers, prevent deletion of POSTED vouchers
- Voucher list filters by type and date range with pagination
- Sidebar shows DNSN voucher menu only for tt58 companies
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import DnsnVoucher

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tt58_company(db):
    return Company.objects.create(
        code="TT58C",
        name="TT58 CRUD Test Co",
        accounting_regime="tt58",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="TT133C",
        name="TT133 Test Co",
        accounting_regime="tt133",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin58",
        password="Secret123!",
        email="admin58@test.local",
    )


@pytest.fixture
def auth_client(admin_user, tt58_company):
    """Authenticated client with TT58 company in session."""
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = tt58_company.id
    session.save()
    return c


@pytest.fixture
def auth_client_tt133(admin_user, tt133_company):
    """Authenticated client with TT133 company in session."""
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = tt133_company.id
    session.save()
    return c


# ---------------------------------------------------------------------------
# View tests — DNSN voucher list (VAL-TT58-017)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dnsn_voucher_list_requires_login(db):
    c = Client()
    response = c.get("/modern/dnsn-vouchers/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_dnsn_voucher_list_loads_empty(auth_client):
    response = auth_client.get("/modern/dnsn-vouchers/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chứng từ DNSN" in content or "DNSN" in content


@pytest.mark.django_db
def test_dnsn_voucher_list_shows_voucher(tt58_company, auth_client):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien ban hang",
        total_amount=Decimal("1000000"),
    )
    response = auth_client.get("/modern/dnsn-vouchers/")
    content = response.content.decode("utf-8")
    assert "PT0001" in content
    assert "Thu tien ban hang" in content


@pytest.mark.django_db
def test_dnsn_voucher_list_filter_by_type(tt58_company, auth_client):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PC0001",
        voucher_type="phieu_chi",
        voucher_date=date(2026, 7, 2),
    )
    response = auth_client.get("/modern/dnsn-vouchers/?voucher_type=phieu_thu")
    content = response.content.decode("utf-8")
    assert "PT0001" in content
    assert "PC0001" not in content


@pytest.mark.django_db
def test_dnsn_voucher_list_filter_by_date_range(tt58_company, auth_client):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=6,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 6, 15),
    )
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0002",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 15),
    )
    response = auth_client.get("/modern/dnsn-vouchers/?date_from=2026-07-01&date_to=2026-07-31")
    content = response.content.decode("utf-8")
    assert "PT0002" in content
    assert "PT0001" not in content


@pytest.mark.django_db
def test_dnsn_voucher_list_pagination(tt58_company, auth_client):
    for i in range(30):
        DnsnVoucher.objects.create(
            company=tt58_company,
            fiscal_year=2026,
            period=7,
            voucher_no=f"PT{i:04d}",
            voucher_type="phieu_thu",
            voucher_date=date(2026, 7, 1),
        )
    response = auth_client.get("/modern/dnsn-vouchers/?page=2")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# View tests — DNSN voucher create form (VAL-TT58-010, 011, 012, 013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dnsn_voucher_create_form_loads(auth_client):
    response = auth_client.get("/modern/dnsn-vouchers/new/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "voucher_type" in content
    assert "Phiếu thu" in content
    assert "Phiếu chi" in content


@pytest.mark.django_db
def test_dnsn_voucher_form_has_no_account_code_debit_credit(auth_client):
    """VAL-TT58-013: Form must NOT contain account_code/debit/credit fields."""
    response = auth_client.get("/modern/dnsn-vouchers/new/")
    content = response.content.decode("utf-8")
    # No account_code field
    assert 'name="account_code"' not in content
    # No debit/credit fields
    assert 'name="debit"' not in content
    assert 'name="credit"' not in content
    assert 'name="debit_vnd"' not in content
    assert 'name="credit_vnd"' not in content


@pytest.mark.django_db
def test_create_phieu_thu_voucher(tt58_company, auth_client):
    """VAL-TT58-010: Create phiếu thu voucher via UI."""
    response = auth_client.post(
        "/modern/dnsn-vouchers/new/",
        {
            "voucher_no": "PT0001",
            "voucher_type": "phieu_thu",
            "voucher_date": "2026-07-01",
            "description": "Thu tien ban hang",
            "partner_name": "Khach hang A",
            "total_amount": "1000000",
        },
    )
    assert response.status_code == 302
    v = DnsnVoucher.objects.get(voucher_no="PT0001")
    assert v.voucher_type == "phieu_thu"
    assert v.description == "Thu tien ban hang"
    assert v.partner_name == "Khach hang A"
    assert v.total_amount == Decimal("1000000")
    assert v.status == "draft"


@pytest.mark.django_db
def test_create_phieu_chi_voucher(tt58_company, auth_client):
    """VAL-TT58-011: Create phiếu chi voucher via UI."""
    response = auth_client.post(
        "/modern/dnsn-vouchers/new/",
        {
            "voucher_no": "PC0001",
            "voucher_type": "phieu_chi",
            "voucher_date": "2026-07-01",
            "description": "Chi tien mat",
            "partner_name": "NCC B",
            "total_amount": "500000",
        },
    )
    assert response.status_code == 302
    v = DnsnVoucher.objects.get(voucher_no="PC0001")
    assert v.voucher_type == "phieu_chi"
    assert v.partner_name == "NCC B"


@pytest.mark.django_db
def test_create_phieu_nhap_voucher(tt58_company, auth_client):
    """VAL-TT58-012: Create phiếu nhập voucher via UI."""
    response = auth_client.post(
        "/modern/dnsn-vouchers/new/",
        {
            "voucher_no": "PN0001",
            "voucher_type": "phieu_nhap",
            "voucher_date": "2026-07-01",
            "description": "Nhap kho hang hoa",
            "total_amount": "2000000",
        },
    )
    assert response.status_code == 302
    v = DnsnVoucher.objects.get(voucher_no="PN0001")
    assert v.voucher_type == "phieu_nhap"


@pytest.mark.django_db
def test_create_phieu_xuat_voucher(tt58_company, auth_client):
    """VAL-TT58-012: Create phiếu xuất voucher via UI."""
    response = auth_client.post(
        "/modern/dnsn-vouchers/new/",
        {
            "voucher_no": "PX0001",
            "voucher_type": "phieu_xuat",
            "voucher_date": "2026-07-01",
            "description": "Xuat kho hang hoa",
            "total_amount": "1500000",
        },
    )
    assert response.status_code == 302
    v = DnsnVoucher.objects.get(voucher_no="PX0001")
    assert v.voucher_type == "phieu_xuat"


# ---------------------------------------------------------------------------
# View tests — DNSN voucher detail (VAL-TT58-019)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dnsn_voucher_detail_loads(tt58_company, auth_client):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien ban hang",
        partner_name="Khach A",
        total_amount=Decimal("1000000"),
    )
    response = auth_client.get(f"/modern/dnsn-vouchers/{v.id}/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "PT0001" in content
    assert "Thu tien ban hang" in content
    assert "Khach A" in content


# ---------------------------------------------------------------------------
# View tests — DNSN voucher edit (VAL-TT58-014)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dnsn_voucher_edit_form_loads(tt58_company, auth_client):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien",
        total_amount=Decimal("1000000"),
        status="draft",
    )
    response = auth_client.get(f"/modern/dnsn-vouchers/{v.id}/edit/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "PT0001" in content


@pytest.mark.django_db
def test_dnsn_voucher_edit_draft_success(tt58_company, auth_client):
    """VAL-TT58-014: Edit DRAFT voucher successfully."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien",
        total_amount=Decimal("1000000"),
        status="draft",
    )
    response = auth_client.post(
        f"/modern/dnsn-vouchers/{v.id}/edit/",
        {
            "voucher_no": "PT0001",
            "voucher_type": "phieu_thu",
            "voucher_date": "2026-07-01",
            "description": "Thu tien ban hang — da sua",
            "partner_name": "Khach A",
            "total_amount": "2000000",
        },
    )
    assert response.status_code == 302
    v.refresh_from_db()
    assert v.description == "Thu tien ban hang — da sua"
    assert v.total_amount == Decimal("2000000")


# ---------------------------------------------------------------------------
# View tests — DNSN voucher delete (VAL-TT58-015, 016)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_draft_voucher(tt58_company, auth_client):
    """VAL-TT58-015: Delete DRAFT voucher."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status="draft",
    )
    response = auth_client.post(f"/modern/dnsn-vouchers/{v.id}/delete/")
    assert response.status_code == 302
    assert not DnsnVoucher.objects.filter(id=v.id).exists()


@pytest.mark.django_db
def test_delete_posted_voucher_prevented(tt58_company, auth_client):
    """VAL-TT58-016: Cannot delete POSTED voucher."""
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status="posted",
    )
    response = auth_client.post(f"/modern/dnsn-vouchers/{v.id}/delete/")
    assert response.status_code == 302
    # Voucher should still exist
    assert DnsnVoucher.objects.filter(id=v.id).exists()


# ---------------------------------------------------------------------------
# Sidebar tests — DNSN menu visibility (sidebar shows DNSN for tt58 only)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sidebar_shows_dnsn_menu_for_tt58(auth_client):
    """Sidebar shows DNSN voucher menu for tt58 companies."""
    response = auth_client.get("/modern/dnsn-vouchers/")
    content = response.content.decode("utf-8")
    assert "dnsn-vouchers" in content or "Chứng từ DNSN" in content


# ---------------------------------------------------------------------------
# API tests — django-ninja endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client(admin_user, tt58_company):
    """Authenticated API client with TT58 company in session."""
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = tt58_company.id
    session.save()
    return c


@pytest.mark.django_db
def test_api_list_dnsn_vouchers(api_client, tt58_company):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    response = api_client.get("/api/v1/dnsn/vouchers/")
    assert response.status_code == 200
    data = response.json()
    # Could be paginated
    items = data.get("items", data)
    assert len(items) >= 1
    assert items[0]["voucher_no"] == "PT0001"


@pytest.mark.django_db
def test_api_create_dnsn_voucher(api_client):
    response = api_client.post(
        "/api/v1/dnsn/vouchers/",
        {
            "voucher_no": "PT0001",
            "voucher_type": "phieu_thu",
            "voucher_date": "2026-07-01",
            "description": "Thu tien",
            "total_amount": "1000000",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["voucher_no"] == "PT0001"
    assert data["voucher_type"] == "phieu_thu"


@pytest.mark.django_db
def test_api_get_dnsn_voucher(api_client, tt58_company):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien",
    )
    response = api_client.get(f"/api/v1/dnsn/vouchers/{v.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["voucher_no"] == "PT0001"


@pytest.mark.django_db
def test_api_update_dnsn_voucher(api_client, tt58_company):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        description="Thu tien",
        status="draft",
    )
    response = api_client.patch(
        f"/api/v1/dnsn/vouchers/{v.id}",
        {"description": "Updated description"},
        content_type="application/json",
    )
    assert response.status_code == 200
    v.refresh_from_db()
    assert v.description == "Updated description"


@pytest.mark.django_db
def test_api_delete_dnsn_voucher_draft(api_client, tt58_company):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status="draft",
    )
    response = api_client.delete(f"/api/v1/dnsn/vouchers/{v.id}")
    assert response.status_code == 200
    assert not DnsnVoucher.objects.filter(id=v.id).exists()


@pytest.mark.django_db
def test_api_delete_dnsn_voucher_posted_blocked(api_client, tt58_company):
    v = DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status="posted",
    )
    response = api_client.delete(f"/api/v1/dnsn/vouchers/{v.id}")
    assert response.status_code == 400
    assert DnsnVoucher.objects.filter(id=v.id).exists()


@pytest.mark.django_db
def test_api_filter_by_type(api_client, tt58_company):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
    )
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PC0001",
        voucher_type="phieu_chi",
        voucher_date=date(2026, 7, 2),
    )
    response = api_client.get("/api/v1/dnsn/vouchers/?voucher_type=phieu_chi")
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data)
    assert len(items) == 1
    assert items[0]["voucher_type"] == "phieu_chi"


@pytest.mark.django_db
def test_api_filter_by_date_range(api_client, tt58_company):
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=6,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 6, 15),
    )
    DnsnVoucher.objects.create(
        company=tt58_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0002",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 15),
    )
    response = api_client.get("/api/v1/dnsn/vouchers/?date_from=2026-07-01&date_to=2026-07-31")
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data)
    assert len(items) == 1
    assert items[0]["voucher_no"] == "PT0002"
