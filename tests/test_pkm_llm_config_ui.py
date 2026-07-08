"""Integration tests for PKM LLM Config UI views (/modern/knowledge/settings/).

Covers:
  - LLM config settings page renders with provider dropdown
  - Adding OpenAI config via UI
  - Adding Anthropic config via UI
  - Adding Gemini config via UI
  - Adding Groq config via UI
  - Adding OpenRouter config via UI
  - Adding Ollama config (no API key needed) via UI
  - API key stored encrypted (no plaintext in DB)
  - Validate button (AJAX endpoint) calls API and shows result
  - Custom base URL field available
  - Edit config via UI
  - Delete config via UI
  - Q&A disabled state: dashboard shows 'configure provider first' prompt
    when no active config exists
  - Per-user isolation

Fulfills:
    VAL-LLM-016 - Q&A disabled without LLM config
"""

from unittest.mock import patch

import pytest
from django.test import Client

from apps.core.models import Company
from apps.identity.models import Permission, Role, User, UserCompanyRole
from apps.pkm.models import UserLLMConfig
from apps.pkm.services import encryption_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(code="PKM_LLM_UI", name="PKM LLM UI Co")


@pytest.fixture
def admin_user(db):
    """Superuser — bypasses permission checks (has pkm.access implicitly)."""
    return User.objects.create_superuser(
        username="llm_admin", password="Test1234", email="llmadmin@t.co"
    )


@pytest.fixture
def regular_user_with_perm(db, company):
    """Regular user with pkm.access permission."""
    user = User.objects.create_user(
        username="llm_perm_user", password="Test1234", email="llmperm@t.co"
    )
    perm, _ = Permission.objects.get_or_create(
        code="pkm.access",
        defaults={"module": "pkm", "name": "PKM Access", "description": "Access PKM module"},
    )
    role = Role.objects.create(company=company, code="llm_role", name="LLM Role")
    role.permissions.add(perm)
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def regular_user_no_perm(db, company):
    """Regular user WITHOUT pkm.access permission."""
    user = User.objects.create_user(
        username="llm_noperm", password="Test1234", email="llmnoperm@t.co"
    )
    role = Role.objects.create(company=company, code="no_llm", name="No LLM Role")
    UserCompanyRole.objects.create(user=user, company=company, role=role)
    return user


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.fixture
def perm_client(regular_user_with_perm, company):
    """Client for a regular user WITH pkm.access permission."""
    c = Client()
    c.force_login(regular_user_with_perm)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def no_perm_client(regular_user_no_perm, company):
    """Client for a regular user WITHOUT pkm.access permission."""
    c = Client()
    c.force_login(regular_user_no_perm)
    session = c.session
    session["current_company_id"] = company.id
    session.save()
    return c


@pytest.fixture
def openai_config(admin_user, company):
    return UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-existing-key"),
        default_model="gpt-4o",
        is_active=True,
    )


@pytest.fixture
def ollama_config(admin_user, company):
    return UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="ollama",
        api_key_encrypted="",
        api_base="http://localhost:11434",
        default_model="llama3",
    )


# ---------------------------------------------------------------------------
# Settings page renders with provider dropdown
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_settings_page_renders(admin_client):
    """GET /modern/knowledge/settings/ renders the config list page."""
    response = admin_client.get("/modern/knowledge/settings/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Cấu hình nhà cung cấp AI" in content
    assert "Thêm cấu hình" in content


@pytest.mark.django_db
def test_create_page_renders_with_provider_dropdown(admin_client):
    """GET create page shows provider dropdown with all 6 providers."""
    response = admin_client.get("/modern/knowledge/settings/new/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # All 6 providers should be in the dropdown
    assert "OpenAI" in content
    assert "Anthropic" in content
    assert "Google Gemini" in content
    assert "Groq" in content
    assert "OpenRouter" in content
    assert "Ollama" in content


@pytest.mark.django_db
def test_create_page_has_api_key_password_field(admin_client):
    """Create page renders API key as a password input."""
    response = admin_client.get("/modern/knowledge/settings/new/")
    content = response.content.decode("utf-8")
    assert 'type="password"' in content
    assert 'name="api_key"' in content


@pytest.mark.django_db
def test_create_page_has_base_url_field(admin_client):
    """Create page has an API base URL field."""
    response = admin_client.get("/modern/knowledge/settings/new/")
    content = response.content.decode("utf-8")
    assert 'name="api_base"' in content
    assert "API Base URL" in content


@pytest.mark.django_db
def test_create_page_has_model_field(admin_client):
    """Create page has a default model field."""
    response = admin_client.get("/modern/knowledge/settings/new/")
    content = response.content.decode("utf-8")
    assert 'name="default_model"' in content


@pytest.mark.django_db
def test_create_page_has_validate_button(admin_client):
    """Create page has a validate button."""
    response = admin_client.get("/modern/knowledge/settings/new/")
    content = response.content.decode("utf-8")
    assert "Kiểm tra API key" in content
    assert "validateApiKey" in content


@pytest.mark.django_db
def test_unauthenticated_redirect_to_login(db):
    """Unauthenticated user is redirected to login."""
    c = Client()
    response = c.get("/modern/knowledge/settings/")
    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
def test_no_perm_user_redirected(no_perm_client):
    """User without pkm.access is redirected to /no-access/."""
    response = no_perm_client.get("/modern/knowledge/settings/")
    assert response.status_code == 302
    assert "/no-access/" in response.url


# ---------------------------------------------------------------------------
# Add OpenAI config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_openai_config(admin_client, admin_user, company):
    """POST create form saves an OpenAI config."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": "sk-test-openai",
            "default_model": "gpt-4o",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/modern/knowledge/settings/")
    config = UserLLMConfig.objects.get(provider="openai", user=admin_user)
    assert config.default_model == "gpt-4o"
    assert config.is_active is True
    # API key is encrypted
    assert config.api_key_encrypted != "sk-test-openai"
    assert encryption_service.decrypt(config.api_key_encrypted) == "sk-test-openai"


@pytest.mark.django_db
def test_add_openai_config_shows_in_list(admin_client, admin_user, company):
    """After adding, the config appears in the list page."""
    UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-test"),
        default_model="gpt-4o",
    )
    response = admin_client.get("/modern/knowledge/settings/")
    content = response.content.decode("utf-8")
    assert "OpenAI" in content
    assert "gpt-4o" in content


# ---------------------------------------------------------------------------
# Add Anthropic config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_anthropic_config(admin_client, admin_user, company):
    """POST create form saves an Anthropic config."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "anthropic",
            "api_key": "sk-ant-test",
            "default_model": "claude-sonnet-4-20250514",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="anthropic", user=admin_user)
    assert config.default_model == "claude-sonnet-4-20250514"
    assert encryption_service.decrypt(config.api_key_encrypted) == "sk-ant-test"


# ---------------------------------------------------------------------------
# Add Gemini config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_gemini_config(admin_client, admin_user, company):
    """POST create form saves a Gemini config."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "gemini",
            "api_key": "AIza-test-key",
            "default_model": "gemini-2.0-flash",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="gemini", user=admin_user)
    assert config.default_model == "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# Add Groq config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_groq_config(admin_client, admin_user, company):
    """POST create form saves a Groq config."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "groq",
            "api_key": "gsk-test-key",
            "default_model": "llama-3.3-70b-versatile",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="groq", user=admin_user)
    assert config.default_model == "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Add OpenRouter config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_openrouter_config(admin_client, admin_user, company):
    """POST create form saves an OpenRouter config."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openrouter",
            "api_key": "sk-or-test-key",
            "default_model": "anthropic/claude-3.5-sonnet",
            "api_base": "https://openrouter.ai/api/v1",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="openrouter", user=admin_user)
    assert config.default_model == "anthropic/claude-3.5-sonnet"


# ---------------------------------------------------------------------------
# Add Ollama config (no API key)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_ollama_config_without_api_key(admin_client, admin_user, company):
    """POST create form saves an Ollama config with base URL but no API key."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "ollama",
            "api_key": "",  # No API key needed
            "api_base": "http://localhost:11434",
            "default_model": "llama3",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="ollama", user=admin_user)
    assert config.default_model == "llama3"
    assert config.api_base == "http://localhost:11434"
    assert config.api_key_encrypted == ""


# ---------------------------------------------------------------------------
# API key stored encrypted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_key_stored_encrypted(admin_client, admin_user, company):
    """API key saved via UI is stored encrypted (ciphertext, not plaintext)."""
    plaintext = "sk-very-secret-key-12345"
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": plaintext,
            "default_model": "gpt-4o",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="openai", user=admin_user)
    # The stored value must NOT be the plaintext
    assert config.api_key_encrypted != plaintext
    assert plaintext not in config.api_key_encrypted
    # Should be a Fernet token
    assert config.api_key_encrypted.startswith("gAAAAA")
    # Decryption round-trip
    assert encryption_service.decrypt(config.api_key_encrypted) == plaintext


@pytest.mark.django_db
def test_api_key_not_shown_in_list(admin_client, admin_user, company):
    """List page does not display the plaintext API key."""
    UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-super-secret-key"),
        default_model="gpt-4o",
    )
    response = admin_client.get("/modern/knowledge/settings/")
    content = response.content.decode("utf-8")
    assert "sk-super-secret-key" not in content
    # Should show "Đã lưu (mã hóa)" instead
    assert "Đã lưu" in content or "mã hóa" in content


# ---------------------------------------------------------------------------
# Custom base URL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_custom_base_url_saved(admin_client, admin_user, company):
    """POST with custom api_base saves the base URL."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": "sk-test",
            "api_base": "https://my-proxy.example.com/v1",
            "default_model": "gpt-4o",
        },
    )
    assert response.status_code == 302
    config = UserLLMConfig.objects.get(provider="openai", user=admin_user)
    assert config.api_base == "https://my-proxy.example.com/v1"


# ---------------------------------------------------------------------------
# Edit config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_edit_page_loads(admin_client, openai_config):
    """GET edit page loads with existing config data."""
    response = admin_client.get(f"/modern/knowledge/settings/{openai_config.pk}/edit/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "OpenAI" in content
    assert "gpt-4o" in content


@pytest.mark.django_db
def test_edit_page_does_not_pre_fill_api_key(admin_client, openai_config):
    """Edit page API key field is empty (never pre-fills decrypted key)."""
    response = admin_client.get(f"/modern/knowledge/settings/{openai_config.pk}/edit/")
    content = response.content.decode("utf-8")
    # The decrypted key should not appear anywhere
    assert "sk-existing-key" not in content
    # Placeholder should indicate leaving blank keeps existing
    assert "Để trống" in content


@pytest.mark.django_db
def test_edit_config_update_model(admin_client, openai_config):
    """POST edit page updates the model."""
    response = admin_client.post(
        f"/modern/knowledge/settings/{openai_config.pk}/edit/",
        {
            "default_model": "gpt-4o-mini",
            "api_base": "",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    openai_config.refresh_from_db()
    assert openai_config.default_model == "gpt-4o-mini"


@pytest.mark.django_db
def test_edit_config_keep_existing_api_key(admin_client, openai_config):
    """POST edit without api_key keeps the existing encrypted key."""
    old_encrypted = openai_config.api_key_encrypted
    response = admin_client.post(
        f"/modern/knowledge/settings/{openai_config.pk}/edit/",
        {
            "default_model": "gpt-4o-mini",
            "api_key": "",  # Leave blank
            "api_base": "",
        },
    )
    assert response.status_code == 302
    openai_config.refresh_from_db()
    assert openai_config.api_key_encrypted == old_encrypted
    assert encryption_service.decrypt(openai_config.api_key_encrypted) == "sk-existing-key"


@pytest.mark.django_db
def test_edit_config_change_api_key(admin_client, openai_config):
    """POST edit with new api_key updates and re-encrypts."""
    response = admin_client.post(
        f"/modern/knowledge/settings/{openai_config.pk}/edit/",
        {
            "default_model": "gpt-4o",
            "api_key": "sk-new-replacement",
            "api_base": "",
        },
    )
    assert response.status_code == 302
    openai_config.refresh_from_db()
    assert encryption_service.decrypt(openai_config.api_key_encrypted) == "sk-new-replacement"


@pytest.mark.django_db
def test_edit_config_404_for_nonexistent(admin_client):
    """GET edit on nonexistent config returns 404."""
    response = admin_client.get("/modern/knowledge/settings/99999/edit/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_edit_config_empty_model_validation(admin_client, openai_config):
    """POST edit with empty model shows error."""
    response = admin_client.post(
        f"/modern/knowledge/settings/{openai_config.pk}/edit/",
        {
            "default_model": "",
            "api_base": "",
        },
    )
    assert response.status_code == 200  # Stays on form
    content = response.content.decode("utf-8")
    assert "Model mặc định là bắt buộc" in content


# ---------------------------------------------------------------------------
# Delete config
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_confirm_page_loads(admin_client, openai_config):
    """GET delete confirmation page loads."""
    response = admin_client.get(f"/modern/knowledge/settings/{openai_config.pk}/delete/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Xác nhận" in content or "Xóa cấu hình" in content
    assert "OpenAI" in content


@pytest.mark.django_db
def test_delete_config_submit(admin_client, openai_config):
    """POST delete confirmation removes the config."""
    pk = openai_config.pk
    response = admin_client.post(f"/modern/knowledge/settings/{pk}/delete/", {})
    assert response.status_code == 302
    assert response.url.endswith("/modern/knowledge/settings/")
    assert not UserLLMConfig.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_delete_config_404_for_nonexistent(admin_client):
    """DELETE nonexistent config returns 404."""
    response = admin_client.post("/modern/knowledge/settings/99999/delete/", {})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Q&A disabled state (VAL-LLM-016)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_shows_configure_prompt_without_config(admin_client):
    """Dashboard shows 'configure provider first' prompt when no config exists."""
    response = admin_client.get("/modern/knowledge/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Hỏi đáp" in content or "Q&A" in content
    assert "Cấu hình nhà cung cấp" in content
    assert "cấu hình nhà cung cấp" in content.lower() or "configure" in content.lower()


@pytest.mark.django_db
def test_dashboard_no_prompt_with_active_config(admin_client, openai_config):
    """Dashboard does NOT show the prompt when an active config exists."""
    response = admin_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    # The warning prompt should NOT appear
    assert "Tính năng Hỏi đáp (Q&A) đang tắt" not in content


@pytest.mark.django_db
def test_dashboard_shows_prompt_with_inactive_config(admin_client, openai_config):
    """Dashboard shows prompt when config exists but is not active."""
    openai_config.is_active = False
    openai_config.save()
    response = admin_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    assert "Tính năng Hỏi đáp (Q&A) đang tắt" in content


@pytest.mark.django_db
def test_settings_page_shows_prompt_without_config(admin_client):
    """Settings page shows 'configure provider first' prompt."""
    response = admin_client.get("/modern/knowledge/settings/")
    content = response.content.decode("utf-8")
    assert "Chưa có cấu hình AI hoạt động" in content


@pytest.mark.django_db
def test_settings_page_no_prompt_with_active_config(admin_client, openai_config):
    """Settings page does NOT show prompt when active config exists."""
    response = admin_client.get("/modern/knowledge/settings/")
    content = response.content.decode("utf-8")
    assert "Chưa có cấu hình AI hoạt động" not in content


# ---------------------------------------------------------------------------
# Validation (AJAX endpoint integration)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_endpoint_success(admin_client):
    """Validate endpoint returns success (mocked)."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=True):
        response = admin_client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={"provider": "openai", "api_key": "sk-valid"},
            content_type="application/json",
        )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.django_db
def test_validate_endpoint_failure(admin_client):
    """Validate endpoint returns failure (mocked)."""
    with patch("apps.pkm.services.llm_service.validate_api_key", return_value=False):
        response = admin_client.post(
            "/api/v1/pkm/llm-configs/validate/",
            data={"provider": "openai", "api_key": "sk-invalid"},
            content_type="application/json",
        )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_configs_private_per_user(admin_client, admin_user, regular_user_with_perm, company):
    """User B cannot see or access User A's LLM config via UI."""
    UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-admin-key"),
        default_model="gpt-4o",
    )
    # Other user logs in
    other_client = Client()
    other_client.force_login(regular_user_with_perm)
    session = other_client.session
    session["current_company_id"] = company.id
    session.save()

    # Other user sees empty list
    response = other_client.get("/modern/knowledge/settings/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Chưa có cấu hình AI" in content  # Empty state

    # Other user cannot edit admin's config (404)
    config = UserLLMConfig.objects.get(provider="openai", user=admin_user)
    response = other_client.get(f"/modern/knowledge/settings/{config.pk}/edit/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Duplicate provider prevention
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_duplicate_provider_prevented(admin_client, admin_user, company):
    """Adding the same provider twice shows an error."""
    UserLLMConfig.objects.create(
        user=admin_user,
        company=company,
        provider="openai",
        api_key_encrypted=encryption_service.encrypt("sk-first"),
        default_model="gpt-4o",
    )
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": "sk-second",
            "default_model": "gpt-4o",
        },
    )
    assert response.status_code == 200  # Stays on form
    content = response.content.decode("utf-8")
    assert "Đã có cấu hình" in content


# ---------------------------------------------------------------------------
# Validation: missing required fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_missing_provider(admin_client):
    """POST without provider shows error."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "",
            "api_key": "sk-test",
            "default_model": "gpt-4o",
        },
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "chọn nhà cung cấp" in content.lower()


@pytest.mark.django_db
def test_create_missing_api_key_for_openai(admin_client):
    """POST without api_key for OpenAI shows error."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": "",
            "default_model": "gpt-4o",
        },
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "API key" in content


@pytest.mark.django_db
def test_create_missing_model(admin_client):
    """POST without default_model shows error."""
    response = admin_client.post(
        "/modern/knowledge/settings/new/",
        {
            "provider": "openai",
            "api_key": "sk-test",
            "default_model": "",
        },
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Model mặc định là bắt buộc" in content


# ---------------------------------------------------------------------------
# Sidebar Settings link
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sidebar_has_settings_link(perm_client):
    """Sidebar includes a link to the AI config settings page."""
    response = perm_client.get("/modern/knowledge/")
    content = response.content.decode("utf-8")
    assert "Cấu hình AI" in content
    assert "/modern/knowledge/settings/" in content
