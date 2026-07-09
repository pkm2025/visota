"""Tests for the UserInteractionLog model.

Covers model creation, field defaults, interaction type choices, metadata
JSON storage, indexes, multi-tenant isolation, and cascade delete behaviour.
"""

import pytest
from django.db import connection

from apps.core.managers import CompanyOwnedModel
from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import UserInteractionLog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="ILOG_TEST", name="InteractionLog Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="ilog_user", password="Test1234", email="ilog@t.co")


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="ilog_other", password="Test1234", email="ilog_other@t.co"
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="ILOG_OTHER", name="InteractionLog Other Co")


# ---------------------------------------------------------------------------
# Model inheritance
# ---------------------------------------------------------------------------


def test_user_interaction_log_extends_company_owned_model():
    """UserInteractionLog must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(UserInteractionLog, CompanyOwnedModel)


# ---------------------------------------------------------------------------
# Model creation and field defaults
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_creation_minimal(company, user):
    """UserInteractionLog can be created with only the required fields."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.PAGE_VIEW,
        module="pkm",
    )
    assert log.pk is not None
    assert log.user == user
    assert log.company == company
    assert log.interaction_type == "page_view"
    assert log.module == "pkm"
    assert log.entity_type == ""  # blank default
    assert log.entity_id == ""  # blank default
    assert log.metadata == {}  # default dict
    assert log.created_at is not None


@pytest.mark.django_db
def test_interaction_log_creation_with_all_fields(company, user):
    """UserInteractionLog can be created with all fields populated."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.NOTE_CREATE,
        module="pkm",
        entity_type="note",
        entity_id="42",
        metadata={"title": "My Note", "tags": ["tax", "vat"]},
    )
    assert log.pk is not None
    assert log.interaction_type == "note_create"
    assert log.module == "pkm"
    assert log.entity_type == "note"
    assert log.entity_id == "42"
    assert log.metadata == {"title": "My Note", "tags": ["tax", "vat"]}


@pytest.mark.django_db
def test_interaction_log_metadata_defaults_to_empty_dict(company, user):
    """metadata defaults to an empty dict, not None or list."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.PAGE_VIEW,
        module="ledger",
    )
    assert log.metadata == {}
    assert isinstance(log.metadata, dict)


@pytest.mark.django_db
def test_interaction_log_entity_fields_blank_by_default(company, user):
    """entity_type and entity_id are blank strings by default."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.PAGE_VIEW,
        module="reporting",
    )
    assert log.entity_type == ""
    assert log.entity_id == ""


# ---------------------------------------------------------------------------
# Interaction type choices
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_type_all_choices(company, user):
    """All five interaction types can be stored."""
    choices = [
        UserInteractionLog.InteractionType.PAGE_VIEW,
        UserInteractionLog.InteractionType.SEARCH,
        UserInteractionLog.InteractionType.NOTE_CREATE,
        UserInteractionLog.InteractionType.DOCUMENT_CREATE,
        UserInteractionLog.InteractionType.VOUCHER_CREATE,
    ]
    for itype in choices:
        log = UserInteractionLog.objects.create(
            user=user,
            company=company,
            interaction_type=itype,
            module="pkm",
        )
        assert log.interaction_type == itype


@pytest.mark.django_db
def test_interaction_type_values():
    """Interaction type choice values match the expected strings."""
    assert UserInteractionLog.InteractionType.PAGE_VIEW == "page_view"
    assert UserInteractionLog.InteractionType.SEARCH == "search"
    assert UserInteractionLog.InteractionType.NOTE_CREATE == "note_create"
    assert UserInteractionLog.InteractionType.DOCUMENT_CREATE == "document_create"
    assert UserInteractionLog.InteractionType.VOUCHER_CREATE == "voucher_create"


@pytest.mark.django_db
def test_interaction_type_choices_count():
    """There are exactly 5 interaction type choices."""
    assert len(UserInteractionLog.InteractionType.choices) == 5


# ---------------------------------------------------------------------------
# Metadata JSON storage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_metadata_stores_complex_json(company, user):
    """metadata can store nested JSON structures."""
    complex_data = {
        "query": "how to calculate VAT",
        "filters": {"module": "ledger", "date_from": "2026-01-01"},
        "results_count": 5,
    }
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.SEARCH,
        module="pkm",
        metadata=complex_data,
    )
    log.refresh_from_db()
    assert log.metadata == complex_data
    assert log.metadata["query"] == "how to calculate VAT"
    assert log.metadata["filters"]["module"] == "ledger"


@pytest.mark.django_db
def test_interaction_log_search_metadata(company, user):
    """Search interactions store query in metadata."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.SEARCH,
        module="pkm",
        metadata={"query": "VAT calculation guide"},
    )
    assert log.metadata["query"] == "VAT calculation guide"


# ---------------------------------------------------------------------------
# Module field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_module_various_values(company, user):
    """module field can store various Visota module names."""
    for module in ["pkm", "ledger", "sales", "purchasing", "inventory", "hr", "reporting"]:
        UserInteractionLog.objects.create(
            user=user,
            company=company,
            interaction_type=UserInteractionLog.InteractionType.PAGE_VIEW,
            module=module,
        )
    logs = UserInteractionLog.objects.filter(user=user, company=company)
    modules = set(logs.values_list("module", flat=True))
    assert modules == {"pkm", "ledger", "sales", "purchasing", "inventory", "hr", "reporting"}


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_indexes_exist():
    """Indexes on (user, company) and (user, company, created_at) exist in DB."""
    index_names = set()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT index_name FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'pkm_user_interaction_log'"
        )
        for row in cursor.fetchall():
            index_names.add(row[0])

    # Django generates index names with a hash suffix; match by prefix.
    matching = [n for n in index_names if n.startswith("pkm_user_in_user_id_")]
    assert len(matching) >= 2, (
        f"Expected at least 2 indexes on pkm_user_interaction_log, found: {index_names}"
    )


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_default_ordering(company, user):
    """Default ordering is by created_at descending."""
    import time

    log1 = UserInteractionLog.objects.create(
        user=user, company=company, interaction_type="page_view", module="pkm"
    )
    time.sleep(0.01)
    log2 = UserInteractionLog.objects.create(
        user=user, company=company, interaction_type="page_view", module="pkm"
    )
    logs = list(UserInteractionLog.objects.filter(user=user, company=company))
    assert logs[0].pk == log2.pk
    assert logs[1].pk == log1.pk


# ---------------------------------------------------------------------------
# Isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_user_isolation(company, user, other_user):
    """Interaction logs are private per user."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="pkm",
    )
    other_logs = UserInteractionLog.objects.filter(user=other_user, company=company)
    assert other_logs.count() == 0


@pytest.mark.django_db
def test_interaction_log_company_isolation(user, company, other_company):
    """Interaction logs are isolated by company."""
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="pkm",
    )
    other_logs = UserInteractionLog.objects.filter(user=user, company=other_company)
    assert other_logs.count() == 0


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_cascade_delete_user(company, user):
    """Deleting a user cascades to their interaction logs."""
    user_id = user.id
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="pkm",
    )
    assert UserInteractionLog.objects.filter(user_id=user_id).count() == 1
    user.delete()
    assert UserInteractionLog.objects.filter(user_id=user_id).count() == 0


@pytest.mark.django_db
def test_interaction_log_cascade_delete_company(company, user):
    """Deleting a company cascades to its interaction logs."""
    company_id = company.id
    UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type="page_view",
        module="pkm",
    )
    assert UserInteractionLog.objects.filter(company_id=company_id).count() == 1
    company.delete()
    assert UserInteractionLog.objects.filter(company_id=company_id).count() == 0


# ---------------------------------------------------------------------------
# String representation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interaction_log_str_representation(company, user):
    """__str__ returns a meaningful representation including user and type."""
    log = UserInteractionLog.objects.create(
        user=user,
        company=company,
        interaction_type=UserInteractionLog.InteractionType.NOTE_CREATE,
        module="pkm",
    )
    s = str(log)
    assert "note_create" in s
    assert "pkm" in s
    assert user.username in s


# ---------------------------------------------------------------------------
# db_table
# ---------------------------------------------------------------------------


def test_interaction_log_db_table():
    """db_table is set to the expected value."""
    assert UserInteractionLog._meta.db_table == "pkm_user_interaction_log"
