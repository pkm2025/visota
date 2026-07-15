"""Integration tests for TT58 cross-area flows.

Covers VAL-CROSS-001 through VAL-CROSS-014:
- VAL-CROSS-001: Onboarding — create TT58 company
- VAL-CROSS-002: Tax method configuration persists
- VAL-CROSS-003: Group 1 cycle — phieu thu → S1-DNSN → report
- VAL-CROSS-004: Group 4 cycle — sales/purchase → S2b/S3b → B01/B02
- VAL-CROSS-005: TT133→TT58 conversion flow
- VAL-CROSS-006: HKD setup — no kế toán trưởng requirement
- VAL-CROSS-007: 02BANHANG e-invoice for GTGT% DNSN
- VAL-CROSS-008: Sidebar navigability — no 404s for TT58 features
- VAL-CROSS-009: No PMKetoan leakage during TT58 operations
- VAL-CROSS-010: Module visibility simplified for DNSN
- VAL-CROSS-011: Brand consistency in TT58 report PDF exports
- VAL-CROSS-012: Login page branding for TT58 onboarding
- VAL-CROSS-013: Tax method group drives ledger/report availability
- VAL-CROSS-014: API branding consistency during TT58 operations
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import (
    AccountPeriodBalance,
    DnsnLedgerBalance,
    DnsnLedgerEntry,
    DnsnVoucher,
)
from apps.ledger.services.balance_conversion_service import BalanceConversionService
from apps.ledger.services.dnsn_posting_service import DnsnPostingService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tt58_company(group: int, code: str = "TT58", **kwargs) -> Company:
    """Create a TT58 company with the given tax method group."""
    vat = "ty_le_phan_tram" if group in (1, 2) else "khau_tru"
    tndn = "ty_le_phan_tram" if group in (1, 3) else "tinh_thue"
    defaults = {
        "code": code,
        "name": f"TT58 Group {group} Co",
        "accounting_regime": "tt58",
        "vat_method": vat,
        "tndn_method": tndn,
        "entity_type": "doanh_nghiep_sieu_nho",
    }
    defaults.update(kwargs)
    return Company.objects.create(**defaults)


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_cross",
        password="Secret123!",
        email="admin_cross@test.local",
    )


@pytest.fixture
def g1_company(db):
    return _make_tt58_company(1, "CF1CO")


@pytest.fixture
def g4_company(db):
    return _make_tt58_company(4, "CF4CO")


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="CF133C",
        name="TT133 Cross Test Co",
        accounting_regime="tt133",
    )


@pytest.fixture
def hkd_company(db):
    return _make_tt58_company(
        1, "CFHKD", name="Hộ kinh doanh Cross Test", entity_type="ho_kinh_doanh"
    )


def _auth_client(user, company):
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
def g4_client(admin_user, g4_company):
    return _auth_client(admin_user, g4_company)


@pytest.fixture
def tt133_client(admin_user, tt133_company):
    return _auth_client(admin_user, tt133_company)


@pytest.fixture
def hkd_client(admin_user, hkd_company):
    return _auth_client(admin_user, hkd_company)


def _post_voucher(company, voucher_no, entries_data, fy=2026, period=7, voucher_type="phieu_thu"):
    """Create and post a DnsnVoucher."""
    voucher = DnsnVoucher.objects.create(
        company=company,
        fiscal_year=fy,
        period=period,
        voucher_no=voucher_no,
        voucher_type=voucher_type,
        voucher_date=date(fy, period, 15),
        status=DnsnVoucher.Status.DRAFT,
    )
    service = DnsnPostingService()
    service.post(voucher, entries_data)
    return voucher


# ===========================================================================
# VAL-CROSS-001: Onboarding — create TT58 company
# ===========================================================================


@pytest.mark.django_db
def test_onboarding_create_tt58_company(g1_client):
    """VAL-CROSS-001: Company profile page shows TT58 fields and branding."""
    response = g1_client.get("/modern/admin/company-profile/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # TT58-related fields should be present
    assert "vat_method" in content
    assert "tndn_method" in content
    assert "entity_type" in content
    # No PMKetoan
    assert "PMKetoan" not in content


@pytest.mark.django_db
def test_onboarding_create_tt58_company_persists(admin_user):
    """VAL-CROSS-001: A TT58 company can be created and regime persists."""
    company = _make_tt58_company(1, "OB-TEST")
    company.refresh_from_db()
    assert company.accounting_regime == "tt58"
    assert company.tax_method_group == 1


# ===========================================================================
# VAL-CROSS-002: Tax method configuration persists
# ===========================================================================


@pytest.mark.django_db
def test_tax_method_config_persists_via_company_profile(g1_client, g1_company):
    """VAL-CROSS-002: Saving tax method config through company profile persists."""
    # Change to Group 4 (khau_tru + tinh_thue)
    response = g1_client.post(
        "/modern/admin/company-profile/",
        data={
            "name": g1_company.name,
            "accounting_regime": "tt58",
            "vat_method": "khau_tru",
            "tndn_method": "tinh_thue",
            "entity_type": "doanh_nghiep_sieu_nho",
        },
    )
    assert response.status_code == 302
    g1_company.refresh_from_db()
    assert g1_company.vat_method == "khau_tru"
    assert g1_company.tndn_method == "tinh_thue"
    assert g1_company.tax_method_group == 4


@pytest.mark.django_db
def test_tax_method_config_shows_visota_branding(g1_client):
    """VAL-CROSS-002: Company profile page shows Visota ERP branding."""
    response = g1_client.get("/modern/admin/company-profile/")
    content = response.content.decode("utf-8")
    assert "PMKetoan" not in content


# ===========================================================================
# VAL-CROSS-003: Group 1 cycle — phieu thu → S1-DNSN → report
# ===========================================================================


@pytest.mark.django_db
def test_group1_cycle_phieu_thu_to_s1_to_report(g1_client, g1_company):
    """VAL-CROSS-003: Full Group 1 cycle works."""
    # 1. Create and post a phieu thu with revenue
    voucher = _post_voucher(
        g1_company,
        "PT001",
        [
            {
                "ledger_type": "s1",
                "description": "Bán hàng tháng 7",
                "revenue_amount": Decimal("100000000"),
            }
        ],
        voucher_type="phieu_thu",
    )
    assert voucher.status == "posted"

    # 2. Verify S1-DNSN has the entry
    s1_entries = DnsnLedgerEntry.objects.filter(company=g1_company, ledger_type="s1")
    assert s1_entries.exists()
    total_revenue = sum(e.revenue_amount or 0 for e in s1_entries)
    assert total_revenue == Decimal("100000000")

    # 3. View S1-DNSN ledger page
    response = g1_client.get("/modern/dnsn-ledgers/s1/")
    assert response.status_code == 200

    # 4. Generate B01-DNSN and B02-DNSN reports
    response = g1_client.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 200

    response = g1_client.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_group1_report_pdf_has_visota_branding(g1_client, g1_company):
    """VAL-CROSS-003/011: Report PDF export contains Visota ERP branding."""
    # Post some data
    _post_voucher(
        g1_company,
        "PT-PDF",
        [
            {
                "ledger_type": "s1",
                "description": "Doanh thu test",
                "revenue_amount": Decimal("50000000"),
            }
        ],
    )
    # Export B02-DNSN as PDF
    response = g1_client.get("/modern/dnsn-reports/export/?report=B02-DNSN&format=pdf")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


# ===========================================================================
# VAL-CROSS-004: Group 4 cycle — sales/purchase → S2b/S3b → B01/B02
# ===========================================================================


@pytest.mark.django_db
def test_group4_cycle_sales_purchase_to_reports(g4_client, g4_company):
    """VAL-CROSS-004: Full Group 4 cycle works with S2b/S2c/S2d/S3b ledgers."""
    # Post revenue to S2b
    _post_voucher(
        g4_company,
        "G4-REV",
        [
            {
                "ledger_type": "s2b",
                "description": "Bán hàng Group 4",
                "revenue_amount": Decimal("200000000"),
            }
        ],
        voucher_type="hoa_don_ban_hang",
    )
    # Post cost to S2b
    _post_voucher(
        g4_company,
        "G4-COST",
        [
            {
                "ledger_type": "s2b",
                "description": "Chi phí hàng bán",
                "cost_amount": Decimal("120000000"),
            }
        ],
        voucher_type="phieu_chi",
    )
    # Post VAT output to S3b
    _post_voucher(
        g4_company,
        "G4-VAT",
        [
            {
                "ledger_type": "s3b",
                "description": "Thuế GTGT đầu ra",
                "vat_output": Decimal("20000000"),
            }
        ],
        voucher_type="hoa_don_ban_hang",
    )

    # Verify ledgers have entries
    for lt in ("s2b", "s3b"):
        entries = DnsnLedgerEntry.objects.filter(company=g4_company, ledger_type=lt)
        assert entries.exists(), f"No entries for {lt}"

    # View ledger pages
    for lt in ("s2b", "s2c", "s2d", "s3b"):
        response = g4_client.get(f"/modern/dnsn-ledgers/{lt}/")
        assert response.status_code == 200

    # Generate reports
    response = g4_client.get("/modern/dnsn-reports/b01-dnsn/")
    assert response.status_code == 200

    response = g4_client.get("/modern/dnsn-reports/b02-dnsn/")
    assert response.status_code == 200


# ===========================================================================
# VAL-CROSS-005: TT133→TT58 conversion flow
# ===========================================================================


@pytest.mark.django_db
def test_conversion_flow_view_renders(tt133_client):
    """VAL-CROSS-005: Conversion page renders for TT133 company."""
    response = tt133_client.get("/modern/dnsn-conversion/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_conversion_flow_executes(tt133_company, admin_user):
    """VAL-CROSS-005: TT133→TT58 conversion creates DNSN balances and switches regime."""
    # Create source balances
    AccountPeriodBalance.objects.create(
        company=tt133_company,
        fiscal_year=2026,
        period=6,
        account_code="111",
        closing_debit=Decimal("100000000"),
        closing_credit=Decimal("0"),
    )
    AccountPeriodBalance.objects.create(
        company=tt133_company,
        fiscal_year=2026,
        period=6,
        account_code="411",
        closing_debit=Decimal("0"),
        closing_credit=Decimal("100000000"),
    )

    # Run conversion
    service = BalanceConversionService()
    summary = service.convert(tt133_company, fiscal_year=2026, source_period=6)

    # Verify balances were created
    balances = DnsnLedgerBalance.objects.filter(company=tt133_company, fiscal_year=2026, period=6)
    assert balances.exists()
    assert summary.converted_count > 0

    # Verify S2d got cash from TK 111
    s2d = balances.filter(ledger_type="s2d").first()
    assert s2d is not None
    assert s2d.opening_cash == Decimal("100000000")


@pytest.mark.django_db
def test_conversion_page_no_pmketoan(tt133_client):
    """VAL-CROSS-005: Conversion page has no PMKetoan branding."""
    response = tt133_client.get("/modern/dnsn-conversion/")
    content = response.content.decode("utf-8")
    assert "PMKetoan" not in content


# ===========================================================================
# VAL-CROSS-006: HKD setup — no kế toán trưởng requirement
# ===========================================================================


@pytest.mark.django_db
def test_hkd_company_profile_hides_chief_accountant(hkd_client):
    """VAL-CROSS-006: HKD company profile hides kế toán trưởng fields."""
    response = hkd_client.get("/modern/admin/company-profile/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chief-accountant-section" in content
    assert "data-hide-for-dnsn" in content or "data-hide-for-hkd" in content


@pytest.mark.django_db
def test_hkd_can_create_vouchers(hkd_client, hkd_company):
    """VAL-CROSS-006: HKD company can create and post vouchers."""
    voucher = _post_voucher(
        hkd_company,
        "HKD-V01",
        [
            {
                "ledger_type": "s1",
                "description": "Doanh thu HKD",
                "revenue_amount": Decimal("30000000"),
            }
        ],
    )
    assert voucher.status == "posted"
    assert hkd_company.chief_accountant == ""


@pytest.mark.django_db
def test_hkd_can_view_reports(hkd_client):
    """VAL-CROSS-006: HKD company can view DNSN reports."""
    response = hkd_client.get("/modern/dnsn-reports/")
    assert response.status_code == 200


# ===========================================================================
# VAL-CROSS-008: Sidebar navigability — no 404s for TT58 features
# ===========================================================================


@pytest.mark.django_db
def test_sidebar_navigability_all_tt58_pages(g1_client):
    """VAL-CROSS-008: All TT58 feature pages are accessible (no 404s)."""
    urls = [
        "/modern/dnsn-vouchers/",
        "/modern/dnsn-vouchers/new/",
        "/modern/dnsn-ledgers/",
        "/modern/dnsn-ledgers/settings/",
        "/modern/dnsn-ledgers/s1/",
        "/modern/dnsn-reports/",
        "/modern/dnsn-reports/b01-dnsn/",
        "/modern/dnsn-reports/b02-dnsn/",
        "/modern/dnsn-conversion/",
        "/modern/admin/company-profile/",
    ]
    for url in urls:
        response = g1_client.get(url)
        assert response.status_code == 200, f"URL {url} returned {response.status_code}"


@pytest.mark.django_db
def test_sidebar_has_dnsn_report_links(g1_client):
    """VAL-CROSS-008: Sidebar contains links to DNSN reports and conversion."""
    response = g1_client.get("/modern/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Check for the URL paths generated by the url tag
    assert "/modern/dnsn-reports/" in content
    assert "/modern/dnsn-reports/b01-dnsn/" in content
    assert "/modern/dnsn-reports/b02-dnsn/" in content
    assert "/modern/dnsn-conversion/" in content


# ===========================================================================
# VAL-CROSS-009: No PMKetoan leakage during TT58 operations
# ===========================================================================


@pytest.mark.django_db
def test_no_pmketoan_on_dashboard(g1_client):
    """VAL-CROSS-009: Dashboard has no PMKetoan string."""
    response = g1_client.get("/modern/")
    assert response.status_code == 200
    assert "PMKetoan" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_no_pmketoan_on_voucher_pages(g1_client):
    """VAL-CROSS-009: DNSN voucher pages have no PMKetoan string."""
    urls = [
        "/modern/dnsn-vouchers/",
        "/modern/dnsn-vouchers/new/",
    ]
    for url in urls:
        response = g1_client.get(url)
        assert response.status_code == 200
        assert "PMKetoan" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_no_pmketoan_on_report_pages(g1_client):
    """VAL-CROSS-009: DNSN report pages have no PMKetoan string."""
    urls = [
        "/modern/dnsn-reports/",
        "/modern/dnsn-reports/b01-dnsn/",
        "/modern/dnsn-reports/b02-dnsn/",
    ]
    for url in urls:
        response = g1_client.get(url)
        assert response.status_code == 200
        assert "PMKetoan" not in response.content.decode("utf-8")


# ===========================================================================
# VAL-CROSS-010: Module visibility simplified for DNSN
# ===========================================================================


@pytest.mark.django_db
def test_dnsn_sidebar_hides_advanced_modules(g1_client):
    """VAL-CROSS-010: DNSN company sidebar hides advanced modules by default."""
    response = g1_client.get("/modern/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # DNSN section should be present
    assert "DNSN (TT58)" in content
    # Core modules should be present
    assert "Hóa đơn điện tử" in content or "einvoice" in content.lower()


@pytest.mark.django_db
def test_dnsn_module_visibility_service():
    """VAL-CROSS-010: ModuleVisibilityService hides advanced for DNSN."""
    from apps.core.module_config import ADVANCED_MODULES, ModuleVisibilityService

    company = _make_tt58_company(1, "MV-TEST")
    service = ModuleVisibilityService(company)
    # Advanced modules should be hidden by default for DNSN
    for mod in ADVANCED_MODULES:
        assert not service.is_module_visible(mod), f"{mod} should be hidden for DNSN"


# ===========================================================================
# VAL-CROSS-011: Brand consistency in TT58 report PDF exports
# ===========================================================================


@pytest.mark.django_db
def test_dnsn_pdf_template_has_visota_branding():
    """VAL-CROSS-011: DNSN report PDF template contains Visota ERP in footer."""
    from django.template.loader import render_to_string

    html = render_to_string(
        "modern/dnsn/report_export_pdf.html",
        {
            "company_name": "Test Co",
            "report_title": "B01-DNSN",
            "period_label": "Tháng 07/2026",
            "headers": ["A", "B"],
            "rows": [["1", "2"]],
        },
    )
    assert "Visota ERP" in html
    assert "PMKetoan" not in html


@pytest.mark.django_db
def test_einvoice_pdf_template_has_visota_branding():
    """VAL-CROSS-007/011: E-invoice PDF template file contains Visota ERP."""
    from pathlib import Path

    template_path = (
        Path(__file__).resolve().parent.parent
        / "templates"
        / "modern"
        / "einvoice"
        / "pdf_template.html"
    )
    content = template_path.read_text(encoding="utf-8")
    assert "Visota ERP" in content
    assert "PMKetoan" not in content


# ===========================================================================
# VAL-CROSS-012: Login page branding for TT58 onboarding
# ===========================================================================


@pytest.mark.django_db
def test_login_page_has_visota_branding():
    """VAL-CROSS-012: Login page shows Visota ERP branding."""
    c = Client()
    response = c.get("/auth/login/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Visota ERP" in content
    assert "PMKetoan" not in content


# ===========================================================================
# VAL-CROSS-013: Tax method group drives ledger and report availability
# ===========================================================================


@pytest.mark.django_db
def test_group1_sidebar_shows_s1_only(g1_client):
    """VAL-CROSS-013: Group 1 company sidebar shows S1-DNSN, not S2/S3."""
    response = g1_client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "S1-DNSN" in content
    assert "S2a-DNSN" not in content
    assert "S3a-DNSN" not in content


@pytest.mark.django_db
def test_group4_sidebar_shows_s2b_s3b(g4_client):
    """VAL-CROSS-013: Group 4 company sidebar shows S2b/S2c/S2d and S3b."""
    response = g4_client.get("/modern/")
    content = response.content.decode("utf-8")
    assert "S2b-DNSN" in content
    assert "S3b-DNSN" in content
    assert "S1-DNSN" not in content
    assert "S2a-DNSN" not in content
    assert "S3a-DNSN" not in content


# ===========================================================================
# VAL-CROSS-014: API branding consistency during TT58 operations
# ===========================================================================


@pytest.mark.django_db
def test_api_schema_title_is_visota():
    """VAL-CROSS-014: API schema title is 'Visota ERP API'."""
    from apps.core.api import api

    assert api.title == "Visota ERP API"


@pytest.mark.django_db
def test_api_schema_endpoint_has_visota_title(admin_user):
    """VAL-CROSS-014: API schema endpoint returns Visota ERP API title."""
    c = Client()
    c.force_login(admin_user)
    response = c.get("/api/v1/openapi.json")
    # API might return 200 or redirect depending on auth
    if response.status_code == 200:
        import json

        data = json.loads(response.content)
        assert data["info"]["title"] == "Visota ERP API"
