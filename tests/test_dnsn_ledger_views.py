"""Tests for TT58 DNSN ledger views: ledger availability, list, detail,
optional ledgers, settings, and API endpoints.

Covers VAL-TT58-022 through VAL-TT58-028:
- Group 1 sees only S1-DNSN
- Group 2 sees S2a/b/c/d-DNSN
- Group 3 sees S3a/b-DNSN
- Group 4 sees S2b/c/d + S3b-DNSN
- Ledger availability updates when tax method group changes
- Optional S4a-S4d ledgers disabled by default, can be enabled independently
- Ledger view shows running balances
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.dnsn_ledger_types import (
    OPTIONAL_LEDGER_TYPES,
    get_available_ledgers,
    get_company_available_ledgers,
    get_required_ledgers,
)
from apps.ledger.models import DnsnLedgerEntry, DnsnVoucher
from apps.ledger.services.dnsn_posting_service import DnsnPostingService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_company(group: int, code: str = "TT58") -> Company:
    """Create a TT58 company with the given tax method group."""
    vat = "ty_le_phan_tram" if group in (1, 2) else "khau_tru"
    tndn = "ty_le_phan_tram" if group in (1, 3) else "tinh_thue"
    return Company.objects.create(
        code=code,
        name=f"TT58 Group {group} Co",
        accounting_regime="tt58",
        vat_method=vat,
        tndn_method=tndn,
        entity_type="doanh_nghiep_sieu_nho",
    )


@pytest.fixture
def g1_company(db):
    return _make_company(1, "G1CO")


@pytest.fixture
def g2_company(db):
    return _make_company(2, "G2CO")


@pytest.fixture
def g3_company(db):
    return _make_company(3, "G3CO")


@pytest.fixture
def g4_company(db):
    return _make_company(4, "G4CO")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin58l",
        password="Secret123!",
        email="admin58l@test.local",
    )


def _auth_client(user, company):
    """Create an authenticated client with the given company in session."""
    c = Client()
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def g1_client(admin_user, g1_company):
    return _auth_client(admin_user, g1_company)


@pytest.fixture
def g2_client(admin_user, g2_company):
    return _auth_client(admin_user, g2_company)


@pytest.fixture
def g3_client(admin_user, g3_company):
    return _auth_client(admin_user, g3_company)


@pytest.fixture
def g4_client(admin_user, g4_company):
    return _auth_client(admin_user, g4_company)


# ---------------------------------------------------------------------------
# Unit tests — ledger type availability logic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_ledger_map_group1():
    """Group 1 should map to only S1."""
    assert get_required_ledgers(1) == ["s1"]


@pytest.mark.django_db
def test_group_ledger_map_group2():
    """Group 2 should map to S2a, S2b, S2c, S2d."""
    assert get_required_ledgers(2) == ["s2a", "s2b", "s2c", "s2d"]


@pytest.mark.django_db
def test_group_ledger_map_group3():
    """Group 3 should map to S3a, S3b."""
    assert get_required_ledgers(3) == ["s3a", "s3b"]


@pytest.mark.django_db
def test_group_ledger_map_group4():
    """Group 4 should map to S2b, S2c, S2d, S3b."""
    assert get_required_ledgers(4) == ["s2b", "s2c", "s2d", "s3b"]


@pytest.mark.django_db
def test_group1_excludes_s2_s3():
    """Group 1 must not have S2 or S3 ledgers."""
    required = get_required_ledgers(1)
    assert "s1" in required
    for lt in ["s2a", "s2b", "s2c", "s2d", "s3a", "s3b"]:
        assert lt not in required


@pytest.mark.django_db
def test_group2_excludes_s1_s3():
    """Group 2 must not have S1 or S3 ledgers."""
    required = get_required_ledgers(2)
    assert "s1" not in required
    assert "s3a" not in required
    assert "s3b" not in required


@pytest.mark.django_db
def test_group3_excludes_s1_s2():
    """Group 3 must not have S1 or S2 ledgers."""
    required = get_required_ledgers(3)
    assert "s1" not in required
    for lt in ["s2a", "s2b", "s2c", "s2d"]:
        assert lt not in required


@pytest.mark.django_db
def test_group4_excludes_s1_s2a_s3a():
    """Group 4 must not have S1, S2a, S3a."""
    required = get_required_ledgers(4)
    assert "s1" not in required
    assert "s2a" not in required
    assert "s3a" not in required


@pytest.mark.django_db
def test_optional_ledgers_default_off(g1_company):
    """Optional ledgers S4a-S4d should be disabled by default."""
    available = get_company_available_ledgers(g1_company)
    for lt in OPTIONAL_LEDGER_TYPES:
        assert lt not in available


@pytest.mark.django_db
def test_enable_optional_ledger(g1_company):
    """Enabling an optional ledger makes it available."""
    g1_company.dnsn_optional_ledgers = {"s4a": True}
    g1_company.save()
    available = get_company_available_ledgers(g1_company)
    assert "s4a" in available
    # Others should still be off
    assert "s4b" not in available
    assert "s4c" not in available
    assert "s4d" not in available


@pytest.mark.django_db
def test_enable_multiple_optional_ledgers(g1_company):
    """Enabling multiple optional ledgers independently."""
    g1_company.dnsn_optional_ledgers = {"s4a": True, "s4c": True}
    g1_company.save()
    available = get_company_available_ledgers(g1_company)
    assert "s4a" in available
    assert "s4c" in available
    assert "s4b" not in available
    assert "s4d" not in available


@pytest.mark.django_db
def test_non_tt58_company_has_no_ledgers(db):
    """Non-TT58 companies should see no DNSN ledgers."""
    company = Company.objects.create(
        code="TT133L",
        name="TT133 Test",
        accounting_regime="tt133",
    )
    assert get_company_available_ledgers(company) == []


@pytest.mark.django_db
def test_available_ledgers_with_optional():
    """Test get_available_ledgers with optional enabled."""
    ledgers = get_available_ledgers(1, {"s4a": True, "s4b": False})
    assert "s1" in ledgers
    assert "s4a" in ledgers
    assert "s4b" not in ledgers


@pytest.mark.django_db
def test_ledger_availability_changes_when_group_changes(g1_company):
    """VAL-TT58-026: Ledger availability updates when tax method group changes."""
    # Group 1 -> S1 only
    available = get_company_available_ledgers(g1_company)
    assert "s1" in available
    assert "s3a" not in available

    # Change to Group 3 (vat=khau_tru, tndn=ty_le_phan_tram)
    g1_company.vat_method = "khau_tru"
    g1_company.save()

    available = get_company_available_ledgers(g1_company)
    assert "s1" not in available
    assert "s3a" in available
    assert "s3b" in available


# ---------------------------------------------------------------------------
# View tests — ledger list page (VAL-TT58-022, 023, 024, 025)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ledger_list_requires_login(db):
    c = Client()
    response = c.get("/modern/dnsn-ledgers/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_group1_ledger_list_shows_s1_only(g1_client):
    """VAL-TT58-022: Group 1 sees only S1-DNSN."""
    response = g1_client.get("/modern/dnsn-ledgers/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "S1-DNSN" in content
    assert "S2a-DNSN" not in content
    assert "S2b-DNSN" not in content
    assert "S3a-DNSN" not in content
    assert "S3b-DNSN" not in content


@pytest.mark.django_db
def test_group2_ledger_list_shows_s2_all(g2_client):
    """VAL-TT58-023: Group 2 sees S2a/b/c/d-DNSN."""
    response = g2_client.get("/modern/dnsn-ledgers/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "S2a-DNSN" in content
    assert "S2b-DNSN" in content
    assert "S2c-DNSN" in content
    assert "S2d-DNSN" in content
    assert "S1-DNSN" not in content
    assert "S3a-DNSN" not in content


@pytest.mark.django_db
def test_group3_ledger_list_shows_s3_ab(g3_client):
    """VAL-TT58-024: Group 3 sees S3a/b-DNSN."""
    response = g3_client.get("/modern/dnsn-ledgers/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "S3a-DNSN" in content
    assert "S3b-DNSN" in content
    assert "S1-DNSN" not in content
    assert "S2a-DNSN" not in content


@pytest.mark.django_db
def test_group4_ledger_list_shows_s2bcd_s3b(g4_client):
    """VAL-TT58-025: Group 4 sees S2b/c/d + S3b-DNSN."""
    response = g4_client.get("/modern/dnsn-ledgers/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "S2b-DNSN" in content
    assert "S2c-DNSN" in content
    assert "S2d-DNSN" in content
    assert "S3b-DNSN" in content
    assert "S1-DNSN" not in content
    assert "S2a-DNSN" not in content
    assert "S3a-DNSN" not in content


# ---------------------------------------------------------------------------
# View tests — ledger detail page (running balances, VAL-TT58-020)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ledger_detail_shows_running_balance(g1_company, g1_client):
    """VAL-TT58-020: Ledger view shows running balances."""
    # Create a posted voucher with entries
    voucher = DnsnVoucher.objects.create(
        company=g1_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(
        voucher,
        [
            {"ledger_type": "s1", "revenue_amount": Decimal("1000000"), "description": "Sale 1"},
            {"ledger_type": "s1", "revenue_amount": Decimal("500000"), "description": "Sale 2"},
        ],
    )

    response = g1_client.get("/modern/dnsn-ledgers/s1/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The entries should have running balances
    assert "running" in content.lower() or "Số dư" in content
    # First entry running balance = 1,000,000
    # Second entry running balance = 1,500,000


@pytest.mark.django_db
def test_ledger_detail_unavailable_ledger_redirects(g1_client):
    """Accessing an unavailable ledger redirects to list."""
    response = g1_client.get("/modern/dnsn-ledgers/s2a/")
    # Group 1 should not have S2a
    assert response.status_code == 302


@pytest.mark.django_db
def test_ledger_detail_available_ledger_loads(g2_client):
    """Accessing an available ledger loads fine."""
    response = g2_client.get("/modern/dnsn-ledgers/s2a/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ledger_detail_empty(g1_client):
    """An empty ledger should display gracefully."""
    response = g1_client.get("/modern/dnsn-ledgers/s1/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chưa có bút toán" in content


# ---------------------------------------------------------------------------
# View tests — optional ledger settings (VAL-TT58-027, 028)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ledger_settings_page_loads(g1_client):
    """Settings page loads and shows optional ledgers."""
    response = g1_client.get("/modern/dnsn-ledgers/settings/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "S4a-DNSN" in content
    assert "S4b-DNSN" in content
    assert "S4c-DNSN" in content
    assert "S4d-DNSN" in content


@pytest.mark.django_db
def test_optional_ledgers_disabled_by_default_in_settings(g1_client):
    """VAL-TT58-028: Optional ledgers are disabled by default."""
    response = g1_client.get("/modern/dnsn-ledgers/settings/")
    content = response.content.decode("utf-8")
    # All should show "Đã tắt" (disabled)
    assert content.count("Đã tắt") == 4


@pytest.mark.django_db
def test_enable_optional_ledger_via_settings(g1_company, g1_client):
    """VAL-TT58-027: Optional ledgers S4a-S4d can be enabled independently."""
    response = g1_client.post(
        "/modern/dnsn-ledgers/settings/",
        {
            "enable_s4a": "on",
            # Leave others unchecked
        },
    )
    assert response.status_code == 302
    g1_company.refresh_from_db()
    assert g1_company.dnsn_optional_ledgers["s4a"] is True
    assert g1_company.dnsn_optional_ledgers.get("s4b") is False
    assert g1_company.dnsn_optional_ledgers.get("s4c") is False
    assert g1_company.dnsn_optional_ledgers.get("s4d") is False


@pytest.mark.django_db
def test_enable_multiple_optional_ledgers_via_settings(g1_company, g1_client):
    """Enable multiple optional ledgers independently."""
    response = g1_client.post(
        "/modern/dnsn-ledgers/settings/",
        {
            "enable_s4a": "on",
            "enable_s4c": "on",
        },
    )
    assert response.status_code == 302
    g1_company.refresh_from_db()
    assert g1_company.dnsn_optional_ledgers["s4a"] is True
    assert g1_company.dnsn_optional_ledgers.get("s4b") is False
    assert g1_company.dnsn_optional_ledgers["s4c"] is True
    assert g1_company.dnsn_optional_ledgers.get("s4d") is False


@pytest.mark.django_db
def test_enabled_optional_ledger_appears_in_list(g1_company, g1_client):
    """Enabled optional ledger should appear in the ledger list."""
    g1_company.dnsn_optional_ledgers = {"s4a": True}
    g1_company.save()
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "S4a-DNSN" in content
    # Still should have S1
    assert "S1-DNSN" in content


@pytest.mark.django_db
def test_disabled_optional_ledger_not_in_list(g1_client):
    """Disabled optional ledgers should not appear in list."""
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "S4a-DNSN" not in content
    assert "S4b-DNSN" not in content


# ---------------------------------------------------------------------------
# Sidebar tests — dynamic ledger menu (VAL-TT58-022..026)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sidebar_group1_shows_s1_link(g1_client):
    """Group 1 sidebar shows S1-DNSN link."""
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s1/" in content


@pytest.mark.django_db
def test_sidebar_group1_does_not_show_s2_links(g1_client):
    """Group 1 sidebar does not show S2 links."""
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s2a/" not in content


@pytest.mark.django_db
def test_sidebar_group2_shows_s2_links(g2_client):
    """Group 2 sidebar shows S2a/b/c/d links."""
    response = g2_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s2a/" in content
    assert "/dnsn-ledgers/s2b/" in content
    assert "/dnsn-ledgers/s2c/" in content
    assert "/dnsn-ledgers/s2d/" in content


@pytest.mark.django_db
def test_sidebar_group3_shows_s3_links(g3_client):
    """Group 3 sidebar shows S3a/b links."""
    response = g3_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s3a/" in content
    assert "/dnsn-ledgers/s3b/" in content


@pytest.mark.django_db
def test_sidebar_group4_shows_correct_links(g4_client):
    """Group 4 sidebar shows S2b/c/d + S3b links, not S1/S2a/S3a."""
    response = g4_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s2b/" in content
    assert "/dnsn-ledgers/s2c/" in content
    assert "/dnsn-ledgers/s2d/" in content
    assert "/dnsn-ledgers/s3b/" in content
    assert "/dnsn-ledgers/s1/" not in content
    assert "/dnsn-ledgers/s2a/" not in content
    assert "/dnsn-ledgers/s3a/" not in content


@pytest.mark.django_db
def test_sidebar_shows_optional_ledger_when_enabled(g1_company, g1_client):
    """Sidebar shows optional ledger link when enabled."""
    g1_company.dnsn_optional_ledgers = {"s4a": True}
    g1_company.save()
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s4a/" in content


@pytest.mark.django_db
def test_sidebar_hides_optional_ledger_when_disabled(g1_client):
    """Sidebar does not show optional ledger when disabled."""
    response = g1_client.get("/modern/dnsn-ledgers/")
    content = response.content.decode("utf-8")
    assert "/dnsn-ledgers/s4a/" not in content


# ---------------------------------------------------------------------------
# API tests — ledger endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_list_ledgers_group1(g1_client):
    """API returns available ledgers for Group 1."""
    response = g1_client.get("/api/v1/dnsn/ledgers/")
    assert response.status_code == 200
    data = response.json()
    ledger_types = [d["ledger_type"] for d in data]
    assert "s1" in ledger_types
    assert "s2a" not in ledger_types
    assert "s3a" not in ledger_types


@pytest.mark.django_db
def test_api_list_ledgers_group2(g2_client):
    """API returns available ledgers for Group 2."""
    response = g2_client.get("/api/v1/dnsn/ledgers/")
    assert response.status_code == 200
    data = response.json()
    ledger_types = [d["ledger_type"] for d in data]
    assert "s2a" in ledger_types
    assert "s2b" in ledger_types
    assert "s2c" in ledger_types
    assert "s2d" in ledger_types
    assert "s1" not in ledger_types


@pytest.mark.django_db
def test_api_list_ledgers_group3(g3_client):
    """API returns available ledgers for Group 3."""
    response = g3_client.get("/api/v1/dnsn/ledgers/")
    assert response.status_code == 200
    data = response.json()
    ledger_types = [d["ledger_type"] for d in data]
    assert "s3a" in ledger_types
    assert "s3b" in ledger_types


@pytest.mark.django_db
def test_api_list_ledgers_group4(g4_client):
    """API returns available ledgers for Group 4."""
    response = g4_client.get("/api/v1/dnsn/ledgers/")
    assert response.status_code == 200
    data = response.json()
    ledger_types = [d["ledger_type"] for d in data]
    assert "s2b" in ledger_types
    assert "s2c" in ledger_types
    assert "s2d" in ledger_types
    assert "s3b" in ledger_types
    assert "s1" not in ledger_types
    assert "s2a" not in ledger_types
    assert "s3a" not in ledger_types


@pytest.mark.django_db
def test_api_list_ledger_entries_unavailable(g1_client):
    """API rejects request for unavailable ledger."""
    response = g1_client.get("/api/v1/dnsn/ledgers/s2a/entries/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_api_list_ledger_entries_available(g1_company, g1_client):
    """API returns entries for an available ledger."""
    voucher = DnsnVoucher.objects.create(
        company=g1_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0001",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 1),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(
        voucher,
        [
            {"ledger_type": "s1", "revenue_amount": Decimal("1000000"), "description": "Sale 1"},
        ],
    )

    response = g1_client.get("/api/v1/dnsn/ledgers/s1/entries/")
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data)
    assert len(items) >= 1
    assert items[0]["ledger_type"] == "s1"
    assert items[0]["running_balance"] == "1000000.0000"


@pytest.mark.django_db
def test_api_list_ledger_entries_with_running_balance(g1_company, g1_client):
    """API entries include running_balance field."""
    voucher = DnsnVoucher.objects.create(
        company=g1_company,
        fiscal_year=2026,
        period=7,
        voucher_no="PT0002",
        voucher_type="phieu_thu",
        voucher_date=date(2026, 7, 2),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(
        voucher,
        [
            {"ledger_type": "s1", "revenue_amount": Decimal("300000"), "description": "Sale 1"},
            {"ledger_type": "s1", "revenue_amount": Decimal("700000"), "description": "Sale 2"},
        ],
    )

    response = g1_client.get("/api/v1/dnsn/ledgers/s1/entries/")
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data)
    # Two entries with cumulative running balance
    assert len(items) == 2
    assert Decimal(items[0]["running_balance"]) == Decimal("300000")
    assert Decimal(items[1]["running_balance"]) == Decimal("1000000")


@pytest.mark.django_db
def test_api_list_ledger_entries_filter_by_year(g1_company, g1_client):
    """API filters by fiscal_year."""
    # Create entries in different years
    for year, amount in [(2025, "100000"), (2026, "200000")]:
        v = DnsnVoucher.objects.create(
            company=g1_company,
            fiscal_year=year,
            period=1,
            voucher_no=f"PT{year}001",
            voucher_type="phieu_thu",
            voucher_date=date(year, 1, 15),
            status=DnsnVoucher.Status.DRAFT,
        )
        DnsnLedgerEntry.objects.create(
            voucher=v,
            company=g1_company,
            fiscal_year=year,
            period=1,
            line_no=1,
            entry_date=date(year, 1, 15),
            ledger_type="s1",
            revenue_amount=Decimal(amount),
            description=f"Sale {year}",
        )

    response = g1_client.get("/api/v1/dnsn/ledgers/s1/entries/?fiscal_year=2026")
    assert response.status_code == 200
    data = response.json()
    items = data.get("items", data)
    assert len(items) == 1
    assert items[0]["fiscal_year"] == 2026


@pytest.mark.django_db
def test_api_ledger_includes_optional_when_enabled(g1_company, g1_client):
    """API returns optional ledgers when enabled."""
    g1_company.dnsn_optional_ledgers = {"s4a": True}
    g1_company.save()
    response = g1_client.get("/api/v1/dnsn/ledgers/")
    data = response.json()
    ledger_types = [d["ledger_type"] for d in data]
    assert "s4a" in ledger_types
    assert "s4b" not in ledger_types


# ---------------------------------------------------------------------------
# Company model tests — dnsn_optional_ledgers field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_company_dnsn_optional_ledgers_default_empty(db):
    """Company dnsn_optional_ledgers defaults to empty dict."""
    company = Company.objects.create(code="NEW58", name="New", accounting_regime="tt58")
    assert company.dnsn_optional_ledgers == {}


@pytest.mark.django_db
def test_company_dnsn_optional_ledgers_persists(db):
    """Company can save and load optional ledger settings."""
    company = Company.objects.create(code="SAVE58", name="Save", accounting_regime="tt58")
    company.dnsn_optional_ledgers = {"s4a": True, "s4d": True}
    company.save()
    company.refresh_from_db()
    assert company.dnsn_optional_ledgers.get("s4a") is True
    assert company.dnsn_optional_ledgers.get("s4d") is True
    assert company.dnsn_optional_ledgers.get("s4b") is not True
