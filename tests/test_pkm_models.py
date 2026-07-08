"""Tests for PKM core models: KnowledgeNote, Tag, UserLLMConfig.

Covers model creation, field constraints, unique constraints, multi-tenant
isolation, and relationship behavior (M2M tags).
"""

import pytest
from django.db import IntegrityError

from apps.core.managers import CompanyOwnedModel
from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import KnowledgeNote, Tag, UserLLMConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_TEST", name="PKM Test Co")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(
        username="pkm_user", password="Test1234", email="pkm@t.co"
    )


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="pkm_other", password="Test1234", email="other@t.co"
    )


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_OTHER", name="PKM Other Co")


# ---------------------------------------------------------------------------
# Model inheritance checks
# ---------------------------------------------------------------------------


def test_knowledge_note_extends_company_owned_model():
    """KnowledgeNote must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(KnowledgeNote, CompanyOwnedModel)


def test_tag_extends_company_owned_model():
    """Tag must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(Tag, CompanyOwnedModel)


def test_user_llm_config_extends_company_owned_model():
    """UserLLMConfig must extend CompanyOwnedModel for multi-tenant isolation."""
    assert issubclass(UserLLMConfig, CompanyOwnedModel)


# ---------------------------------------------------------------------------
# Tag model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tag_creation(company, user):
    """Tag can be created with all required fields."""
    tag = Tag.objects.create(user=user, company=company, name="accounting")
    assert tag.pk is not None
    assert tag.user == user
    assert tag.company == company
    assert tag.name == "accounting"
    assert tag.color == ""  # optional, default empty
    assert tag.created_at is not None
    assert tag.updated_at is not None


@pytest.mark.django_db
def test_tag_with_color(company, user):
    """Tag color field accepts hex color string."""
    tag = Tag.objects.create(user=user, company=company, name="tax", color="#ff0000")
    assert tag.color == "#ff0000"


@pytest.mark.django_db
def test_tag_unique_constraint_user_company_name(company, user):
    """Unique constraint on (user, company, name) prevents duplicate tags."""
    Tag.objects.create(user=user, company=company, name="duplicate")
    with pytest.raises(IntegrityError):
        Tag.objects.create(user=user, company=company, name="duplicate")


@pytest.mark.django_db
def test_tag_same_name_different_user(company, user, other_user):
    """Different users can have tags with the same name."""
    tag1 = Tag.objects.create(user=user, company=company, name="shared")
    tag2 = Tag.objects.create(user=other_user, company=company, name="shared")
    assert tag1.pk != tag2.pk


@pytest.mark.django_db
def test_tag_same_name_different_company(user, company, other_company):
    """Same user in different companies can have tags with the same name."""
    tag1 = Tag.objects.create(user=user, company=company, name="cross-company")
    tag2 = Tag.objects.create(user=user, company=other_company, name="cross-company")
    assert tag1.pk != tag2.pk


@pytest.mark.django_db
def test_tag_str_representation(company, user):
    """Tag __str__ returns a meaningful representation."""
    tag = Tag.objects.create(user=user, company=company, name="vat")
    assert "vat" in str(tag)


# ---------------------------------------------------------------------------
# KnowledgeNote model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_note_creation(company, user):
    """KnowledgeNote can be created with all required fields."""
    note = KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Test Note",
        content="This is **markdown** content.",
    )
    assert note.pk is not None
    assert note.user == user
    assert note.company == company
    assert note.title == "Test Note"
    assert note.content == "This is **markdown** content."
    assert note.role_context == ""  # blank by default
    assert note.is_pinned is False  # default False
    assert note.created_at is not None
    assert note.updated_at is not None


@pytest.mark.django_db
def test_note_with_role_context(company, user):
    """role_context field accepts a string value."""
    note = KnowledgeNote.objects.create(
        user=user,
        company=company,
        title="Accountant Note",
        content="Content here",
        role_context="accountant",
    )
    assert note.role_context == "accountant"


@pytest.mark.django_db
def test_note_is_pinned_default_false(company, user):
    """is_pinned defaults to False."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Pin Test", content=""
    )
    assert note.is_pinned is False


@pytest.mark.django_db
def test_note_is_pinned_true(company, user):
    """is_pinned can be set to True."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Pinned", content="", is_pinned=True
    )
    assert note.is_pinned is True


@pytest.mark.django_db
def test_note_title_max_length(company, user):
    """title field accepts up to 255 characters."""
    long_title = "A" * 255
    note = KnowledgeNote.objects.create(
        user=user, company=company, title=long_title, content=""
    )
    assert len(note.title) == 255


@pytest.mark.django_db
def test_note_tags_m2m_relationship(company, user):
    """KnowledgeNote can have multiple tags via M2M relationship."""
    tag1 = Tag.objects.create(user=user, company=company, name="tag1")
    tag2 = Tag.objects.create(user=user, company=company, name="tag2")
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Tagged Note", content=""
    )
    note.tags.add(tag1, tag2)
    assert note.tags.count() == 2
    assert tag1 in note.tags.all()
    assert tag2 in note.tags.all()


@pytest.mark.django_db
def test_note_tags_can_be_empty(company, user):
    """A note with no tags works correctly."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="No Tags", content=""
    )
    assert note.tags.count() == 0


@pytest.mark.django_db
def test_note_tags_remove(company, user):
    """Tags can be removed from a note."""
    tag = Tag.objects.create(user=user, company=company, name="removable")
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Remove Tag", content=""
    )
    note.tags.add(tag)
    assert note.tags.count() == 1
    note.tags.remove(tag)
    assert note.tags.count() == 0


@pytest.mark.django_db
def test_note_user_isolation(company, user, other_user):
    """Notes are private per user - user A's notes not visible to user B."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Private Note", content="secret"
    )
    other_notes = KnowledgeNote.objects.filter(user=other_user, company=company)
    assert note not in other_notes
    assert other_notes.count() == 0


@pytest.mark.django_db
def test_note_company_isolation(user, company, other_company):
    """Notes are isolated by company."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Company A Note", content=""
    )
    other_notes = KnowledgeNote.objects.filter(user=user, company=other_company)
    assert note not in other_notes
    assert other_notes.count() == 0


@pytest.mark.django_db
def test_note_str_representation(company, user):
    """KnowledgeNote __str__ returns a meaningful representation."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="My Note Title", content=""
    )
    assert "My Note Title" in str(note)


@pytest.mark.django_db
def test_note_cascade_delete_user(company, user):
    """Deleting a user cascades to their notes."""
    user_id = user.id
    KnowledgeNote.objects.create(
        user=user, company=company, title="Will be deleted", content=""
    )
    assert KnowledgeNote.objects.filter(user_id=user_id).count() == 1
    user.delete()
    assert KnowledgeNote.objects.filter(user_id=user_id).count() == 0


@pytest.mark.django_db
def test_note_cascade_delete_company(company, user):
    """Deleting a company cascades to its notes."""
    company_id = company.id
    KnowledgeNote.objects.create(
        user=user, company=company, title="Will be deleted", content=""
    )
    assert KnowledgeNote.objects.filter(company_id=company_id).count() == 1
    company.delete()
    assert KnowledgeNote.objects.filter(company_id=company_id).count() == 0


@pytest.mark.django_db
def test_note_updated_at_changes(company, user):
    """updated_at is refreshed on save."""
    note = KnowledgeNote.objects.create(
        user=user, company=company, title="Original", content=""
    )
    original_updated = note.updated_at
    note.title = "Updated"
    note.save()
    note.refresh_from_db()
    assert note.updated_at >= original_updated


# ---------------------------------------------------------------------------
# UserLLMConfig model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_llm_config_creation(company, user):
    """UserLLMConfig can be created with all required fields."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="encrypted_token_here",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert config.pk is not None
    assert config.user == user
    assert config.company == company
    assert config.provider == "openai"
    assert config.api_key_encrypted == "encrypted_token_here"
    assert config.api_base == ""  # blank by default
    assert config.default_model == "gpt-4o"
    assert config.default_embedding_model == "text-embedding-3-small"
    assert config.is_active is False  # default
    assert config.created_at is not None
    assert config.updated_at is not None


@pytest.mark.django_db
def test_llm_config_provider_choices(company, user):
    """All 6 supported providers can be stored."""
    providers = ["openai", "anthropic", "gemini", "groq", "openrouter", "ollama"]
    for provider in providers:
        config = UserLLMConfig.objects.create(
            user=user,
            company=company,
            provider=provider,
            api_key_encrypted=f"key_{provider}",
            default_model=f"model_{provider}",
            default_embedding_model="text-embedding-3-small",
        )
        assert config.provider == provider


@pytest.mark.django_db
def test_llm_config_unique_constraint_user_company_provider(company, user):
    """Unique constraint on (user, company, provider) prevents duplicates."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key1",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    with pytest.raises(IntegrityError):
        UserLLMConfig.objects.create(
            user=user,
            company=company,
            provider="openai",
            api_key_encrypted="key2",
            default_model="gpt-4o-mini",
            default_embedding_model="text-embedding-3-small",
        )


@pytest.mark.django_db
def test_llm_config_same_provider_different_user(company, user, other_user):
    """Different users can have configs for the same provider."""
    c1 = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key_user1",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    c2 = UserLLMConfig.objects.create(
        user=other_user,
        company=company,
        provider="openai",
        api_key_encrypted="key_user2",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert c1.pk != c2.pk


@pytest.mark.django_db
def test_llm_config_same_provider_different_company(user, company, other_company):
    """Same user in different companies can have configs for the same provider."""
    c1 = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="anthropic",
        api_key_encrypted="key_co1",
        default_model="claude-sonnet-4-20250514",
        default_embedding_model="text-embedding-3-small",
    )
    c2 = UserLLMConfig.objects.create(
        user=user,
        company=other_company,
        provider="anthropic",
        api_key_encrypted="key_co2",
        default_model="claude-sonnet-4-20250514",
        default_embedding_model="text-embedding-3-small",
    )
    assert c1.pk != c2.pk


@pytest.mark.django_db
def test_llm_config_same_user_multiple_providers(company, user):
    """A user can have configs for multiple providers in the same company."""
    for provider in ["openai", "anthropic", "gemini"]:
        UserLLMConfig.objects.create(
            user=user,
            company=company,
            provider=provider,
            api_key_encrypted=f"key_{provider}",
            default_model=f"model_{provider}",
            default_embedding_model="text-embedding-3-small",
        )
    assert UserLLMConfig.objects.filter(user=user, company=company).count() == 3


@pytest.mark.django_db
def test_llm_config_is_active_default_false(company, user):
    """is_active defaults to False."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert config.is_active is False


@pytest.mark.django_db
def test_llm_config_is_active_true(company, user):
    """is_active can be set to True."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
        is_active=True,
    )
    assert config.is_active is True


@pytest.mark.django_db
def test_llm_config_api_base_blank(company, user):
    """api_base is blank by default."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert config.api_base == ""


@pytest.mark.django_db
def test_llm_config_api_base_custom(company, user):
    """api_base can be set to a custom URL."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        api_base="http://localhost:11434",
        default_model="llama3",
        default_embedding_model="nomic-embed-text",
    )
    assert config.api_base == "http://localhost:11434"


@pytest.mark.django_db
def test_llm_config_user_isolation(company, user, other_user):
    """LLM configs are private per user."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="user_a_key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    other_configs = UserLLMConfig.objects.filter(user=other_user, company=company)
    assert config not in other_configs
    assert other_configs.count() == 0


@pytest.mark.django_db
def test_llm_config_company_isolation(user, company, other_company):
    """LLM configs are isolated by company."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="co_a_key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    other_configs = UserLLMConfig.objects.filter(user=user, company=other_company)
    assert config not in other_configs
    assert other_configs.count() == 0


@pytest.mark.django_db
def test_llm_config_str_representation(company, user):
    """UserLLMConfig __str__ returns a meaningful representation."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    s = str(config)
    assert "openai" in s


@pytest.mark.django_db
def test_llm_config_cascade_delete_user(company, user):
    """Deleting a user cascades to their LLM configs."""
    user_id = user.id
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert UserLLMConfig.objects.filter(user_id=user_id).count() == 1
    user.delete()
    assert UserLLMConfig.objects.filter(user_id=user_id).count() == 0


@pytest.mark.django_db
def test_llm_config_cascade_delete_company(company, user):
    """Deleting a company cascades to its LLM configs."""
    company_id = company.id
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted="key",
        default_model="gpt-4o",
        default_embedding_model="text-embedding-3-small",
    )
    assert UserLLMConfig.objects.filter(company_id=company_id).count() == 1
    company.delete()
    assert UserLLMConfig.objects.filter(company_id=company_id).count() == 0
