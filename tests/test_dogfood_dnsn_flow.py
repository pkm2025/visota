"""Dogfood integration test: TT58 DNSN flow for Company DF-HN (Group 2).

Runs `seed_dogfood` first (idempotent), then exercises the complete DNSN
workflow end-to-end through the HTTP layer as a real dogfood user:

1. Login as ``hn_ketoan`` (Company DF-HN, TT58 Group 2 accountant)
2. View DNSN voucher list
3. Create a phiếu thu DNSN voucher via POST
4. View DNSN ledgers list (S2a/b/c/d available for Group 2)
5. View a specific ledger detail (S2a-DNSN)
6. View B01-DNSN balance sheet report
7. View B02-DNSN profit & loss report

Multi-tenant isolation:
8. SG user cannot access DF-HN DNSN voucher by ID → 404
9. HN user cannot access DF-SG regular voucher by ID → 404
10. DF-HN voucher list contains only DF-HN vouchers

Company DF-AB (HKD, Group 1):
11. Login as ``ab_admin``, set company to DF-AB
12. DNSN ledgers list shows only S1-DNSN (no S2/S3)
"""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.ledger.dnsn_ledger_types import get_company_available_ledgers
from apps.ledger.models import AccountingVoucher, DnsnVoucher

User = get_user_model()

PASSWORD = "dogfood123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_dogfood():
    """Run seed_dogfood management command (idempotent)."""
    out = StringIO()
    call_command("seed_dogfood", stdout=out)
    return out.getvalue()


def _client_with_company(username: str, company: Company) -> Client:
    """Create an authenticated client (via force_login) with company in session."""
    c = Client()
    user = User.objects.get(username=username)
    c.force_login(user)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def data(db):
    """Run the dogfood seed and return the three company instances.

    ``seed_dogfood`` is idempotent (uses update_or_create throughout) so
    running it once per test is safe and keeps each test independent.
    """
    _seed_dogfood()
    return {
        "hn": Company.objects.get(code="DF-HN"),
        "sg": Company.objects.get(code="DF-SG"),
        "ab": Company.objects.get(code="DF-AB"),
    }


# ---------------------------------------------------------------------------
# DF-HN DNSN workflow (Group 2)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_hn_dnsn_voucher_list_200(data):
    """Step 2: GET /modern/dnsn-vouchers/ returns 200 for hn_ketoan."""
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-vouchers/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "Chứng từ DNSN" in body or "DNSN" in body


@pytest.mark.django_db
def test_hn_create_dnsn_phieu_thu(data):
    """Step 3: POST to create a phiếu thu DNSN voucher succeeds.

    The create view redirects (302) to the new voucher's detail page.
    """
    c = _client_with_company("hn_ketoan", data["hn"])
    before = DnsnVoucher.objects.filter(company=data["hn"]).count()
    resp = c.post(
        "/modern/dnsn-vouchers/new/",
        data={
            "voucher_type": "phieu_thu",
            "voucher_date": "2026-07-25",
            "voucher_no": "DF-TEST-PT001",
            "description": "Thu tiền dịch vụ test (dogfood)",
            "partner_name": "Khách hàng Test Dogfood",
            "total_amount": "7500000",
        },
    )
    assert resp.status_code == 302, (
        f"Expected 302 redirect after create, got {resp.status_code}: {resp.content[:500]!r}"
    )
    after = DnsnVoucher.objects.filter(company=data["hn"]).count()
    assert after == before + 1
    new_voucher = DnsnVoucher.objects.filter(company=data["hn"], voucher_no="DF-TEST-PT001").first()
    assert new_voucher is not None
    assert new_voucher.voucher_type == DnsnVoucher.VoucherType.PHIEU_THU
    assert new_voucher.total_amount == 7500000


@pytest.mark.django_db
def test_hn_dnsn_ledgers_list_200(data):
    """Step 4: GET /modern/dnsn-ledgers/ returns 200 and shows S2a/b/c/d for group 2."""
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-ledgers/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    for label_fragment in ("S2a", "S2b", "S2c", "S2d"):
        assert label_fragment in body, f"Ledger label '{label_fragment}' missing from ledgers list"


@pytest.mark.django_db
def test_hn_dnsn_ledger_detail_s2a_200(data):
    """Step 5: GET /modern/dnsn-ledgers/s2a/ returns 200.

    The URL is ``dnsn-ledgers/<str:ledger_type>/`` and the view checks
    availability against the company's tax_method_group.
    """
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-ledgers/s2a/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "S2a" in body


@pytest.mark.django_db
def test_hn_b01_dnsn_report_200(data):
    """Step 6: GET /modern/dnsn-reports/b01-dnsn/ returns 200."""
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-reports/b01-dnsn/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "B01-DNSN" in body


@pytest.mark.django_db
def test_hn_b02_dnsn_report_200(data):
    """Step 7: GET /modern/dnsn-reports/b02-dnsn/ returns 200."""
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-reports/b02-dnsn/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "B02-DNSN" in body


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sg_user_cannot_access_hn_dnsn_voucher(data):
    """Step 8: SG user accessing DF-HN DNSN voucher by ID → 404.

    The detail view scopes by ``company=request.current_company`` (DF-SG),
    so a DF-HN voucher PK yields a 404.
    """
    hn_voucher = DnsnVoucher.objects.filter(company=data["hn"]).first()
    assert hn_voucher is not None, "Seed should have created DF-HN DNSN vouchers"
    c = _client_with_company("sg_ketoan", data["sg"])
    resp = c.get(f"/modern/dnsn-vouchers/{hn_voucher.id}/")
    assert resp.status_code == 404, (
        f"SG user should get 404 on DF-HN voucher, got {resp.status_code}"
    )


@pytest.mark.django_db
def test_hn_user_cannot_access_sg_regular_voucher(data):
    """Step 9: HN user accessing DF-SG regular (TT133) voucher by ID is blocked.

    DF-HN is a TT58 company; the voucher detail view scopes by
    ``company=request.current_company``. DF-SG's AccountingVoucher PK
    must not be shown to the DF-HN user.

    Isolation may manifest as either:
    - 404 (company-scoped get_object_or_404), or
    - 302 redirect to /no-access/ (ModulePermissionMiddleware denying
      cross-module access for a user whose role lacks ledger.access
      in the current company context).

    Both outcomes prove the DF-SG voucher data is not leaked.
    """
    sg_voucher = AccountingVoucher.objects.filter(company=data["sg"]).first()
    assert sg_voucher is not None, "Seed should have created DF-SG TT133 vouchers"
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get(f"/modern/vouchers/{sg_voucher.id}/")
    assert resp.status_code in (302, 404), (
        f"HN user should be blocked (302/404) from DF-SG voucher, got {resp.status_code}"
    )
    if resp.status_code == 302:
        assert "/no-access/" in resp.url, f"302 redirect should go to /no-access/, got {resp.url}"


@pytest.mark.django_db
def test_hn_voucher_list_only_hn_data(data):
    """Step 10: DF-HN DNSN voucher list contains only DF-HN vouchers.

    The list view's queryset is company-scoped, so the rendered page's
    voucher numbers must all belong to DF-HN. We assert that at least one
    DF-HN DNSN voucher number appears and no DF-SG TT133 voucher numbers
    leak into the response.
    """
    c = _client_with_company("hn_ketoan", data["hn"])
    resp = c.get("/modern/dnsn-vouchers/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")

    hn_voucher_nos = list(
        DnsnVoucher.objects.filter(company=data["hn"]).values_list("voucher_no", flat=True)
    )
    assert any(no in body for no in hn_voucher_nos), (
        f"None of DF-HN's voucher numbers {hn_voucher_nos} found in voucher list body"
    )

    sg_voucher_nos = list(
        AccountingVoucher.objects.filter(company=data["sg"]).values_list("voucher_no", flat=True)
    )
    leaked = [no for no in sg_voucher_nos if no in body]
    assert not leaked, f"DF-SG voucher numbers leaked into DF-HN view: {leaked}"


# ---------------------------------------------------------------------------
# DF-AB (HKD, Group 1) — only S1-DNSN available
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ab_group1_only_s1_ledger_available(data):
    """Step 11+12: DF-AB (Group 1) only exposes S1-DNSN, not S2/S3.

    Validates at the model/service layer (get_company_available_ledgers)
    and via the HTTP ledgers list view.
    """
    ab = data["ab"]
    available = get_company_available_ledgers(ab)
    assert "s1" in available, "S1-DNSN must be available for Group 1"
    for forbidden in ("s2a", "s2b", "s2c", "s2d", "s3a", "s3b"):
        assert forbidden not in available, (
            f"Ledger '{forbidden}' must NOT be available for Group 1 HKD, got {available}"
        )

    c = _client_with_company("ab_admin", ab)
    resp = c.get("/modern/dnsn-ledgers/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "S1" in body
    for forbidden in ("S2a", "S2b", "S2c", "S2d", "S3a", "S3b"):
        assert forbidden not in body, (
            f"Ledger label '{forbidden}' must NOT appear for Group 1 HKD ledgers view"
        )


@pytest.mark.django_db
def test_ab_group1_ledger_detail_s2a_not_available(data):
    """Extra: DF-AB user requesting S2a detail is rejected (redirect).

    The view redirects to the ledgers list with an error message when the
    requested ledger_type is not available for the company's group.
    """
    c = _client_with_company("ab_admin", data["ab"])
    resp = c.get("/modern/dnsn-ledgers/s2a/")
    assert resp.status_code in (302, 404), (
        f"DF-AB (group 1) accessing S2a should redirect/404, got {resp.status_code}"
    )
