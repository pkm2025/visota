# AGENTS.md — PMKetoan (Visota)

> Vietnamese accounting ERP built with Django 5.2 + django-ninja + HTMX + MariaDB.
> Compliant with TT133/2016, TT200/2014, TT78/2021.

## Setup

```bash
# Create venv + install deps
make install

# Start local MariaDB + Redis via docker-compose
docker compose up -d mariadb

# Configure environment
cp .env.example .env

# Run migrations + seed demo data
make migrate
make seed

# Start dev server on port 8903
make dev
```

The app is at http://localhost:8903/auth/login/ (admin / admin123).

## Architecture

Single Django monolith with 28 apps in `apps/`. Layered:
- `ui_modern` — UI layer (views + templates)
- Domain apps — `ledger`, `sales`, `purchasing`, `inventory`, `hr`, `assets`, `reporting`, etc.
- Foundation — `core`, `identity`, `master_data`

Templates: `templates/modern/` with base layout in `templates/modern/base/layout.html`.

## Testing

```bash
# Unit tests (567 tests, ~6min)
make test

# Fast parallel
make test-fast

# E2E (requires running server on :8903)
pytest -c pytest_e2e.ini
```

## Linting & Formatting

```bash
make lint       # ruff check + format check
make format     # ruff format (auto-fix)
```

Pre-commit hooks: `pre-commit install` then `pre-commit run --all-files`.

## Key Commands

| Command | Description |
|---------|-------------|
| `make dev` | Migrate + seed + run server |
| `make test` | Run pytest |
| `make lint` | Ruff check + format |
| `make migrate` | Apply migrations |
| `make makemigrations` | Create migrations |
| `make shell` | Django shell |
| `make seed` | Seed demo data |
| `make clean` | Clean caches |

## Conventions

- Python 3.12+, line length 100 (ruff)
- `apps/<app>/models/` for models, `apps/<app>/services/` for business logic
- Views in `apps/ui_modern/views/`, templates in `templates/modern/`
- Vietnamese for UI labels, English for code identifiers
- Follow TT133/200 accounting regulation for all accounting features
- mypy strict mode enabled
- Test naming: `tests/test_*.py`

## CI/CD

GitHub Actions CI runs on push to main:
- `lint` job: ruff check + format
- `test` job: pytest with MariaDB service
- `security` job: pip-audit

Deploy workflow triggers on push to main.

## Environment Variables

See `.env.example` for all required env vars. Key ones:
- `SECRET_KEY` — Django secret
- `DB_*` — MariaDB connection
- `SENTRY_DSN` — Error tracking (optional)
- `ALLOWED_HOSTS` — Comma-separated hosts
