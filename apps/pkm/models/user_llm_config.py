"""UserLLMConfig model for per-user LLM provider configuration."""

from django.db import models

from apps.core.managers import CompanyOwnedModel


class UserLLMConfig(CompanyOwnedModel):
    """Per-user LLM provider configuration with encrypted API keys.

    Stores Fernet-encrypted API keys for each supported provider.
    Unique per (user, company, provider) so each user can have one config
    per provider within a company.
    """

    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GEMINI = "gemini", "Google Gemini"
        GROQ = "groq", "Groq"
        OPENROUTER = "openrouter", "OpenRouter"
        OLLAMA = "ollama", "Ollama"

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="pkm_llm_configs",
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
    )
    api_key_encrypted = models.TextField(
        blank=True,
        default="",
        help_text="Fernet-encrypted API key (never store plaintext)",
    )
    api_base = models.URLField(
        blank=True,
        default="",
        help_text="Custom API base URL for self-hosted or compatible endpoints",
    )
    default_model = models.CharField(max_length=100)
    default_embedding_model = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=False)
    disable_masking = models.BooleanField(
        default=False,
        help_text=(
            "When True, PII data (MST, VND amounts, phone, email) is NOT masked "
            "before LLM calls. Useful for local Ollama models where data never "
            "leaves the machine. Default False = mask everything (secure)."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = "pkm_user_llm_config"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company", "provider"],
                name="unique_llm_config_user_company_provider",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "company", "is_active"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.provider}"
