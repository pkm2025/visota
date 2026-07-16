# PKM Sensitive Data Handling Analysis

Scope: PKM (Personal Knowledge Management) module at `apps/pkm/` and its UI
surface at `apps/ui_modern/views/pkm_views.py`,
`apps/ui_modern/urls.py`, and `templates/modern/pkm/`.

Investigation date: 2026-07-17
Investigator: worker subagent (parent task)
Repo: C:\mmm\visota @ main

---

## TL;DR

1. **Sensitive data leakage to LLMs is real and unmitigated.** The Q&A
   pipeline forwards raw user note content, raw uploaded-document chunks,
   the user's accounting regime, tax-method group, entity type, industry,
   and (for business events) voucher numbers and VND amounts into the
   LLM prompt. None of this is masked, redacted, or sanitised before the
   call to LiteLLM. (`apps/pkm/services/qa_service.py`,
   `apps/pkm/services/interaction_service.py`,
   `apps/pkm/services/vector_store.py`)
2. **No PII masking exists in the PKM path.** `apps/core/logging_utils.py`
   has a `scrub_value`/`StructuredJSONFormatter` that masks emails,
   phone numbers, and 9-12 digit numbers (tax IDs) **in structured logs
   only**. The QA service and LLM call path bypass this formatter entirely
   (they call `litellm.completion` directly, not `logger.info`), so the
   scrubbing never runs. There is no middleware or service that strips
   sensitive data before external calls.
3. **Markdown is overkill for an ERP note feature.** It is rendered with
   the full `extra + codehilite + toc` extension set on the read path,
   but the editor is a plain `<textarea>` with no live preview, no
   toolbar, and no schema constraint on content. The rendered HTML is
   injected via `|safe` (XSS surface). For Vietnamese accountants, plain
   text or a structured `title + body` would be simpler and safer.
4. **No retention, archive, or purge mechanism exists for any PKM data.**
   `QAHistory`, `UserInteractionLog`, `KnowledgeNote`, `PKMDocument`,
   `DocumentChunk`, and `pkm_embedding` rows accumulate indefinitely.
   No management command, no cron, no Celery/q beat, no `cleanup_*`
   task. The only deletion paths are interactive single-record deletes.
5. **No export or backup mechanism for PKM data.** Other modules have
   xlsx/docx/PDF export views; PKM has none. There is no
   `pkm_export_note`, `pkm_backup`, `qa_history_export`, or anything
   similar. Users cannot bulk-export their notes or Q&A history.

---

## Part 1: Sensitive Data Exposure to LLM

### Pipeline trace

`apps/pkm/services/qa_service.py::answer_question` constructs the prompt:

```
1. llm_config = _resolve_llm_config(user, company)           # picks provider
2. embed_response = get_embedding(llm_config, [question])    # LLM call #1
3. raw_chunks = search_similar(...)                          # vector search
4. notes = _search_notes(user, company, question)            # keyword search
5. interaction_context = get_context_summary(user, company)  # build summary
6. messages = build_prompt(chunks, notes, question, ctx)     # assemble prompt
7. response = get_completion(llm_config, messages)           # LLM call #2
```

Two external calls per Q&A: one embedding call (`litellm.embedding`) and
one completion call (`litellm.completion`). Both go to whatever provider
the user configured (OpenAI, Anthropic, Google, Groq, OpenRouter, Ollama).

### 1a. System prompt content (`SYSTEM_MESSAGE`)

File: `apps/pkm/services/qa_service.py`, constant `SYSTEM_MESSAGE`.

It is a **static Vietnamese string** instructing the model to act as a
"trợ lý kế toán ERP Visota" grounded on Vietnamese law and the user's
"bối cảnh doanh nghiệp" (company context). It is the same for every user.

It does **not** embed user data itself, but it explicitly tells the model
to look for the `HOAT DONG NGUOI DUNG GAU DAY` section and the
**bối cảnh doanh nghiệp** in the user message (see 1c below).

Sensitive-data verdict: **none directly in SYSTEM_MESSAGE**. It is
template text, no interpolation.

### 1b. User message content

Built in `_build_context_string` + `build_prompt`:

```
NGU CANH (Context):
=== HOAT DONG NGUOI DUNG GAU DAY (Recent user activity) ===
<interaction_context>                      <- see 1c

=== TAI LIEU / DOANH VAN BAN ===
[Doan 1] (Nguon: <doc title>) <chunk text>     <- raw chunk content
[Doan 2] (Nguon: <doc title>) <chunk text>
...

=== GHI CHU CA NHAN ===
[Ghi chu 1] (Tieu de: <note title>) <note.content[:200]>   <- raw note text
...

CAU HOI:
<question>

Vui long tra loi cau hoi dua tren ngu canh tren. Trich dan nguon.
```

The prompt contains, in plaintext Vietnamese with no redaction:

| Field                   | Source                                                  | Could carry PII / financial data? |
|-------------------------|---------------------------------------------------------|-----------------------------------|
| `<interaction_context>` | `interaction_service.get_context_summary` (see 1c)     | YES - amounts, voucher IDs, role, regime, industry |
| `<doc title>`           | `PKMDocument.title`                                     | YES - user-supplied, e.g. "Hợp đồng Viettel" |
| `<chunk text>`          | raw text extracted from user-uploaded PDF/DOCX/XLSX/TXT| YES - whatever the user uploaded: contracts, ledgers, payroll |
| `<note title>`          | `KnowledgeNote.title`                                   | YES |
| `<note.content[:200]>`  | first 200 chars of user note                            | YES - user can type tax codes, names, amounts |
| `<question>`            | user input                                              | YES |

### 1c. `get_context_summary()` - what gets leaked from "interaction context"

File: `apps/pkm/services/interaction_service.py`, function
`get_context_summary`.

Summary is assembled from:

- `_format_company_context(user, company)`:
  - `entity_type` (e.g. "Doanh nghiệp siêu nhỏ")
  - `accounting_regime` (TT133/2016, TT200/2014, TT58/2026, QĐ48/2006)
  - `tax_method_group` 1-4 (only for TT58) - which VAT + TNDN method
  - `vat_method` (Khấu trừ / Tỷ lệ %)
  - `tndn_method` (Tính thuế / Tỷ lệ %)
  - `industry` (free text - e.g. "Thương mại - Công nghệ")
  These are **configuration choices**, not raw PII, but they are
  business-confidential context (size, regime, tax strategy) sent to a
  third party on every Q&A.

- `_format_project_context(user, company)`:
  - `project.name` - user-supplied, could be confidential
  - `project.status`
  - `project.budget_revenue` - **rendered as VND amount** in the prompt
    (`Ngân sách doanh thu: 500.000.000 VND`)
  - `project.progress_percent`

- `_get_user_role_vn(user, company)`:
  - role name (e.g. "Kế toán viên")

- `_format_business_events_vn(events)`:
  - For each of the last 10 business events in the 24h window, includes
    the **verb + entity_id + amount**. Example rendered text:
    `hoạt động nghiệp vụ: lập phiếu kế toán BE-V01 (50.000.000 VND)`,
    `lập hóa đơn bán hàng ...`
  - **amounts come straight from the metadata dict**. The vouchers
    service writes `metadata={"amount": str(voucher.total_vnd)}`, the
    sales invoice service writes `metadata={"total_amount":
    str(invoice.total_amount)}`. These are real VND figures.
  - `entity_id` is the voucher number / invoice number - a business
    document identifier.

- `_format_page_views_vn` and `_format_content_actions_vn`:
  counts only ("xem 3 trang Kế toán", "tạo 2 ghi chú") - low risk.

**Conclusion for 1c**: amounts and document IDs are deliberately
forwarded to the LLM, as are company-confidential configuration (regime,
industry, tax method). No scrubbing.

### 1d. `vector_store.search_similar` - what chunks reach the prompt

File: `apps/pkm/services/vector_store.py`.

`search_similar` returns the literal `content` of each matching
`pkm_embedding` row. The content was produced by `chunking_service.split_text`
operating on the text extracted by `doc_parser.extract_text` from the
user's uploaded file (PDF/DOCX/XLSX/TXT/MD).

Therefore whatever the user uploaded - signed contracts (with party
names, MST tax codes, bank accounts, signatures), payroll XLSX (with
employee names and salaries), ledgers, supplier invoices - is fully
recovered as plaintext and fed into the prompt as `<chunk text>`. There
is no allow/deny list, no field selection, no regex filter, no size cap
beyond the chunker's `DEFAULT_CHUNK_SIZE = 1000` characters per chunk.

The 5 chunks returned (`DEFAULT_TOP_K = 5`) plus the system regulation
chunks (TT58, PIT rates, etc., `is_system=True`) all flow into the same
context block.

### 1e. Masking / redaction / sanitisation before LLM call

**None.** Searched `apps/pkm/**/*.py` for
`mask|redact|sanitize|scrub|PII|sensitive` - zero matches. The QA
pipeline does not import `apps.core.logging_utils` and does not call
`scrub_value` anywhere. The `_build_context_string` and `build_prompt`
functions concatenate raw fields.

The only "filter" in the pipeline is `_contains_accounting_keywords`
used to *boost* regulation chunks - it doesn't redact anything.

---

## Part 2: PII Masking Analysis

### Existing scrubbing infrastructure

`apps/core/logging_utils.py` defines:

```python
PII_PATTERNS = [
    (email regex,  "[EMAIL]"),
    (phone regex,  "[PHONE]"),
    (r"\b\d{9,12}\b", "[TAX_ID]"),     # 9-12 digit number
]
PII_KEYS = {"password","secret","token","api_key","apikey",
            "private_key","credit_card","card_number","cvv","ssn","tax_code"}

def scrub_value(val): ...
class StructuredJSONFormatter(logging.Formatter): ...
def configure_structured_logging(): ...
```

This is **only wired into the JSON log formatter**. It applies when a
record has the matching key (e.g. `record.password`) or when a string
field is being formatted as a log extra. It is **not** applied to:

- LLM message bodies (`messages` list passed to `litellm.completion`)
- LLM embedding inputs
- Stored `QAHistory.question`, `QAHistory.answer`,
  `QAHistory.interaction_context`, `QAHistory.sources`,
  `QAHistory.context_used`
- Stored `UserInteractionLog.metadata` JSON
- Vector store chunk content
- Note content / document text

### Coverage gaps in the existing scrubber

Even if it were applied, it would miss most of the actually sensitive
ERP data:

| Data class                     | Caught by current patterns?      |
|--------------------------------|----------------------------------|
| Email                          | yes                              |
| Vietnamese mobile (10 digits)  | yes (PHONE) and yes (TAX_ID, overlap) |
| MST / tax code (10-14 digits)  | partial - 9-12 digits only, no 13/14 |
| VND amounts                    | **no** (numbers under 9 digits)  |
| Customer / vendor / employee names | **no** (free text)           |
| Bank account numbers           | **no**                           |
| Citizen ID (CCCD, 12 digits)   | yes by TAX_ID (12 digits)        |
| Salary / payroll lines         | **no**                           |
| Invoice / voucher numbers      | **no** (alphanumeric)            |

### Middleware

`apps/pkm/middleware.py::PKMInteractionMiddleware` only logs
`page_view` interactions; it does **not** redact `request.path`. Other
interaction emitters in `apps/ledger/`, `apps/sales/`, `apps/einvoice/`
push `metadata={"amount": str(voucher.total_vnd)}` directly without
scrubbing.

### Conclusion for Part 2

- A scrubbing utility exists, but it is **logger-only**.
- No middleware or service strips sensitive data before any external call
  (LLM or otherwise).
- The PKM module is a direct, unmasked exfiltration path from ERP
  database to a third-party LLM provider.

---

## Part 3: Note Format Analysis

### Storage

File: `apps/pkm/models/knowledge_note.py`.

```python
title    = CharField(max_length=255)
content  = TextField(blank=True, default="", help_text="Markdown content")
```

The model stores raw markdown text. There is no separate "rendered HTML"
column; rendering happens on the fly at read time in
`pkm_views.render_markdown`.

### Rendering

`apps/ui_modern/views/pkm_views.py`:

```python
def render_markdown(text: str) -> str:
    extensions = ["extra", "codehilite", "toc"]
    return md_lib.markdown(text, extensions=extensions, output_format="html")
```

Used only in `KnowledgeNoteDetailView.get_context_data` as
`ctx["rendered_content"] = render_markdown(self.object.content)`.

Template `templates/modern/pkm/note_detail.html`:

```django
{% if rendered_content %}
{{ rendered_content|safe }}
{% else %}
<p class="text-muted">Ghi chú này chưa có nội dung.</p>
{% endif %}
```

The `|safe` filter disables Django autoescaping, so any HTML produced by
`markdown.markdown` is injected verbatim. The `markdown` library's
default output is not sanitised against XSS; combined with the `extra`
extension (which permits inline HTML and `abbr`, `def_list`, `fenced_code`,
`footnotes`, `tables`, `attr_list`, `md_in_html`), a malicious or
careless user can inject `<script>`, `<img onerror=...>`, etc.

(Note content is owner-only, so the attacker is mostly the user
themselves, but XSS still matters if a note is shared across roles via
`role_context`, or if a seeded role-template note contains injected
HTML - see `seed_pkm_templates`.)

### Editing UX

`templates/modern/pkm/note_form.html`:

- Plain `<textarea name="content" rows="12">`
- A hint line: *"Hỗ trợ Markdown: **đậm**, *nghiêng*, # tiêu đề, -
  danh sách, ```code```"*
- **No live preview**, **no toolbar**, **no keyboard shortcuts**, **no
  split-pane**.
- Client-side draft autosave via `window.PKMCache.saveDraft(...)` to
  IndexedDB (this is fine).

So the editor UX is identical to plain text, but the read side renders
markdown. There is no `codehilite` stylesheet loaded anywhere in the PKM
templates (no `pygments.css`, no `<link>` for syntax styles), so
`codehilite` produces `<div class="codehilite"><pre>` blocks with no
syntax colouring. It is effectively dead code that still adds CPU and a
hidden surface for HTML injection via fenced blocks.

`codehilite` requires **Pygments** to actually colour tokens; Pygments
is **not** in `requirements.txt`. The `codehilite` extension silently
falls back to plain `<pre>` when Pygments is missing. So the "syntax
highlighting" promise is unfulfilled.

### Is markdown necessary?

Arguments **against** markdown for this ERP:

1. **Audience mismatch.** The product targets Vietnamese accountants
   (per `AGENTS.md`: "Vietnamese for UI labels"). They are not the
   typical markdown-writing demographic. The hint line in the form is
   the only affordance.
2. **No editing tools.** A raw textarea asking non-technical users to
   remember `**bold**` syntax is poor UX.
3. **Hidden complexity.** `extra + codehilite + toc` are configured but
   the `toc` extension is never consumed (no `[TOC]` marker in
   templates, no Jinja-side use), `codehilite` cannot colour anything
   without Pygments.
4. **Security.** The `|safe` injection of `markdown(...)` output into
   the DOM is a standing XSS vector. Bleach / nh3 / Django's
   `safe_svg|strip_html_tags` is **not** applied.
5. **ERP data is structured.** A note about "khấu hao xe Honda" is
   really a title + body + tags + role_context. The schema already has
   those fields (`title`, `content`, `tags`, `role_context`). The free
   markdown body is the only unstructured part, and for it, plain text
   with `\n` line breaks (rendered via `|linebreaks` and autoescaped)
   would be safer, simpler, and equally readable.
6. **Q&A path doesn't benefit.** Notes are also fed to the LLM
   (`_search_notes` -> `_build_context_string`) as plain text; markdown
   punctuation is noise to the model.

Arguments **for** keeping markdown:

- Some power users may paste markdown from elsewhere (Confluence,
  GitHub). This is a weak argument in an accounting ERP.

**Verdict for Part 3:** Markdown is over-engineered for the actual UX
delivered. Either:

- (preferred) **Drop markdown**: store plain text, render with
  `{{ note.content|linebreaks }}` (autoescaped). Removes the XSS surface
  and the unused extension code paths.
- or **Commit to markdown properly**: add an editor (e.g. EasyMDE /
  Toast UI Editor), a live preview, a Bleach/nh3 sanitiser on save,
  Pygments + a stylesheet for `codehilite`, and a `[TOC]` marker in
  `note_detail.html` to make `toc` do something.

The current state is the worst of both worlds: markdown complexity on
the read side, plain-text UX on the write side, XSS exposure, and two
of the three configured extensions produce no visible effect.

---

## Part 4: Retention and Lifecycle

### Management commands

```
apps/pkm/management/commands/
├── seed_pkm_regulations.py    # seeds system regulation chunks
├── seed_pkm_templates.py      # seeds role-template notes
├── _regulation_content.py
└── _role_template_content.py
```

There is **no** `purge_*`, `cleanup_*`, `archive_*`, `prune_*`,
`expire_*`, `gc_*`, or `retention_*` command for any PKM model.

### Scheduled tasks / cron

Searched the repo for `cron`, `beat_schedule`, `CELERY_BEAT`,
`django_q schedule`, `qcluster`. The only q2 usage found is the
async-task broker for `interaction_service._create_sync` (fire-and-forget
single-task enqueue, not scheduled). No `Schedule` rows are created
anywhere for PKM cleanup.

The `notifications` app has `send_tax_reminders.py` (a manual command,
not on a beat). Nothing equivalent exists for PKM.

### What grows unbounded

| Table                          | Growth driver                          | Retention |
|--------------------------------|----------------------------------------|-----------|
| `pkm_qa_history`               | every Q&A call (auto-saved in service) | none      |
| `pkm_user_interaction_log`     | every page view + every business event | none      |
| `pkm_knowledge_note`           | user creates notes                     | user-driven delete only |
| `pkm_document` + `pkm_documentchunk` | user uploads files               | user-driven delete only |
| `pkm_embedding` (VECTOR table) | one row per chunk                      | cascade on chunk delete |
| `pkm_userllmconfig`            | user config                            | user-driven delete only |

`QAHistory` and `UserInteractionLog` are the most concerning: they grow
on every page load and every LLM Q&A, with **no TTL and no cleanup**.
For a 10-user SMB this is hundreds of rows/day. Over a year, the
`pkm_user_interaction_log` table will dwarf most transactional tables,
and each row carries amounts + voucher IDs in `metadata` (Part 1).

### Lifecycle on user delete vs deactivate

All PKM models that reference `User` use
`on_delete=models.CASCADE` (`apps/pkm/models/*.py`):

```python
# knowledge_note.py
user = ForeignKey("identity.User", on_delete=models.CASCADE, related_name="pkm_notes")
# document.py
user = ForeignKey("identity.User", on_delete=models.CASCADE, related_name="pkm_documents")
# qa_history.py
user = ForeignKey("identity.User", on_delete=models.CASCADE, related_name="pkm_qa_history")
# user_llm_config.py (same pattern)
```

`UserInteractionLog` is the exception: `user = ForeignKey(...,
on_delete=models.CASCADE, null=True, blank=True)` - so when the user is
deleted, the row's `user_id` is nulled **only if** Django's collector
actually cascades, but with `on_delete=CASCADE` and `null=True`, the row
is **deleted** (CASCADE wins; `null=True` only matters for SET_NULL).

Wait - `null=True` with `on_delete=CASCADE` means the column allows NULL
in general but CASCADE still deletes the row when the FK target goes. So
on **hard delete** of a user:

- `pkm_knowledge_note` rows: **deleted** (CASCADE)
- `pkm_document` + chunks + embeddings: **deleted** (CASCADE on
  document, then cascade on chunk; embeddings need raw-SQL cascade -
  `rag_pipeline.delete_document_data` - which is NOT invoked by Django's
  cascade, so **orphaned rows in `pkm_embedding` will remain**. The
  embedding table uses raw SQL inserts and has no FK constraint to
  enforce cascade.)
- `pkm_qa_history`: **deleted** (CASCADE)
- `pkm_user_interaction_log`: **deleted** (CASCADE)
- `pkm_userllmconfig`: **deleted** (CASCADE)

On **deactivate** (i.e. `user.is_active = False`, no row deletion):

- Nothing in PKM reacts. No signal, no check. Deactivated users' data
  stays in place, the embedding rows keep matching vector queries, and
  the data still shows up in admin / API listing (subject to
  `LoginRequiredMixin`, which `is_active=False` users fail).
- There is no "anonymise on deactivate" path. The `is_active` flag is
  only consulted by `ModelBackend` for authentication.

### Conclusion for Part 4

- **No retention policy** of any kind: no command, no cron, no TTL.
- **Orphaned vector rows** on user delete (raw-SQL table, no FK).
- **No anonymisation** on deactivate.
- **No GDPR / Vietnamese data-protection hook** (Decree 13/2023/ND-CP on
  Personal Data Protection, in force since 1 July 2023 in Vietnam).

---

## Bonus: Export / Backup

- No PKM export view, command, or API endpoint exists.
- `apps/ui_modern/views/_export_utils.py` and the
  `report_export_views.py`, `vendor_views.py`, etc. provide xlsx/docx/PDF
  export for ledger, sales, VAT, DNSN, etc. **PKM is absent** from the
  `urls.py` export list.
- No `pkm/management/commands/backup_*.py` or
  `dump_pkm_notes`/`dump_qa_history` command.
- API endpoints at `apps/pkm/api.py` allow per-record GET but no bulk
  export (`list_notes` is paginated but returns JSON one page at a time;
  there is no `format=csv` or `format=xlsx` switch).

Users have **no way** to take their PKM data with them, which
compounds the retention problem (Part 4) and the lack of an
anonymisation path: a user leaving the company cannot self-export, and
an admin cannot bulk-purge-export-then-delete.

---

## Concrete data-class exposure matrix

For a typical accounting user in a TT133/2016 SMB who has uploaded a
supplier contract PDF and asked the Q&A "Làm sao hạch toán thuế GTGT
hóa đơn đầu vào?", the LLM provider sees all of the following in a
single completion call:

| Data                                              | Where it came from                              | Sensitivity |
|---------------------------------------------------|-------------------------------------------------|-------------|
| Question text                                     | user                                            | low-high (varies) |
| `Công ty thuộc loại hình Doanh nghiệp siêu nhỏ`   | `company.entity_type`                           | medium (business confidential) |
| `áp dụng chế độ kế toán TT133/2016`               | `company.accounting_regime`                     | medium |
| `Phương pháp GTGT: Khấu trừ`                      | `company.vat_method`                            | medium |
| `Phương pháp TNDN: Tính thuế`                     | `company.tndn_method`                           | medium |
| `Ngành: Thương mại - Công nghệ`                   | `company.industry`                              | medium |
| `Vai trò: Kế toán viên`                           | `UserCompanyRole.role.name`                     | low |
| `Đang ở module Kế toán`                           | latest `UserInteractionLog.module`              | low |
| `hoạt động nghiệp vụ: lập phiếu kế toán BE-V01 (50.000.000 VND)` | `voucher_posting_service` metadata | **HIGH** |
| `lập hóa đơn bán hàng ...`                        | `invoice_service` metadata (total_amount)       | **HIGH** |
| Document chunks from the supplier contract PDF    | user upload                                     | **HIGH** (names, MST, bank accounts) |
| Note content (first 200 chars of each of 5 notes) | user notes                                      | **HIGH** (whatever user typed) |
| Document titles                                   | user-supplied                                   | medium |

This goes to whichever external LLM provider the user picked. If they
chose OpenAI / Anthropic / Google, the data leaves the ERP's trust
boundary. If they chose Ollama (local), it does not - but there is no
guardrail forcing that choice, and the default-suggested models are all
cloud providers.

---

## Files inspected

- `apps/pkm/services/qa_service.py`
- `apps/pkm/services/interaction_service.py`
- `apps/pkm/services/vector_store.py`
- `apps/pkm/services/llm_service.py`
- `apps/pkm/services/chunking_service.py`
- `apps/pkm/services/doc_parser.py`
- `apps/pkm/models/knowledge_note.py`
- `apps/pkm/models/document.py`
- `apps/pkm/models/document_chunk.py`
- `apps/pkm/models/qa_history.py`
- `apps/pkm/models/interaction_log.py`
- `apps/pkm/api.py`
- `apps/pkm/middleware.py`
- `apps/pkm/signals.py`
- `apps/ui_modern/views/pkm_views.py`
- `templates/modern/pkm/note_form.html`
- `templates/modern/pkm/note_detail.html`
- `apps/core/logging_utils.py`
- `apps/core/models.py` (Company fields)
- `apps/ledger/services/voucher_posting_service.py` (metadata)
- `apps/sales/services/invoice_service.py` (metadata)
- `apps/pkm/management/commands/` (full listing)
- `requirements.txt` (markdown>=3.5; Pygments absent)

## Gaps / things not checked (in scope but not exhaustively verified)

- The `rag_pipeline.py` orchestrator was referenced but not re-read
  end-to-end. From the call sites seen (`schedule_document_processing`,
  `delete_document_data`), behaviour matches what is described above.
- The encrypted `api_key_encrypted` storage (via
  `encryption_service`) is correctly implemented: keys are encrypted at
  rest and decrypted per-call, never logged, never echoed in API
  responses. This is **not** a sensitive-data leak; it is the one place
  PKM gets secret handling right.
- No unit tests were executed; this is a static-analysis report.
