# PKM (Personal Knowledge Management) Module — Deep Investigation

> **Path:** `apps/pkm/`
> **App config:** `apps/pkm/apps.py` — `PKMConfig` (`name = "apps.pkm"`, `verbose_name = "Personal Knowledge Management"`)
> **Purpose:** Per-user RAG (Retrieval-Augmented Generation) knowledge base. Upload documents, chunk + embed them, ask questions answered from those documents and personal notes. Multi-provider LLM support (OpenAI, Anthropic, Gemini, Groq, OpenRouter, Ollama) with per-user encrypted API keys. Passive interaction logging feeds a "smart context" summary that personalises Q&A prompts.
> **Multi-tenancy:** All models extend `CompanyOwnedModel` (FK to `core.company`) and filter by `(user_id, company_id)`.
> **Permissions:** 4 codes registered via `apps/identity/migrations/0004_pkm_permissions.py`: `pkm.access`, `pkm.notes.manage`, `pkm.documents.manage`, `pkm.qa.use`. Granted to `admin` and `chief_accountant` roles. Enforced by `apps.identity.middleware.ModulePermissionMiddleware` on the `/modern/knowledge/` URL prefix.
> **DB engine:** MariaDB with native `VECTOR(1536)` type + HNSW vector index for cosine similarity search.

---

## 1. Models (`apps/pkm/models/`)

Eight models total (see `__init__.py`). All user-scoped models extend `apps.core.managers.CompanyOwnedModel` (abstract base providing the `company` FK).

### 1.1 `Tag` (`models/tag.py`, table `pkm_tag`)
User-specific tag for classifying notes. Unique per (user, company, name).

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_tags"`, CASCADE |
| `company` | FK → `core.company` | (from `CompanyOwnedModel`) CASCADE |
| `name` | CharField(100) | |
| `color` | CharField(20), blank | |
| `created_at` / `updated_at` | DateTimeField | auto |

- **Constraints:** `UniqueConstraint("user","company","name")` named `unique_tag_user_company_name`.
- **Indexes:** `(user, company)`. Ordering: `name`.

### 1.2 `KnowledgeNote` (`models/knowledge_note.py`, table `pkm_knowledge_note`)
Personal markdown note with optional tags and role-context filtering.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_notes"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `title` | CharField(255) | |
| `content` | TextField, blank | Markdown source |
| `tags` | M2M → `pkm.Tag` | `related_name="notes"`, blank |
| `role_context` | CharField(100), blank | Role code for filtering (e.g. `accountant`) |
| `is_pinned` | BooleanField, default False | |
| `created_at` / `updated_at` | DateTimeField | auto |

- **Indexes:** `(user, company)`, `(user, company, is_pinned)`. Ordering: `(-is_pinned, -updated_at)`.

### 1.3 `UserLLMConfig` (`models/user_llm_config.py`, table `pkm_user_llm_config`)
Per-user LLM provider configuration with Fernet-encrypted API key.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_llm_configs"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `provider` | CharField(20) | Choices: `openai`, `anthropic`, `gemini`, `groq`, `openrouter`, `ollama` |
| `api_key_encrypted` | TextField, blank | Fernet token (never plaintext) |
| `api_base` | URLField, blank | Custom endpoint for self-hosted/Ollama |
| `default_model` | CharField(100) | Required |
| `default_embedding_model` | CharField(100), blank | |
| `is_active` | BooleanField, default False | |
| `created_at` / `updated_at` | DateTimeField | auto |

- **Constraints:** `UniqueConstraint("user","company","provider")` named `unique_llm_config_user_company_provider`.
- **Indexes:** `(user, company)`, `(user, company, is_active)`. Ordering: `-updated_at`.

### 1.4 `PKMDocument` (`models/document.py`, table `pkm_document`)
Source document uploaded by a user for RAG processing.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_documents"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `title` | CharField(255) | |
| `file` | FileField | `upload_to="pkm/docs/%Y/%m/"` |
| `file_type` | CharField(20) | Extension: pdf/docx/txt/md/xlsx |
| `file_size` | PositiveIntegerField | bytes |
| `status` | CharField(20) | Choices: `pending`/`processing`/`processed`/`failed`; default `pending` |
| `checksum` | CharField(64), blank | SHA-256 for dedup |
| `error_message` | TextField, blank | Populated on failure |
| `created_at` / `updated_at` | DateTimeField | auto |

- **Indexes:** `(user, company)`, `(user, company, status)`, `(checksum)`. Ordering: `-created_at`.

### 1.5 `DocumentChunk` (`models/document_chunk.py`, table `pkm_documentchunk`)
Text chunk produced by splitting a `PKMDocument`. **Note:** does NOT extend `CompanyOwnedModel` (no `company` FK); tenant scoping is via the parent document.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `document` | FK → `pkm.PKMDocument` | `related_name="chunks"`, CASCADE |
| `chunk_index` | IntegerField | 0-based ordinal |
| `content` | TextField | Extracted text |
| `token_count` | IntegerField, default 0 | tiktoken count |
| `created_at` | DateTimeField | auto |

- **Indexes:** `(document)`, `(document, chunk_index)`. Ordering: `(document, chunk_index)`.

### 1.6 `Embedding` (`models/embedding.py`, table `pkm_embedding`)
Vector embedding for a `DocumentChunk`, stored in MariaDB `VECTOR(1536)`.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `chunk` | FK → `pkm.DocumentChunk` | `related_name="embeddings"`, CASCADE |
| `user` | FK → `identity.User` | `related_name="pkm_embeddings"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `content` | TextField, blank | Cached embedded text |
| `model_name` | CharField(100) | e.g. `text-embedding-3-small` |
| `embedding` | `VectorField(dimensions=1536)` | Custom field; raw SQL only (see §9) |
| `created_at` | DateTimeField | auto |

- **Indexes:** `(user, company)`, `(chunk)`. Ordering: `-created_at`.
- **Vector index:** HNSW `VECTOR INDEX pkm_embedding_vec_idx ... M=8 DISTANCE=cosine` created via raw SQL in migration `0002`.

### 1.7 `QAHistory` (`models/qa_history.py`, table `pkm_qa_history`)
Persisted Q&A interaction.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_qa_history"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `question` | TextField | |
| `answer` | TextField, blank | |
| `sources` | JSONField, default `list` | Source citations |
| `context_used` | JSONField, default `list` | Context chunks/notes used |
| `interaction_context` | TextField, blank | Recent-activity summary from `interaction_service` |
| `created_at` | DateTimeField | auto |

- **Indexes:** `(user, company)`, `(user, company, -created_at)`. Ordering: `-created_at`.

### 1.8 `UserInteractionLog` (`models/interaction_log.py`, table `pkm_user_interaction_log`)
Passive user-behaviour capture used by the smart-context feature.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField PK | |
| `user` | FK → `identity.User` | `related_name="pkm_interaction_logs"`, CASCADE |
| `company` | FK → `core.company` | CASCADE |
| `interaction_type` | CharField(20) | Choices: `page_view`/`search`/`note_create`/`document_create`/`voucher_create` |
| `module` | CharField(50) | Source module (e.g. `pkm`, `ledger`) |
| `entity_type` | CharField(100), blank | e.g. `note`, `document`, `voucher` |
| `entity_id` | CharField(100), blank | String identifier |
| `metadata` | JSONField, default `dict` | Free-form (search query, URL, etc.) |
| `created_at` | DateTimeField | auto |

- **Indexes:** `(user, company)`, `(user, company, -created_at)`. Ordering: `-created_at`.

### Cross-app FK summary
- All user FKs → `identity.User`.
- All `company` FKs → `core.company`.
- **No FKs from PKM models to ledger/sales/purchasing/inventory/hr/assets/reporting.** PKM is fully self-contained.
- The `interaction_type` enum includes `voucher_create` and `module` field allow logging events from other apps, but **no other app currently emits these** (see §8).

---

## 2. Services (`apps/pkm/services/`)

Nine service modules. No service imports Django request objects; they accept model instances or IDs (serialisable for django-q2 tasks).

### 2.1 `chunking_service.py` — Text chunking
- `split_text(text, chunk_size=1000, chunk_overlap=200) -> list[str]`: Uses `langchain_text_splitters.RecursiveCharacterTextSplitter` with separators `["\n\n", "\n", ". ", " ", ""]`, `keep_separator=True`. Validates `chunk_size > 0`, `chunk_overlap >= 0`, `chunk_overlap < chunk_size`.
- `count_tokens(text, model="gpt-4o") -> int`: Uses `tiktoken` (`encoding_for_model`, fallback `cl100k_base`). Encoding cached via `lru_cache(32)`.
- Constants: `DEFAULT_CHUNK_SIZE=1000`, `DEFAULT_CHUNK_OVERLAP=200`, `DEFAULT_MODEL="gpt-4o"`.
- Pure functions; no DB access.

### 2.2 `doc_parser.py` — Document text extraction
- `extract_text(file_path) -> str`: Dispatches by extension.
- Supported: `pdf` (pypdf), `docx` (python-docx), `txt`/`md` (UTF-8 with fallbacks utf-8-sig, latin-1), `xlsx` (openpyxl, tab-joined cells).
- Raises `ValueError` for unsupported extensions, `FileNotFoundError` if missing.

### 2.3 `encryption_service.py` — Fernet API-key encryption
- `encrypt(plaintext: str) -> str` / `decrypt(ciphertext: str) -> str`.
- Derives a Fernet key from `settings.SECRET_KEY` via `PBKDF2HMAC(SHA256, 600_000 iterations, 32-byte output)` with fixed salt `sha256(b"visota.pkm.encryption.v1")`. Key cached per-process (`lru_cache(1)`).
- Re-exports `InvalidToken` from `cryptography.fernet` so callers can catch integrity failures.

### 2.4 `interaction_service.py` — Interaction logging + smart-context summary
- `log_interaction(user, company, interaction_type, module, entity_type=None, entity_id=None, metadata=None) -> UserInteractionLog | None`:
  - Prefers async via django-q2 (`async_task` → `_create_sync`) when `_django_q_available()` returns True.
  - `_django_q_available()` returns True if `Q_CLUSTER["sync"]` is True, OR if there is evidence of a live worker (`Success` or `Task` rows exist in django-q's tables). This avoids silent enqueue-then-never-run in dev.
  - Falls back to synchronous `_create_sync` (which itself never raises — logs and returns `None`).
  - **Non-blocking by contract (VAL-CAP-009):** all exceptions are swallowed.
- `_create_sync(user_id, company_id, ...)`: Resolves `User`/`Company` by PK (serialisable for the broker), creates the `UserInteractionLog` row.
- `get_recent_interactions(user, company, limit=20)`: Queryset of recent logs, scoped.
- `get_context_summary(user, company, hours=24) -> str`: Aggregates interactions in the window by type, produces a human-readable Vietnamese summary, e.g. `"Recently: viewed 3 ledger pages, created 2 notes."`. Module-specific labels for page views (`ledger`, `pkm`, `sales`, `purchasing`, `inventory`, `hr`, `reporting`).
- Constants: `DEFAULT_SUMMARY_HOURS=24`, `DEFAULT_RECENT_LIMIT=20`.

### 2.5 `llm_service.py` — Multi-provider LLM wrapper (LiteLLM)
- `get_completion(user_config, messages, stream=False)`: Calls `litellm.completion` with the decrypted API key passed **per call** (never stored in env). Model formatted as `provider/model`.
- `get_embedding(user_config, texts, model=None)`: Calls `litellm.embedding`. Uses `user_config.default_embedding_model` unless overridden.
- `get_available_providers() -> list[str]`: `["openai","anthropic","gemini","groq","openrouter","ollama"]`.
- `get_provider_models(provider) -> list[str]`: Curated suggested-models list per provider (see `_PROVIDER_MODELS` dict).
- `validate_api_key(provider, api_key, api_base=None) -> bool`: Minimal test call (`max_tokens=1`) using `_VALIDATION_MODELS` (cheapest model per provider).
- Exception hierarchy: `LLMError` (base) → `LLMAuthError` (401), `LLMRateLimitError` (429), `LLMTimeoutError` (504). Translates litellm's `AuthenticationError`/`RateLimitError`/`Timeout`/`APIConnectionError`.

### 2.6 `qa_service.py` — RAG Q&A orchestration
- `answer_question(user, company, question, *, top_k=5, note_limit=5) -> dict`:
  Pipeline:
  1. Resolve active `UserLLMConfig` (raises `ValueError` if none).
  2. Embed question via `llm_service.get_embedding`.
  3. `vector_store.search_similar(user_id, company_id, vector, top_k)` — cosine search scoped to user+company.
  4. `_search_notes`: keyword (icontains) search of `KnowledgeNote` by question terms.
  5. `_enrich_chunks_with_titles`: batch-resolve chunk → document title.
  6. Fetch `interaction_service.get_context_summary` for smart-context enrichment.
  7. `build_prompt(chunks, notes, question, interaction_context)` → OpenAI chat messages with a Vietnamese system message instructing the LLM to answer from context and cite sources.
  8. `llm_service.get_completion`.
  9. Collect sources (chunk_id, document_title, preview, distance) and persist `QAHistory` (including `interaction_context`).
  - Returns `{answer, sources, context_used, interaction_context}`.
- `build_prompt(...)`: Constructs `[{system, SYSTEM_MESSAGE}, {user, "NGU CANH ... CAU HOI ..."}]`. `SYSTEM_MESSAGE` instructs the assistant (in Vietnamese, ASCII-folded) to answer based on the provided context, cite sources, and reply in Vietnamese.
- `save_qa_history(...)`: Persists the Q&A record.
- Constants: `DEFAULT_TOP_K=5`, `DEFAULT_NOTE_SEARCH_LIMIT=5`, `PREVIEW_LENGTH=200`.

### 2.7 `rag_pipeline.py` — End-to-end document processing
- `process_document(document_id)`: Designed as a django-q2 task.
  1. Set `PKMDocument.status = processing`.
  2. `doc_parser.extract_text(file.path)`.
  3. `chunking_service.split_text(text, chunk_size=1000, chunk_overlap=200)`.
  4. Resolve active `UserLLMConfig` for embedding (raises if none).
  5. `llm_service.get_embedding(config, chunks, model=embed_model)`.
  6. `_store_chunks_and_embeddings`: per chunk, ORM-create `DocumentChunk` then `vector_store.store_embedding` (raw SQL).
  7. Set status `processed`.
  - On any error: set status `failed` with `error_message[:5000]`, re-raise (so django-q2 can retry).
- `reprocess_document(document_id)`: Delete old chunks/embeddings then re-run.
- `delete_document_data(document_id) -> int`: `vector_store.delete_embeddings` (raw SQL) then ORM-delete chunks.
- `schedule_document_processing(document_id)` / `schedule_reprocessing(document_id)`: `async_task` with `timeout=300`. (`max_attempts=3` is cluster-level.)
- Constants: `DEFAULT_CHUNK_SIZE=1000`, `DEFAULT_CHUNK_OVERLAP=200`, `TASK_TIMEOUT=300`, `TASK_MAX_ATTEMPTS=3`.

### 2.8 `vector_store.py` — MariaDB VECTOR operations (raw SQL)
- `store_embedding(chunk_id, user_id, company_id, content, embedding_vector, model_name) -> int`: INSERT with `VEC_FromText(%s)` for the vector. Returns `lastrowid`.
- `search_similar(user_id, company_id, query_embedding, top_k=10) -> list[dict]`: SELECT with `VEC_DISTANCE_COSINE` in `ORDER BY` (uses the HNSW index), filtered by `user_id` + `company_id`. Returns `[{id, content, chunk_id, distance}]`.
- `delete_embeddings(document_id=None, chunk_id=None) -> int`: DELETE via raw SQL.
- `EMBEDDING_DIMENSIONS = 1536`.
- All operations use `django.db.connection.cursor()` directly because the ORM cannot express `VECTOR(1536)`.

---

## 3. API (`apps/pkm/api.py`) — django-ninja Router

Registered in `apps/core/api.py` as `api.add_router("/pkm/", pkm_router)` under the `/api/v1/` NinjaAPI. All endpoints use `auth=get_current_user`. Multi-tenant scoping via `get_current_company(request)`.

### Notes
| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/pkm/notes/` | Create note (title, content, role_context, is_pinned, tag_ids) |
| GET | `/api/v1/pkm/notes/` | List notes — `?search=`, `?tag=` (paginated) |
| POST | `/api/v1/pkm/notes/search/` | Search notes by keyword (logs `search` interaction) |
| GET | `/api/v1/pkm/notes/{id}/` | Note detail |
| PUT | `/api/v1/pkm/notes/{id}/` | Update note |
| DELETE | `/api/v1/pkm/notes/{id}/` | Delete note |

### LLM Configs
| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/pkm/llm-configs/` | List user's configs (never exposes the key; `has_key` bool only) |
| POST | `/api/v1/pkm/llm-configs/` | Create config (api_key encrypted before save) |
| POST | `/api/v1/pkm/llm-configs/validate/` | Validate API key via minimal test call (never stored) |
| PUT | `/api/v1/pkm/llm-configs/{id}/` | Update config |
| DELETE | `/api/v1/pkm/llm-configs/{id}/` | Delete config |
| GET | `/api/v1/pkm/providers/` | List providers + suggested models |

### Documents
| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/pkm/documents/` | Multipart upload — validates type/size, computes SHA-256 checksum (dedup warning if exists), creates `pending` record, enqueues RAG pipeline |
| GET | `/api/v1/pkm/documents/` | List (`?status=`) |
| GET | `/api/v1/pkm/documents/{id}/` | Detail (includes `file_url`, `has_file`) |
| DELETE | `/api/v1/pkm/documents/{id}/` | Delete file + chunks + embeddings + record |
| POST | `/api/v1/pkm/documents/{id}/reprocess/` | Reset to `pending`, enqueue reprocess |
| GET | `/api/v1/pkm/documents/{id}/status/` | Lightweight status (id, status, error_message) |

- `MAX_FILE_SIZE = 20 * 1024 * 1024` (20 MB).
- `ALLOWED_FILE_TYPES = {"pdf","docx","txt","md","xlsx"}`.

### Q&A
| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/pkm/qa/ask/` | RAG Q&A — requires active LLM config (400 if none). Maps LLM errors: Auth→401, RateLimit→429, Timeout→504, other LLM→502. Returns `{answer, sources, context_used, interaction_context, context_used_indicator}` |
| GET | `/api/v1/pkm/qa/history/` | Paginated Q&A history |

### Stats
| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/pkm/stats/` | Aggregate counts: notes, docs, doc_status_counts, qa_count, tags, llm_configs, has_active_config, pinned_notes, role_suggestions_count (notes whose `role_context` matches the user's `UserCompanyRole.role__code` set in the current company), `user_role_codes` |

---

## 4. Signals (`apps/pkm/signals.py`)

Two `post_save` receivers registered via `apps.py:PKMConfig.ready()` which imports `signals` for side effects.

| Signal | Sender | Handler | Behaviour |
|---|---|---|---|
| `post_save` | `KnowledgeNote` | `log_note_create` | On `created=True`: calls `log_interaction(interaction_type="note_create", module="pkm", entity_type="note", entity_id=str(pk), metadata={"title": title})`. Wrapped in `try/except` — non-blocking. |
| `post_save` | `PKMDocument` | `log_document_create` | On `created=True`: calls `log_interaction(interaction_type="document_create", module="pkm", entity_type="document", entity_id=str(pk), metadata={"title","file_type","file_size"})`. Non-blocking. |

- **Only fire on creation** (not updates) to avoid duplicate logs.
- **No signals listen to other apps.** There is no `voucher_create` receiver wired to `ledger.Voucher` or any other cross-app sender. The `voucher_create` interaction type is defined in the enum but **not currently emitted anywhere in the codebase** (see §8).

---

## 5. Views (`apps/ui_modern/views/pkm_views.py`)

All views require `LoginRequiredMixin` (`login_url="/auth/login/"`). The `pkm.access` permission is enforced at the middleware layer (`ModulePermissionMiddleware` maps `/modern/knowledge/` → `pkm`). All queries scoped by `request.user` + `request.current_company`.

| View | Type | Purpose |
|---|---|---|
| `PKMDashboardView` | View (GET) | Stats cards, recent activity feed (`UserInteractionLog`), pinned notes, role-based knowledge suggestions (notes whose `role_context` ∈ user's role codes) |
| `KnowledgeNoteListView` | ListView (paginate 10) | Pinned-first, search + tag filter |
| `KnowledgeNoteDetailView` | DetailView | Single note with markdown rendered via `markdown` lib (extensions: extra, codehilite, toc) |
| `KnowledgeNoteCreateView` / `KnowledgeNoteUpdateView` | View (GET/POST) | Plain form (no ModelForm) — tags selected by name from the user's tag set |
| `KnowledgeNoteDeleteView` | DeleteView | Confirmation page → `pkm_note_list` |
| `PKMSearchView` | View (GET) | Unified note search (`?q=`), logs `search` interaction |
| `LLMConfigListView` / `CreateView` / `UpdateView` / `DeleteView` | View/DeleteView | Manage provider configs; API key encrypted before save; edit form never pre-fills the decrypted key |
| `DocumentListView` | ListView (paginate 10) | Status badges; HTMX polling (`_DOC_POLL_INTERVAL_MS=3000`) for pending/processing |
| `DocumentUploadView` | View (GET/POST) | Drag-drop upload, validates `_ALLOWED_DOC_TYPES={"pdf","docx","txt","md","xlsx"}` and `_MAX_DOC_FILE_SIZE=20MB`, enqueues `rag_pipeline.schedule_document_processing` |
| `DocumentDetailView` | DetailView | Status, chunk count, reprocess button for failed docs |
| `DocumentDeleteView` | DeleteView | Removes chunks/embeddings/file/record |
| `DocumentStatusBadgeView` | View (GET) | HTMX partial `_document_status_badge.html`. Sets `HX-Trigger: status-updated` when terminal. |
| `DocumentReprocessView` | View (POST) | Reset to `pending`, enqueue reprocessing |
| `QAChatView` | View (GET/POST) | Q&A chat UI. GET shows last 20 history entries; POST calls `qa_service.answer_question`. Requires active config. |

Helpers: `_get_notes_qs`, `_get_tags_qs`, `_get_llm_configs_qs`, `_get_documents_qs`, `_get_qa_history_qs`, `_get_interaction_logs_qs`, `_get_user_role_codes`, `_log_search`, `render_markdown`, `_status_badge_class`, `_status_label`.

---

## 6. Templates (`templates/modern/pkm/`)

15 templates:
- `base_pkm.html` — extends `modern/base/layout.html`; loads `dexie.min.js` + `pkm-cache.js` (IndexedDB client cache).
- `dashboard.html` — dashboard.
- `note_list.html`, `note_form.html`, `note_detail.html`, `note_confirm_delete.html`.
- `llm_config_list.html`, `llm_config_form.html`, `llm_config_confirm_delete.html`.
- `document_list.html`, `document_upload.html`, `document_detail.html`, `document_confirm_delete.html`.
- `_document_status_badge.html` — HTMX partial.
- `qa_chat.html` — Q&A chat.

Client-side: `static/modern/js/pkm-cache.js` uses Dexie (IndexedDB) with stores `drafts`, `qa_history`, `cached_results`, and an outbox for background sync. `static/sw.js` (service worker, verified by tests) precaches PKM static assets, uses `staleWhileRevalidate` for `/modern/knowledge/`, `cacheFirst` for static assets, has offline fallback to `/offline/`, and a background-sync handler (`pkm-draft-sync` tag) that queues/replays POSTs to `/api/v1/pkm/notes`.

---

## 7. Middleware / Passive Capture (`apps/pkm/middleware.py`)

### `PKMInteractionMiddleware`
Registered in `config/settings/base.py` `MIDDLEWARE` (after `ModulePermissionMiddleware`).

- Logs a `page_view` interaction for every successful (2xx) GET response to URLs starting with `PKM_URL_PREFIX = "/modern/knowledge/"`.
- Conditions: `request.method == "GET"` AND `user.is_authenticated` AND path starts with prefix AND `200 <= status_code < 300` AND `request.current_company` is set.
- Calls `log_interaction(interaction_type="page_view", module="pkm", entity_type="page", entity_id=request.path, metadata={"url", "method"})`.
- **Non-blocking:** all exceptions swallowed (VAL-CAP-009).

### Cross-module capture?
**No.** The middleware only watches `/modern/knowledge/` URLs. There is **no** equivalent middleware logging page views, searches, or document/voucher creation in `ledger`, `sales`, `purchasing`, `inventory`, `hr`, `assets`, or `reporting`. The `voucher_create` interaction type and `module` field exist to support cross-module logging, but **no other app currently emits these events** (see §8).

---

## 8. Cross-module Integration Points

### Imports of PKM from other apps (`from apps.pkm` / `import pkm`)
| File | Usage |
|---|---|
| `apps/core/api.py` | Mounts `pkm_router` at `/api/v1/pkm/` |
| `apps/ui_modern/views/pkm_views.py` | All PKM views (the PKM UI layer) |
| `apps/identity/migrations/0004_pkm_permissions.py` | Registers the 4 PKM permission codes and grants them to `admin`/`chief_accountant` roles |
| `apps/identity/middleware.py` | Maps URL prefix `/modern/knowledge/` → permission module `pkm` |

### `pkm.access` permission usage
Enforced generically by `ModulePermissionMiddleware` (maps the `/modern/knowledge/` prefix to module `pkm`). No view-level `@permission_required("pkm.access")` decorators — reliance is on the middleware.

### Does any other module send data to PKM or consume PKM data?
**No.** Grep for `from apps.pkm` / `import pkm` / `log_interaction` / `UserInteractionLog` / `interaction_service` returns matches **only** inside `apps/pkm/`, `apps/ui_modern/views/pkm_views.py`, `apps/core/api.py` (router mount), and `apps/identity` (permission migration + middleware URL map). **No ledger/sales/purchasing/inventory/hr/assets/reporting module references PKM.**

### Direction of data flow
- **PKM → other modules:** None. PKM does not write to or query other apps' models (except the foundational `core.company` and `identity.User` / `identity.UserCompanyRole`).
- **Other modules → PKM:** None currently wired. The `UserInteractionLog` schema and `interaction_service.log_interaction` are designed to accept any `module` string and the `voucher_create` type is defined, but no other app calls `log_interaction`. The only emitters are PKM's own middleware, signals, and views (for `page_view`, `search`, `note_create`, `document_create`).

---

## 9. Vector Storage

- **Engine:** MariaDB native `VECTOR(1536)` column type.
- **Table:** `pkm_embedding` (model `Embedding`).
- **Field:** `embedding` — `apps/pkm/fields.VectorField(dimensions=1536)`. `db_type()` returns `VECTOR(1536)`. `editable=False`, `default=None`. The ORM cannot read/write the vector; it exists for schema/migration awareness.
- **Index:** HNSW vector index, created by raw SQL in migration `0002_document_models.py`:
  ```sql
  CREATE VECTOR INDEX pkm_embedding_vec_idx
    ON pkm_embedding (embedding) M=8 DISTANCE=cosine;
  ```
- **Writes:** `vector_store.store_embedding` — raw `INSERT ... VALUES (?, ?, ?, ?, VEC_FromText(?), ?, NOW())`. Vector serialised with `json.dumps(list[float])`.
- **Search:** `vector_store.search_similar` — raw `SELECT id, content, chunk_id, VEC_DISTANCE_COSINE(embedding, VEC_FromText(?)) AS distance ... ORDER BY VEC_DISTANCE_COSINE(...) LIMIT ?`. Filtered by `user_id` + `company_id`. The bare `ORDER BY` form is used so MariaDB chooses the HNSW index.
- **Deletes:** `vector_store.delete_embeddings` — raw `DELETE`.
- **Dimension:** Fixed at 1536 (matches OpenAI `text-embedding-3-small/large`). The `Embedding.model_name` column records which model produced each row.

---

## 10. Management Commands

**None.** `apps/pkm/` has no `management/` directory and no management commands. The RAG pipeline is triggered exclusively via:
- The upload API/UI (which calls `rag_pipeline.schedule_document_processing`).
- The reprocess API/UI action (`rag_pipeline.schedule_reprocessing`).
Both enqueue `django_q.tasks.async_task` tasks (`process_document` / `reprocess_document`).

---

## Additional Notes

### Django settings integration (`config/settings/base.py`)
- `INSTALLED_APPS` includes `apps.pkm`.
- `MIDDLEWARE` includes `apps.pkm.middleware.PKMInteractionMiddleware` (last, after `ModulePermissionMiddleware`).
- `django-q2` (`django-q2>=1.9`, pinned `==1.10.0`) provides the async task broker for `log_interaction` and the RAG pipeline. `Q_CLUSTER["sync"]=True` makes tasks run inline in tests/dev.

### Dependencies (`requirements.txt`)
`litellm>=1.40`, `tiktoken>=0.7`, `langchain-text-splitters>=0.3`, `pypdf>=4.0`, `python-docx>=1.1`, `openpyxl>=3.1`, `cryptography>=43.0`, `markdown>=3.5`, `django-q2>=1.9`.

### Migrations (`apps/pkm/migrations/`)
- `0001_initial` — `Tag`, `KnowledgeNote`, `UserLLMConfig` + indexes/constraints.
- `0002_document_models` — `PKMDocument`, `DocumentChunk`, `Embedding` (with `VectorField`), indexes, and the raw-SQL HNSW vector index.
- `0003_qa_history_model` — `QAHistory`.
- `0004_userinteractionlog` — `UserInteractionLog`.
- `0005_qa_history_interaction_context` — adds `QAHistory.interaction_context` (smart-context summary field).

### Admin
`apps/pkm/admin.py` is essentially empty (32 bytes) — no model registration.

### Test coverage
~30 test files in `tests/` plus 3 E2E tests in `tests/e2e/`, covering: models, encryption, chunking, doc parser, vector store, RAG pipeline, LLM service, Q&A service + API + UI, notes API + UI, documents API + UI, LLM config API + UI, interaction service + middleware + log + sync fallback, smart-context integration, dashboard stats, cross-area (multi-user/multi-tenant isolation, provider switching, reprocess), permissions, service worker, note autosave, QA history cache.
