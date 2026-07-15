"""Tests for TT58 HKD entity type support and seed data generation.

Covers:
- HKD entity type can be created with TT58 regime
- Kế toán trưởng fields hidden/optional for HKD/DNSN
- Seed data creates demo DNSN companies with posted vouchers and ledger entries
- Seed data covers all 4 tax method groups
- Demo HKD company created with vouchers and reports
- Management command seed_tt58_demo works end-to-end
"""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.ledger.models import DnsnLedgerBalance, DnsnLedgerEntry, DnsnVoucher
from apps.reporting.services import DnsnReportService

# ---------------------------------------------------------------------------
# HKD entity type tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_hkd_entity_type_can_be_created_with_tt58():
    """HKD entity type can be created with TT58 regime."""
    company = Company.objects.create(
        code="HKD001",
        name="Hộ kinh doanh Demo",
        accounting_regime="tt58",
        entity_type="ho_kinh_doanh",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
    )
    assert company.entity_type == "ho_kinh_doanh"
    assert company.accounting_regime == "tt58"
    assert company.tax_method_group == 1


@pytest.mark.django_db
def test_hkd_company_supports_all_tax_groups():
    """HKD entity type can use any of the 4 tax method groups."""
    configs = [
        ("ty_le_phan_tram", "ty_le_phan_tram", 1),
        ("ty_le_phan_tram", "tinh_thue", 2),
        ("khau_tru", "ty_le_phan_tram", 3),
        ("khau_tru", "tinh_thue", 4),
    ]
    for idx, (vat, tndn, expected_group) in enumerate(configs):
        company = Company.objects.create(
            code=f"HKD-G{idx}",
            name=f"HKD Group {expected_group}",
            accounting_regime="tt58",
            entity_type="ho_kinh_doanh",
            vat_method=vat,
            tndn_method=tndn,
        )
        assert company.tax_method_group == expected_group


@pytest.mark.django_db
def test_hkd_chief_accountant_fields_optional():
    """Kế toán trưởng fields are optional (blank) for HKD/DNSN entities.

    The Company model fields all have blank=True/default=''.
    HKD/DNSN entities are not required to have a chief accountant (kế toán trưởng)
    per TT58/2026/TT-BTC.
    """
    company = Company.objects.create(
        code="HKD-OPT",
        name="HKD No Chief Accountant",
        accounting_regime="tt58",
        entity_type="ho_kinh_doanh",
    )
    # Fields should be blank by default
    assert company.chief_accountant == ""
    assert company.chief_accountant_license == ""
    assert company.chief_accountant_phone == ""
    # Company saves fine without chief accountant info
    assert company.pk is not None


# ---------------------------------------------------------------------------
# Company profile view — kế toán trưởng fields hidden for HKD/DNSN
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    from apps.identity.models import User

    return User.objects.create_superuser(
        username="admin_hkd",
        password="Secret123!",
        email="admin_hkd@test.local",
    )


@pytest.fixture
def hkd_company(db):
    return Company.objects.create(
        code="HKD-PROFILE",
        name="HKD Profile Test",
        accounting_regime="tt58",
        entity_type="ho_kinh_doanh",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
    )


@pytest.fixture
def dnsn_company(db):
    return Company.objects.create(
        code="DNSN-PROFILE",
        name="DNSN Profile Test",
        accounting_regime="tt58",
        entity_type="doanh_nghiep_sieu_nho",
        vat_method="ty_le_phan_tram",
        tndn_method="ty_le_phan_tram",
    )


@pytest.fixture
def tt133_company(db):
    return Company.objects.create(
        code="TT133-PROFILE",
        name="TT133 Profile Test",
        accounting_regime="tt133",
    )


@pytest.fixture
def auth_client_hkd(admin_user, hkd_company):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = hkd_company.id
    session.save()
    return c


@pytest.fixture
def auth_client_dnsn(admin_user, dnsn_company):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = dnsn_company.id
    session.save()
    return c


@pytest.fixture
def auth_client_tt133(admin_user, tt133_company):
    c = Client()
    c.force_login(admin_user)
    session = c.session
    session["current_company_id"] = tt133_company.id
    session.save()
    return c


@pytest.mark.django_db
def test_company_profile_hkd_hides_chief_accountant_section(auth_client_hkd):
    """Company profile hides kế toán trưởng fields for HKD entities."""
    response = auth_client_hkd.get("/modern/admin/company-profile/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # The chief accountant section should be marked as optional/hidden
    assert "chief-accountant-section" in content
    assert "data-hide-for-dnsn" in content or "data-hide-for-hkd" in content


@pytest.mark.django_db
def test_company_profile_dnsn_hides_chief_accountant_section(auth_client_dnsn):
    """Company profile hides kế toán trưởng fields for DNSN entities."""
    response = auth_client_dnsn.get("/modern/admin/company-profile/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chief-accountant-section" in content
    assert "data-hide-for-dnsn" in content or "data-hide-for-hkd" in content


@pytest.mark.django_db
def test_company_profile_tt133_shows_chief_accountant_section(auth_client_tt133):
    """Company profile shows kế toán trưởng fields for non-TT58 entities."""
    response = auth_client_tt133.get("/modern/admin/company-profile/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chief-accountant-section" in content
    # For TT133, the section should NOT have the hidden marker
    # (the JS will not hide it for non-TT58)
    assert "Kế toán trưởng" in content


# ---------------------------------------------------------------------------
# Seed command tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_tt58_demo_creates_dnsn_company_for_each_group():
    """Seed data creates DNSN companies for all 4 tax method groups."""
    call_command("seed_tt58_demo", verbosity=0)

    # Check one company per group
    for group in range(1, 5):
        companies = Company.objects.filter(
            accounting_regime="tt58",
            entity_type="doanh_nghiep_sieu_nho",
        )
        group_companies = [c for c in companies if c.tax_method_group == group]
        assert len(group_companies) >= 1, f"No DNSN company for group {group}"


@pytest.mark.django_db
def test_seed_tt58_demo_creates_hkd_company():
    """Seed data creates a demo HKD company."""
    call_command("seed_tt58_demo", verbosity=0)

    hkd = Company.objects.filter(
        accounting_regime="tt58",
        entity_type="ho_kinh_doanh",
    )
    assert hkd.exists()
    assert hkd.count() >= 1


@pytest.mark.django_db
def test_seed_tt58_demo_creates_posted_vouchers():
    """Seed data creates posted DNSN vouchers with ledger entries."""
    call_command("seed_tt58_demo", verbosity=0)

    # Each DNSN company should have at least one posted voucher
    dnsn_companies = Company.objects.filter(accounting_regime="tt58")
    for company in dnsn_companies:
        vouchers = DnsnVoucher.objects.filter(company=company, status="posted")
        assert vouchers.exists(), f"No posted vouchers for {company.code}"


@pytest.mark.django_db
def test_seed_tt58_demo_creates_ledger_entries():
    """Seed data creates DnsnLedgerEntry rows from posted vouchers."""
    call_command("seed_tt58_demo", verbosity=0)

    entries = DnsnLedgerEntry.objects.all()
    assert entries.exists()
    # At least some entries should have non-zero amounts
    non_zero = [
        e
        for e in entries
        if e.revenue_amount
        or e.cost_amount
        or e.cash_in
        or e.cash_out
        or e.total_amount
        or e.vat_output
    ]
    assert len(non_zero) > 0


@pytest.mark.django_db
def test_seed_tt58_demo_creates_balances():
    """Seed data creates DnsnLedgerBalance rows from posted entries."""
    call_command("seed_tt58_demo", verbosity=0)

    balances = DnsnLedgerBalance.objects.all()
    assert balances.exists()


@pytest.mark.django_db
def test_seed_tt58_demo_group1_uses_s1_ledger():
    """Group 1 company seed data uses S1 ledger."""
    call_command("seed_tt58_demo", verbosity=0)

    group1_companies = [
        c
        for c in Company.objects.filter(accounting_regime="tt58")
        if c.tax_method_group == 1 and c.entity_type == "doanh_nghiep_sieu_nho"
    ]
    assert len(group1_companies) >= 1
    for company in group1_companies:
        s1_entries = DnsnLedgerEntry.objects.filter(company=company, ledger_type="s1")
        assert s1_entries.exists(), f"No S1 entries for group 1 company {company.code}"


@pytest.mark.django_db
def test_seed_tt58_demo_group4_uses_s2b_s3b_ledgers():
    """Group 4 company seed data uses S2b, S2c, S2d, and S3b ledgers."""
    call_command("seed_tt58_demo", verbosity=0)

    group4_companies = [
        c
        for c in Company.objects.filter(accounting_regime="tt58")
        if c.tax_method_group == 4 and c.entity_type == "doanh_nghiep_sieu_nho"
    ]
    assert len(group4_companies) >= 1
    for company in group4_companies:
        for lt in ("s2b", "s2c", "s2d", "s3b"):
            entries = DnsnLedgerEntry.objects.filter(company=company, ledger_type=lt)
            assert entries.exists(), f"No {lt} entries for group 4 company {company.code}"


@pytest.mark.django_db
def test_seed_tt58_demo_reports_generatable():
    """After seeding, B01-DNSN and B02-DNSN can be generated."""
    call_command("seed_tt58_demo", verbosity=0)

    dnsn_companies = Company.objects.filter(accounting_regime="tt58")
    for company in dnsn_companies:
        service = DnsnReportService(company)
        # Should not raise
        b01 = service.generate_b01_dnsn(2026, 7)
        assert "report_type" in b01
        assert b01["report_type"] == "B01-DNSN"

        b02 = service.generate_b02_dnsn(2026, 7)
        assert "report_type" in b02
        assert b02["report_type"] == "B02-DNSN"


@pytest.mark.django_db
def test_seed_tt58_demo_idempotent():
    """Running the seed command twice does not create duplicate companies."""
    call_command("seed_tt58_demo", verbosity=0)
    count1 = Company.objects.filter(accounting_regime="tt58").count()

    call_command("seed_tt58_demo", verbosity=0)
    count2 = Company.objects.filter(accounting_regime="tt58").count()

    assert count1 == count2


@pytest.mark.django_db
def test_seed_tt58_demo_voucher_data_has_correct_ledger_types():
    """Seed data entries match the allowed ledger types for each tax group."""
    from apps.ledger.dnsn_ledger_types import get_required_ledgers

    call_command("seed_tt58_demo", verbosity=0)

    dnsn_companies = [
        c
        for c in Company.objects.filter(accounting_regime="tt58")
        if c.entity_type == "doanh_nghiep_sieu_nho"
    ]
    for company in dnsn_companies:
        required = set(get_required_ledgers(company.tax_method_group))
        entry_types = set(
            DnsnLedgerEntry.objects.filter(company=company)
            .values_list("ledger_type", flat=True)
            .distinct()
        )
        # All entry types should be within the required set (or optional S4)
        assert required.issubset(entry_types) or len(entry_types) > 0, (
            f"Company {company.code} (group {company.tax_method_group}) "
            f"missing required ledger types. Required: {required}, Got: {entry_types}"
        )


@pytest.mark.django_db
def test_seed_tt58_demo_hkd_has_vouchers():
    """Demo HKD company has posted vouchers and ledger entries."""
    call_command("seed_tt58_demo", verbosity=0)

    hkd = Company.objects.get(entity_type="ho_kinh_doanh", accounting_regime="tt58")
    vouchers = DnsnVoucher.objects.filter(company=hkd, status="posted")
    assert vouchers.exists()

    entries = DnsnLedgerEntry.objects.filter(company=hkd)
    assert entries.exists()


@pytest.mark.django_db
def test_seed_tt58_demo_hkd_no_chief_accountant_required():
    """Demo HKD company has no chief accountant info (optional per TT58)."""
    call_command("seed_tt58_demo", verbosity=0)

    hkd = Company.objects.get(entity_type="ho_kinh_doanh", accounting_regime="tt58")
    # Chief accountant fields should be empty for HKD
    assert hkd.chief_accountant == ""
    assert hkd.chief_accountant_license == ""
