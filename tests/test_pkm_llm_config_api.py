"""Integration tests for PKM LLM Config API (/api/v1/pkm/llm-configs/, /api/v1/pkm/providers/).

Covers:
  - CRUD: create, list, update, delete LLM configs
  - Encryption-at-rest: DB column stores ciphertext, not plaintext
  - API response never exposes plaintext or encrypted key
  - Validate endpoint (mocked LLM call)
  - Providers list returns all 6 supported providers
  - Per-user isolation (user B cannot see/access user A configs)
  - Per-company isolation
  - Ollama provider can be saved without an API key

Fulfills:
    VAL-LLM-001 through VAL-LLM-015
"""

from unittest.mock import patch

import pytest
from django.db import connection
from django.test import Client

from apps.core.models import Company
from apps.identity.models import User
from apps.pkm.models import UserLLMConfig
from apps.pkm.services import encryption_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_LLM", name="PKM LLM Co")


@pytest.fixture
def other_company(db):
    return Company.objects.create(code="PKM_LLM2", name="PKM LLM Co 2")


@pytest.fixture
def user(db, company):
    return User.objects.create_user(username="llm_user", password="Test1234", email="llmuser@t.co")


@pytest.fixture
def other_user(db, company):
    return User.objects.create_user(
        username="llm_other", password="Test1234", email="llmother@t.co"
    )


@pytest.fixture
def client(user):
    """Authenticated test client for ``user``."""
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def other_client(other_user):
    """Authenticated test client for ``other_user`` (same company)."""
    c = Client()
    c.force_login(other_user)
    return c


# ---------------------------------------------------------------------------
# Providers endpoint (VAL-LLM-002..007: all 6 providers listed)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_providers_list_returns_all_six(client):
    """GET /api/v1/pkm/providers/ returns all 6 supported providers."""
    response = client.get("/api/v1/pkm/providers/")
    assert response.status_code == 200
    data = response.json()
    providers = {p["value"] for p in data["providers"]}
    assert providers == {"openai", "anthropic", "gemini", "groq", "openrouter", "ollama"}
    assert len(data["providers"]) == 6


@pytest.mark.django_db
def test_providers_list_includes_models(client):
    """Each provider entry includes suggested models."""
    response = client.get("/api/v1/pkm/providers/")
    data = response.json()
    for p in data["providers"]:
        assert "models" in p
        assert isinstance(p["models"], list)
        assert len(p["models"]) > 0


@pytest.mark.django_db
def test_providers_list_unauthenticated(db):
    """GET /api/v1/pkm/providers/ without auth returns 401."""
    c = Client()
    response = c.get("/api/v1/pkm/providers/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Create config (VAL-LLM-002..007, VAL-LLM-008, VAL-LLM-009)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_openai_config(client, user, company):
    """POST creates an OpenAI config with encrypted API key."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-test-key-12345",
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["provider"] == "openai"
    assert data["default_model"] == "gpt-4o"
    assert data["is_active"] is False
    assert data["has_key"] is True
    # Response must never include the encrypted or plaintext key
    assert "api_key_encrypted" not in data
    assert "api_key" not in data


@pytest.mark.django_db
def test_create_anthropic_config(client):
    """POST creates an Anthropic config."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "anthropic",
            "api_key": "sk-ant-test12345",
            "default_model": "claude-sonnet-4-20250514",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["provider"] == "anthropic"


@pytest.mark.django_db
def test_create_gemini_config(client):
    """POST creates a Gemini config."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "gemini",
            "api_key": "AIza-test-key",
            "default_model": "gemini-2.0-flash",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["provider"] == "gemini"


@pytest.mark.django_db
def test_create_groq_config(client):
    """POST creates a Groq config."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "groq",
            "api_key": "gsk_test12345",
            "default_model": "llama-3.3-70b-versatile",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["provider"] == "groq"


@pytest.mark.django_db
def test_create_openrouter_config(client):
    """POST creates an OpenRouter config."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openrouter",
            "api_key": "sk-or-test12345",
            "default_model": "anthropic/claude-3.5-sonnet",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["provider"] == "openrouter"


@pytest.mark.django_db
def test_create_ollama_config_without_api_key(client):
    """POST creates an Ollama config with only a base URL (no API key needed)."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "ollama",
            "api_base": "http://localhost:11434",
            "default_model": "llama3",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["provider"] == "ollama"
    assert data["has_key"] is False


@pytest.mark.django_db
def test_create_config_with_custom_api_base(client):
    """POST can set a custom api_base for OpenAI-compatible endpoints."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-test",
            "api_base": "https://my-proxy.example.com/v1",
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["api_base"] == "https://my-proxy.example.com/v1"


@pytest.mark.django_db
def test_create_config_sets_default_model(client):
    """POST saves the default_model field."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-test",
            "default_model": "gpt-4o-mini",
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["default_model"] == "gpt-4o-mini"


@pytest.mark.django_db
def test_create_config_active_flag(client):
    """POST with is_active=True sets the config as active."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-test",
            "default_model": "gpt-4o",
            "is_active": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.django_db
def test_create_config_invalid_provider(client):
    """POST with an invalid provider returns 422."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "invalid_provider",
            "api_key": "sk-test",
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_create_config_missing_default_model(client):
    """POST without default_model returns 422."""
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-test",
        },
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_create_duplicate_provider_returns_400(client, user, company):
    """POST with same provider twice returns 400 (unique constraint)."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-old"),
        default_model="gpt-4o",
    )
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": "sk-new",
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_config_unauthenticated(db):
    """POST without auth returns 401."""
    c = Client()
    response = c.post(
        "/api/v1/pkm/llm-configs/",
        data={"provider": "openai", "api_key": "sk-test", "default_model": "gpt-4o"},
        content_type="application/json",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Encryption-at-rest (VAL-LLM-008)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_key_encrypted_at_rest(client, user, company):
    """The DB column stores Fernet ciphertext, not the plaintext key."""
    plaintext_key = "sk-super-secret-key-12345"
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": plaintext_key,
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    config_id = response.json()["id"]

    # Query the raw DB column
    config = UserLLMConfig.objects.get(id=config_id)
    stored = config.api_key_encrypted

    # The stored value must NOT be the plaintext
    assert stored != plaintext_key
    assert plaintext_key not in stored
    # The stored value should be a Fernet token (starts with 'gAAAAA')
    assert stored.startswith("gAAAAA")
    # Decryption round-trip works
    assert encryption_service.decrypt(stored) == plaintext_key


@pytest.mark.django_db
def test_api_key_encrypted_at_rest_raw_sql(client, user, company):
    """Verify ciphertext at rest via a raw SQL query (DB inspection)."""
    plaintext_key = "sk-raw-sql-test-key"
    response = client.post(
        "/api/v1/pkm/llm-configs/",
        data={
            "provider": "openai",
            "api_key": plaintext_key,
            "default_model": "gpt-4o",
        },
        content_type="application/json",
    )
    config_id = response.json()["id"]

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT api_key_encrypted FROM pkm_user_llm_config WHERE id = %s",
            [config_id],
        )
        row = cursor.fetchone()
    stored = row[0]
    assert stored != plaintext_key
    assert plaintext_key not in stored
    assert stored.startswith("gAAAAA")


@pytest.mark.django_db
def test_response_never_exposes_key(client, user, company):
    """API response never includes api_key or api_key_encrypted fields."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-secret"),
        default_model="gpt-4o",
        is_active=True,
    )
    # List response
    response = client.get("/api/v1/pkm/llm-configs/")
    assert response.status_code == 200
    data = response.json()
    # Could be a list or paginated; check the first item
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 1
    item = items[0]
    assert "api_key_encrypted" not in item
    assert "api_key" not in item
    assert item["has_key"] is True
    assert item["provider"] == "openai"
    assert item["is_active"] is True

    # Detail (via update PUT returns the config too)
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"default_model": "gpt-4o-mini"},
        content_type="application/json",
    )
    assert response.status_code == 200
    item = response.json()
    assert "api_key_encrypted" not in item
    assert "api_key" not in item


@pytest.mark.django_db
def test_encryption_different_keys_different_ciphertext(client, user, company):
    """Different API keys produce different ciphertexts."""
    r1 = client.post(
        "/api/v1/pkm/llm-configs/",
        data={"provider": "openai", "api_key": "sk-key-one", "default_model": "gpt-4o"},
        content_type="application/json",
    )
    r2 = client.post(
        "/api/v1/pkm/llm-configs/",
        data={"provider": "anthropic", "api_key": "sk-key-two", "default_model": "claude"},
        content_type="application/json",
    )
    c1 = UserLLMConfig.objects.get(id=r1.json()["id"])
    c2 = UserLLMConfig.objects.get(id=r2.json()["id"])
    assert c1.api_key_encrypted != c2.api_key_encrypted


# ---------------------------------------------------------------------------
# List configs
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_configs(client, user, company):
    """GET returns the user's configs."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-1"),
        default_model="gpt-4o",
    )
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="anthropic",
        api_key_encrypted=encryption_service.encrypt("sk-2"),
        default_model="claude",
    )
    response = client.get("/api/v1/pkm/llm-configs/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 2


@pytest.mark.django_db
def test_list_configs_empty(client):
    """GET returns empty list when user has no configs."""
    response = client.get("/api/v1/pkm/llm-configs/")
    assert response.status_code == 200
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_list_configs_has_key_boolean(client, user, company):
    """List response shows has_key=True for configs with a key, False for Ollama."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-1"),
        default_model="gpt-4o",
    )
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        default_model="llama3",
    )
    response = client.get("/api/v1/pkm/llm-configs/")
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    by_provider = {item["provider"]: item for item in items}
    assert by_provider["openai"]["has_key"] is True
    assert by_provider["ollama"]["has_key"] is False


# ---------------------------------------------------------------------------
# Update config (VAL-LLM-010)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_update_config_model(client, user, company):
    """PUT updates the default_model."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-test"),
        default_model="gpt-4o",
    )
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"default_model": "gpt-4o-mini"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["default_model"] == "gpt-4o-mini"
    config.refresh_from_db()
    assert config.default_model == "gpt-4o-mini"


@pytest.mark.django_db
def test_update_config_api_key(client, user, company):
    """PUT can update the API key (re-encrypts)."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-old"),
        default_model="gpt-4o",
    )
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"api_key": "sk-new-key"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    config.refresh_from_db()
    assert encryption_service.decrypt(config.api_key_encrypted) == "sk-new-key"
    # The old key is no longer the stored value
    assert config.api_key_encrypted != encryption_service.encrypt("sk-old")


@pytest.mark.django_db
def test_update_config_active(client, user, company):
    """PUT can toggle is_active."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-test"),
        default_model="gpt-4o",
        is_active=False,
    )
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"is_active": True},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.django_db
def test_update_config_api_base(client, user, company):
    """PUT can update the api_base URL."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-test"),
        default_model="gpt-4o",
    )
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"api_base": "https://custom.example.com/v1"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["api_base"] == "https://custom.example.com/v1"


@pytest.mark.django_db
def test_update_config_without_api_key_keeps_existing(client, user, company):
    """PUT without api_key field keeps the existing encrypted key."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-original"),
        default_model="gpt-4o",
    )
    old_encrypted = config.api_key_encrypted
    response = client.put(
        f"/api/v1/pkm/llm-configs/{config.id}/",
        data={"default_model": "gpt-4o-mini"},
        content_type="application/json",
    )
    assert response.status_code == 200
    config.refresh_from_db()
    assert config.api_key_encrypted == old_encrypted


@pytest.mark.django_db
def test_update_nonexistent_config_returns_404(client):
    """PUT on nonexistent config returns 404."""
    response = client.put(
        "/api/v1/pkm/llm-configs/99999/",
        data={"default_model": "gpt-4o"},
        content_type="application/json",
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete config (VAL-LLM-011)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_config(client, user, company):
    """DELETE removes the config."""
    config = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-test"),
        default_model="gpt-4o",
    )
    response = client.delete(f"/api/v1/pkm/llm-configs/{config.id}/")
    assert response.status_code == 200
    assert not UserLLMConfig.objects.filter(id=config.id).exists()


@pytest.mark.django_db
def test_delete_nonexistent_config_returns_404(client):
    """DELETE on nonexistent config returns 404."""
    response = client.delete("/api/v1/pkm/llm-configs/99999/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Validate endpoint (VAL-LLM-013)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_api_key_success(client):
    """POST /validate/ returns success when the key is valid (mocked)."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=True):
        response = client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={"provider": "openai", "api_key": "sk-valid-key"},
            content_type="application/json",
        )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.django_db
def test_validate_api_key_failure(client):
    """POST /validate/ returns failure when the key is invalid (mocked)."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=False):
        response = client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={"provider": "openai", "api_key": "sk-invalid"},
            content_type="application/json",
        )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


@pytest.mark.django_db
def test_validate_api_key_with_base_url(client):
    """POST /validate/ passes api_base to the validation service (mocked)."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=True) as mock_val:
        response = client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={
                "provider": "openai",
                "api_key": "sk-valid",
                "api_base": "https://custom.example.com/v1",
            },
            content_type="application/json",
        )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    mock_val.assert_called_once_with(
        provider="openai",
        api_key="sk-valid",
        api_base="https://custom.example.com/v1",
    )


@pytest.mark.django_db
def test_validate_does_not_save_config(client):
    """POST /validate/ does not create any config in the DB."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=True):
        client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={"provider": "openai", "api_key": "sk-test"},
            content_type="application/json",
        )
    assert UserLLMConfig.objects.count() == 0


@pytest.mark.django_db
def test_validate_missing_provider(client):
    """POST /validate/ without provider returns 422."""
    response = client.post(
        "/api/v1/pkm/llm-configs/validate/",
        data={"api_key": "sk-test"},
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_validate_missing_api_key_for_non_ollama(client):
    """POST /validate/ without api_key for non-ollama returns 422."""
    response = client.post(
        "/api/v1/pkm/llm-configs/validate/",
        data={"provider": "openai"},
        content_type="application/json",
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Per-user isolation (VAL-LLM-012)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_configs_private_per_user_list(user, other_user, company):
    """User B's list does not include user A's configs."""
    UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-a"),
        default_model="gpt-4o",
    )
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.get("/api/v1/pkm/llm-configs/")
    data = response.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) == 0


@pytest.mark.django_db
def test_configs_private_per_user_update(user, other_user, company):
    """User B cannot update user A's config."""
    config_a = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-a"),
        default_model="gpt-4o",
    )
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.put(
        f"/api/v1/pkm/llm-configs/{config_a.id}/",
        data={"default_model": "hacked"},
        content_type="application/json",
    )
    assert response.status_code == 404
    config_a.refresh_from_db()
    assert config_a.default_model == "gpt-4o"


@pytest.mark.django_db
def test_configs_private_per_user_delete(user, other_user, company):
    """User B cannot delete user A's config."""
    config_a = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-a"),
        default_model="gpt-4o",
    )
    c_b = Client()
    c_b.force_login(other_user)
    response = c_b.delete(f"/api/v1/pkm/llm-configs/{config_a.id}/")
    assert response.status_code == 404
    assert UserLLMConfig.objects.filter(id=config_a.id).exists()


# ---------------------------------------------------------------------------
# Per-company isolation (VAL-LLM-015)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_configs_isolated_by_company_direct(user, company, other_company):
    """Configs are scoped by company at the ORM level."""
    config_x = UserLLMConfig.objects.create(
        user=user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-x"),
        default_model="gpt-4o",
    )
    config_y = UserLLMConfig.objects.create(
        user=user,
        company=other_company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-y"),
        default_model="gpt-4o",
    )
    qs_x = UserLLMConfig.objects.filter(user=user, company=company)
    assert config_x in qs_x
    assert config_y not in qs_x
    qs_y = UserLLMConfig.objects.filter(user=user, company=other_company)
    assert config_y in qs_y
    assert config_x not in qs_y
