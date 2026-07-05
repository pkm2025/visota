"""Tests for exchange rate method on ChartOfAccounts (VAL-M3-032 .. VAL-M3-036)."""

import pytest
from django.core.management import call_command
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.master_data.models import AccountType, ChartOfAccounts


@pytest.fixture
def company(db):
    return Company.objects.create(code="TCO", name="Test Co")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="erm_admin", password="Secret123", email="erm@test.local"
    )


@pytest.fixture
def auth_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.fixture
def asset_type(db):
    return AccountType.objects.create(
        code=1, name="Tài sản", balance_type="debit", category="asset"
    )


# ── VAL-M3-032: ChartOfAccounts fields exist ──────────────────────────


def test_chartofaccounts_has_exchange_rate_method_debit_field():
    """Model exposes exchange_rate_method_debit field."""
    field = ChartOfAccounts._meta.get_field("exchange_rate_method_debit")
    assert field is not None
    assert field.max_length == 10


def test_chartofaccounts_has_exchange_rate_method_credit_field():
    """Model exposes exchange_rate_method_credit field."""
    field = ChartOfAccounts._meta.get_field("exchange_rate_method_credit")
    assert field is not None
    assert field.max_length == 10


def test_exchange_rate_method_choices(asset_type, company):
    """Both fields offer exactly NONE / AVG / ENDING / SPOT."""
    for field_name in (
        "exchange_rate_method_debit",
        "exchange_rate_method_credit",
    ):
        choices = ChartOfAccounts._meta.get_field(field_name).choices
        codes = {code for code, _label in choices}
        assert codes == {"NONE", "AVG", "ENDING", "SPOT"}, f"{field_name} choices mismatch: {codes}"


def test_exchange_rate_method_default_none(asset_type, company):
    """Default value for both fields is NONE."""
    acc = ChartOfAccounts(
        company=company,
        account_code="111",
        account_name="Tiền mặt",
        account_level=1,
        account_type=asset_type,
    )
    assert acc.exchange_rate_method_debit == "NONE"
    assert acc.exchange_rate_method_credit == "NONE"


# ── VAL-M3-033: Choices enumerated ────────────────────────────────────


def test_exchange_rate_method_enum_values():
    """ExchangeRateMethod enum has exactly the four documented values."""
    members = ChartOfAccounts.ExchangeRateMethod.values
    assert set(members) == {"NONE", "AVG", "ENDING", "SPOT"}


# ── VAL-M3-035: load_tt133 sets defaults ──────────────────────────────


def test_load_tt133_sets_vnd_accounts_to_none(company):
    """VND accounts default to NONE on both methods."""
    call_command("load_tt133", company_code="TCO")

    vnd_acc = ChartOfAccounts.objects.get(company=company, account_code="1111")
    assert vnd_acc.currency_code == "VND"
    assert vnd_acc.exchange_rate_method_debit == "NONE"
    assert vnd_acc.exchange_rate_method_credit == "NONE"


def test_load_tt133_sets_foreign_currency_accounts_to_avg(company):
    """Foreign-currency accounts (1112, 1122) default to AVG on both methods."""
    call_command("load_tt133", company_code="TCO")

    fc_acc = ChartOfAccounts.objects.get(company=company, account_code="1112")
    assert fc_acc.currency_code != "VND"
    assert fc_acc.exchange_rate_method_debit == "AVG"
    assert fc_acc.exchange_rate_method_credit == "AVG"

    fc_acc2 = ChartOfAccounts.objects.get(company=company, account_code="1122")
    assert fc_acc2.exchange_rate_method_debit == "AVG"
    assert fc_acc2.exchange_rate_method_credit == "AVG"


def test_load_tt133_all_vnd_accounts_are_none(company):
    """Every VND-denominating account has method NONE."""
    call_command("load_tt133", company_code="TCO")
    vnd_accounts = ChartOfAccounts.objects.filter(company=company, currency_code="VND")
    assert vnd_accounts.count() >= 100
    for acc in vnd_accounts:
        assert acc.exchange_rate_method_debit == "NONE"
        assert acc.exchange_rate_method_credit == "NONE"


def test_load_tt133_all_fc_accounts_are_avg(company):
    """Every foreign-currency account has method AVG."""
    call_command("load_tt133", company_code="TCO")
    fc_accounts = ChartOfAccounts.objects.exclude(currency_code="VND").filter(company=company)
    assert fc_accounts.count() >= 2
    for acc in fc_accounts:
        assert acc.exchange_rate_method_debit == "AVG"
        assert acc.exchange_rate_method_credit == "AVG"


def test_load_tt133_idempotent_with_exchange_rate_method(company):
    """Re-running load_tt133 keeps method assignments stable."""
    call_command("load_tt133", company_code="TCO")
    call_command("load_tt133", company_code="TCO")

    fc_acc = ChartOfAccounts.objects.get(company=company, account_code="1112")
    assert fc_acc.exchange_rate_method_debit == "AVG"
    vnd_acc = ChartOfAccounts.objects.get(company=company, account_code="1111")
    assert vnd_acc.exchange_rate_method_debit == "NONE"


# ── VAL-M3-036: Chart of accounts list shows methods ──────────────────


def test_chart_of_accounts_list_shows_method_columns(auth_client):
    """The list view renders both method column headers and per-row values."""
    company = Company.objects.create(code="LC", name="List Co")
    at = AccountType.objects.create(code=1, name="TS", balance_type="debit", category="asset")
    ChartOfAccounts.objects.create(
        company=company,
        account_code="1111",
        account_name="Tiền Việt Nam",
        account_level=2,
        account_type=at,
        exchange_rate_method_debit="NONE",
        exchange_rate_method_credit="NONE",
    )
    ChartOfAccounts.objects.create(
        company=company,
        account_code="1112",
        account_name="Ngoại tệ",
        account_level=2,
        account_type=at,
        currency_code="USD",
        exchange_rate_method_debit="AVG",
        exchange_rate_method_credit="AVG",
    )

    resp = auth_client.get("/modern/chart-of-accounts/")
    assert resp.status_code == 200
    body = resp.content.decode()

    # Headers present
    assert "PP tỷ giá nợ" in body
    assert "PP tỷ giá có" in body
    # Row values present
    assert "NONE" in body
    assert "AVG" in body


# ── VAL-M3-034: Admin form exposes the fields ─────────────────────────


def test_admin_chartofaccounts_registered():
    """ChartOfAccounts is registered in admin with both fields exposed."""
    from django.contrib import admin

    from apps.master_data.admin import ChartOfAccountsAdmin

    assert ChartOfAccounts in admin.site._registry
    model_admin = admin.site._registry[ChartOfAccounts]
    assert isinstance(model_admin, ChartOfAccountsAdmin)

    # Both fields appear somewhere in the form configuration
    fieldsets_fields = []
    for _name, opts in model_admin.fieldsets:
        fieldsets_fields.extend(opts.get("fields", ()))
    assert "exchange_rate_method_debit" in fieldsets_fields
    assert "exchange_rate_method_credit" in fieldsets_fields
