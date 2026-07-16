"""Tests for m3-change-account-code feature.

Validates VAL-M3-023 through VAL-M3-031 and VAL-M3-037.

ChartOfAccountsChangeCodeView at /modern/chart-of-accounts/<pk>/change-code/:
* GET shows a form with new_code input and the current code displayed.
* POST updates account_code and cascades VoucherLine.account_code +
  AccountPeriodBalance.account_code in a single transaction.
* Validation: new_code required, must be unique within the company.
* Audit trail: created_at/updated_at preserved appropriately.
* Reports (trial balance) reflect the new code without manual cache flush.
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.ledger.models import AccountingVoucher, AccountPeriodBalance, VoucherLine
from apps.ledger.services import VoucherPostingService
from apps.master_data.models import AccountType, ChartOfAccounts


def _account_code_rows(html: str) -> list[str]:
    """Extract account codes that appear as their own <td> cell.

    The trial-balance / chart-of-accounts templates render the account_code
    inside a ``<td ...><code?>{{ account_code }}</code?></td>`` cell. We pull
    those out so toast messages or labels containing the same digits do not
    produce false-positive substring matches.
    """
    # Match <td ...>...CODE...</td> cells whose visible text is a bare account
    # code (digits/letters). Tolerate an inner <code> wrapper and whitespace.
    rows: list[str] = []
    for cell in re.findall(r"<td[^>]*>(.*?)</td>", html, flags=re.DOTALL):
        # Strip inner tags and surrounding whitespace
        text = re.sub(r"<[^>]+>", "", cell).strip()
        if text and re.fullmatch(r"[0-9A-Za-z]+", text):
            rows.append(text)
    return rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def asset_type(db):
    return AccountType.objects.create(
        code=1, name="Tài sản", balance_type="debit", category="asset"
    )


@pytest.fixture
def company(db):
    return Company.objects.create(
        code="CACO",
        name="Change Account Co",
        tax_code="0109998877",
        accounting_regime="tt133",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="cac_admin", password="Secret123", email="cac@test.local"
    )


@pytest.fixture
def auth_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.fixture
def account_1111(company, asset_type):
    return ChartOfAccounts.objects.create(
        company=company,
        account_code="1111",
        account_name="Tiền Việt Nam",
        account_level=2,
        account_type=asset_type,
        is_posting_account=True,
    )


@pytest.fixture
def account_2222(company, asset_type):
    return ChartOfAccounts.objects.create(
        company=company,
        account_code="2222",
        account_name="Tài khoản khác",
        account_level=2,
        account_type=asset_type,
        is_posting_account=True,
    )


def _make_posted_voucher(company, account_code, amount=Decimal("1000000"), suffix="1"):
    """Create and post a simple balanced voucher touching ``account_code``."""
    v = AccountingVoucher.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        voucher_no=f"VC-{account_code}-{suffix}",
        voucher_type="journal",
        voucher_date=date(2026, 6, 15),
        status=AccountingVoucher.Status.DRAFT,
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=1,
        account_code=account_code,
        debit_vnd=amount,
        credit_vnd=Decimal("0"),
    )
    VoucherLine.objects.create(
        voucher=v,
        line_no=2,
        account_code="331",
        debit_vnd=Decimal("0"),
        credit_vnd=amount,
    )
    VoucherPostingService().post(v)
    return v


# ---------------------------------------------------------------------------
# VAL-M3-023 — Change-code form GET
# ---------------------------------------------------------------------------


def test_get_change_code_form_returns_200(auth_client, account_1111):
    """GET /modern/chart-of-accounts/<pk>/change-code/ returns 200 with form."""
    resp = auth_client.get(f"/modern/chart-of-accounts/{account_1111.pk}/change-code/")
    assert resp.status_code == 200
    body = resp.content.decode()
    # The form contains a new_code input
    assert "new_code" in body
    # The current account code is displayed
    assert "1111" in body


def test_get_change_code_form_shows_current_code(auth_client, account_1111):
    """The current account code is shown as a label/heading on the form."""
    resp = auth_client.get(f"/modern/chart-of-accounts/{account_1111.pk}/change-code/")
    assert resp.status_code == 200
    assert account_1111.account_code in resp.content.decode()


def test_change_code_requires_login(account_1111):
    """Anonymous GET redirects to login."""
    c = Client()
    resp = c.get(f"/modern/chart-of-accounts/{account_1111.pk}/change-code/")
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert "/auth/login/" in resp["Location"]


# ---------------------------------------------------------------------------
# VAL-M3-024 — Change-code POST updates ChartOfAccounts
# ---------------------------------------------------------------------------


def test_post_change_code_updates_account(auth_client, account_1111):
    """POST with new_code updates ChartOfAccounts.account_code."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302
    account_1111.refresh_from_db()
    assert account_1111.account_code == "7111"


def test_post_change_code_redirects_to_list(auth_client, account_1111):
    """POST returns a redirect (to list or back to detail)."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302


def test_post_change_code_invalid_pk_404(auth_client, company):
    """A non-existent pk returns 404."""
    # Set session so the view can resolve the current company.
    session = auth_client.session
    session["current_company_id"] = company.id
    session.save()
    resp = auth_client.post(
        "/modern/chart-of-accounts/99999999/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# VAL-M3-025 — Cascade VoucherLine.account_code
# ---------------------------------------------------------------------------


def test_cascade_voucher_line_account_code(auth_client, company, account_1111):
    """VoucherLine rows with the old account_code are updated to new code."""
    _make_posted_voucher(company, "1111", Decimal("1000000"), suffix="A")
    _make_posted_voucher(company, "1111", Decimal("500000"), suffix="B")
    # Pre-state
    assert VoucherLine.objects.filter(account_code="1111").count() >= 2

    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302

    assert VoucherLine.objects.filter(account_code="1111").count() == 0
    assert VoucherLine.objects.filter(account_code="7111").count() >= 2


# ---------------------------------------------------------------------------
# VAL-M3-026 — Cascade AccountPeriodBalance.account_code
# ---------------------------------------------------------------------------


def test_cascade_account_period_balance(auth_client, company, account_1111):
    """AccountPeriodBalance rows updated to new code within the transaction."""
    # Create a balance row directly
    AccountPeriodBalance.objects.create(
        company=company,
        fiscal_year=2026,
        period=6,
        account_code="1111",
        period_debit=Decimal("1000000"),
        closing_debit=Decimal("1000000"),
    )

    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302

    assert AccountPeriodBalance.objects.filter(account_code="1111").count() == 0
    assert AccountPeriodBalance.objects.filter(account_code="7111").count() == 1


# ---------------------------------------------------------------------------
# VAL-M3-027 — Trial balance reflects new code
# ---------------------------------------------------------------------------


def test_trial_balance_reflects_new_code(auth_client, company, account_1111):
    """Trial balance view shows new code (not old) after the change."""
    _make_posted_voucher(company, "1111", Decimal("1000000"))

    # Perform change-code
    auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )

    resp = auth_client.get("/modern/reports/trial-balance/?fiscal_year=2026&period=6")
    assert resp.status_code == 200
    body = resp.content.decode()
    rows = _account_code_rows(body)
    assert "7111" in rows
    assert "1111" not in rows


# ---------------------------------------------------------------------------
# VAL-M3-028 — Old code removed from chart of accounts list
# ---------------------------------------------------------------------------


def test_old_code_removed_from_chart_of_accounts_list(auth_client, account_1111):
    """Old code no longer appears in chart-of-accounts list."""
    auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    resp = auth_client.get("/modern/chart-of-accounts/")
    assert resp.status_code == 200
    body = resp.content.decode()
    rows = _account_code_rows(body)
    assert "7111" in rows
    # Old code 1111 not present in any data row
    assert "1111" not in rows


# ---------------------------------------------------------------------------
# VAL-M3-029 — Validation: cannot change to existing code
# ---------------------------------------------------------------------------


def test_validation_cannot_change_to_existing_code(auth_client, account_1111, account_2222):
    """POST new_code=<existing-other-code> returns form with error, no DB update."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "2222"},
    )
    assert resp.status_code == 200  # form re-rendered with error
    body = resp.content.decode()
    # Validation message present (Vietnamese or English)
    assert "đã tồn tại" in body.lower() or "already exists" in body.lower()
    # Account unchanged
    account_1111.refresh_from_db()
    assert account_1111.account_code == "1111"


# ---------------------------------------------------------------------------
# VAL-M3-030 — Validation: new_code required and non-empty
# ---------------------------------------------------------------------------


def test_validation_new_code_required(auth_client, account_1111):
    """POST with empty new_code returns form error, no DB change."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": ""},
    )
    assert resp.status_code == 200  # form re-rendered
    account_1111.refresh_from_db()
    assert account_1111.account_code == "1111"


def test_validation_new_code_whitespace_only(auth_client, account_1111):
    """Whitespace-only new_code is treated as empty."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "   "},
    )
    assert resp.status_code == 200
    account_1111.refresh_from_db()
    assert account_1111.account_code == "1111"


# ---------------------------------------------------------------------------
# VAL-M3-031 — Audit trail preserved
# ---------------------------------------------------------------------------


def test_audit_trail_preserved(auth_client, account_1111):
    """created_at unchanged, updated_at >= created_at after the change."""
    original_created_at = account_1111.created_at
    original_updated_at = account_1111.updated_at

    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302
    account_1111.refresh_from_db()
    assert account_1111.created_at == original_created_at
    assert account_1111.updated_at >= original_updated_at


# ---------------------------------------------------------------------------
# VAL-M3-037 — Reports reflect changed code without manual refresh
# ---------------------------------------------------------------------------


def test_reports_reflect_new_code_immediately(auth_client, company, account_1111):
    """After change-code, multiple report views show the new code on next request."""
    # Seed a posted voucher under 1111 (cascades to AccountPeriodBalance)
    _make_posted_voucher(company, "1111", Decimal("1000000"))

    auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "7111"},
    )

    # Trial balance must show 7111, not 1111
    tb = auth_client.get("/modern/reports/trial-balance/?fiscal_year=2026&period=6")
    assert tb.status_code == 200
    rows = _account_code_rows(tb.content.decode())
    assert "7111" in rows
    assert "1111" not in rows


def test_change_code_same_value_noop(auth_client, account_1111):
    """Changing to the same code value is a no-op (no error, same code)."""
    resp = auth_client.post(
        f"/modern/chart-of-accounts/{account_1111.pk}/change-code/",
        data={"new_code": "1111"},
    )
    # Either redirect (success) or 200 (form error); account unchanged either way
    assert resp.status_code in (200, 302)
    account_1111.refresh_from_db()
    assert account_1111.account_code == "1111"


# ---------------------------------------------------------------------------
# Cross-company isolation
# ---------------------------------------------------------------------------


def test_change_code_does_not_affect_other_company(auth_client, company, asset_type):
    """Account code in another company with the same value is untouched."""
    other_company = Company.objects.create(
        code="OCO2", name="Other Co 2", accounting_regime="tt133"
    )
    other_acc = ChartOfAccounts.objects.create(
        company=other_company,
        account_code="1111",
        account_name="Other Co 1111",
        account_level=2,
        account_type=asset_type,
        is_posting_account=True,
    )
    my_acc = ChartOfAccounts.objects.create(
        company=company,
        account_code="1111",
        account_name="My Co 1111",
        account_level=2,
        account_type=asset_type,
        is_posting_account=True,
    )

    resp = auth_client.post(
        f"/modern/chart-of-accounts/{my_acc.pk}/change-code/",
        data={"new_code": "7111"},
    )
    assert resp.status_code == 302

    my_acc.refresh_from_db()
    other_acc.refresh_from_db()
    assert my_acc.account_code == "7111"
    assert other_acc.account_code == "1111"
